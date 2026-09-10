#!/usr/bin/env python3
"""NONO 自適應出題引擎 — 依作答紀錄推估程度，挑出「剛好難一點」的題目。

能力模型：1PL (Rasch) + 四選一猜對修正
    P(答對) = c + (1 - c) * sigmoid(theta - b)，c = 0.25
    theta = 使用者該科能力，b = 題目難度，兩者同在 logit 尺度。

選題原則：目標答對率 p* ≈ 0.70（可調）。太簡單學不到、太難只會打擊信心，
挑預測答對率落在 p* 附近的題，是學習效率最高的區間。錯題另走間隔重複 (SM-2 lite)。

所有狀態可由 progress/attempts.jsonl 完整重建；state.json 只是快取。
純標準庫，無外部相依，可直接放在 Google Drive 同步資料夾內執行。

用法：
    python3 quiz_engine.py next   --subject B --count 10
    python3 quiz_engine.py record --qid 113-1-B-042 --chosen C --seconds 35
    python3 quiz_engine.py status
    python3 quiz_engine.py drill  --subject B --count 5      # 終端機互動練習
    python3 quiz_engine.py rebuild                            # 由 attempts 重建 state
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError, ValueError):  # Windows 沒有 SIGPIPE
    pass

ROOT = Path(__file__).resolve().parents[1]
BANK_DIR = ROOT / "data" / "bank"
PROGRESS_DIR = ROOT / "progress"
ATTEMPTS = PROGRESS_DIR / "attempts.jsonl"
STATE = PROGRESS_DIR / "state.json"

GUESS = 0.25          # 四選一猜對機率
TARGET_P = 0.70       # 目標答對率（學習區）
THETA_K_MAX = 0.60    # 能力更新步長上界
THETA_K_MIN = 0.08
ITEM_K = 0.04         # 題目難度更新步長（單一使用者，刻意壓很小）
COOLDOWN_DAYS = 3     # 剛做過的題暫時不重出（除非 SRS 到期）
ID_RE = re.compile(r"^(\d{2,3})-([12])-([A-F])-(\d{3})$")


# ---------------------------------------------------------------- 基礎工具

def disp_width(text: str) -> int:
    """中日韓全形字算 2 格，讓終端機表格對得齊。"""
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1 for ch in text)


def pad(text: str, width: int) -> str:
    return text + " " * max(0, width - disp_width(text))


def sigmoid(x: float) -> float:
    if x < -700:
        return 0.0
    if x > 700:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def predict(theta: float, b: float) -> float:
    """含猜測修正的答對機率。"""
    return GUESS + (1.0 - GUESS) * sigmoid(theta - b)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today() -> date:
    return datetime.now().date()


def parse_date(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- 題庫

def load_bank(bank_dir: Path = BANK_DIR) -> dict[str, dict]:
    bank: dict[str, dict] = {}
    if not bank_dir.is_dir():
        return bank
    for path in sorted(bank_dir.glob("*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                qid = str(rec.get("id", ""))
                if ID_RE.match(qid):
                    bank[qid] = rec
    return bank


def load_subjects() -> dict:
    with open(ROOT / "schema" / "subjects.json", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- 狀態

def blank_state() -> dict:
    return {"version": 1, "updated_at": None, "subjects": {}, "topics": {}, "items": {}}


def load_state() -> dict:
    if STATE.is_file():
        with open(STATE, encoding="utf-8") as fh:
            st = json.load(fh)
        for key in ("subjects", "topics", "items"):
            st.setdefault(key, {})
        return st
    return blank_state()


def save_state(state: dict) -> None:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    tmp = STATE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    tmp.replace(STATE)


def item_state(state: dict, qid: str, question: dict | None) -> dict:
    it = state["items"].get(qid)
    if it is None:
        base = question.get("difficulty") if question else None
        it = {
            "n": 0, "correct": 0, "last_ts": None,
            "ease": 2.5, "interval_days": 0, "due": None, "lapses": 0,
            "b": float(base) if isinstance(base, (int, float)) else 0.0,
        }
        state["items"][qid] = it
    return it


def subject_state(state: dict, code: str) -> dict:
    return state["subjects"].setdefault(code, {"theta": 0.0, "n": 0, "correct": 0})


def theta_step(n: int) -> float:
    """作答越多，能力估計越穩，步長越小。"""
    return max(THETA_K_MIN, THETA_K_MAX / (1.0 + n / 20.0))


def apply_attempt(state: dict, attempt: dict, bank: dict) -> None:
    """把一筆作答併入狀態（可重複呼叫以重建）。"""
    qid = attempt["qid"]
    correct = bool(attempt["correct"])
    question = bank.get(qid)
    m = ID_RE.match(qid)
    code = m.group(3) if m else (question or {}).get("subject", "?")

    subj = subject_state(state, code)
    it = item_state(state, qid, question)

    expected = predict(subj["theta"], it["b"])
    obs = 1.0 if correct else 0.0

    subj["theta"] += theta_step(subj["n"]) * (obs - expected)
    subj["theta"] = max(-3.0, min(3.0, subj["theta"]))
    subj["n"] += 1
    subj["correct"] += int(correct)

    it["b"] -= ITEM_K * (obs - expected)
    it["b"] = max(-3.0, min(3.0, it["b"]))
    it["n"] += 1
    it["correct"] += int(correct)
    it["last_ts"] = attempt.get("ts") or now_iso()

    # SM-2 lite 間隔重複
    ref = parse_date(it["last_ts"]) or today()
    if correct:
        it["ease"] = min(2.8, it["ease"] + 0.10)
        if it["interval_days"] <= 0:
            it["interval_days"] = 1
        elif it["interval_days"] == 1:
            it["interval_days"] = 3
        else:
            it["interval_days"] = int(round(it["interval_days"] * it["ease"]))
        it["interval_days"] = min(it["interval_days"], 180)
    else:
        it["ease"] = max(1.3, it["ease"] - 0.25)
        it["interval_days"] = 1
        it["lapses"] += 1
    it["due"] = (ref + timedelta(days=it["interval_days"])).isoformat()

    for topic in (question or {}).get("topics") or []:
        t = state["topics"].setdefault(topic, {"n": 0, "correct": 0})
        t["n"] += 1
        t["correct"] += int(correct)


def read_attempts() -> list[dict]:
    if not ATTEMPTS.is_file():
        return []
    out = []
    with open(ATTEMPTS, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


# ---------------------------------------------------------------- 選題

def weak_topic_bonus(state: dict, question: dict) -> float:
    """弱項知識點加權：該 topic 答對率越低，加分越多。"""
    topics = question.get("topics") or []
    if not topics:
        return 0.0
    scores = []
    for t in topics:
        st = state["topics"].get(t)
        if not st or st["n"] < 3:      # 樣本太少不採信
            continue
        scores.append(1.0 - st["correct"] / st["n"])
    return max(scores) * 0.25 if scores else 0.0


def select(state: dict, bank: dict, *, subject: str | None, count: int,
           mode: str, target_p: float, include_figures: bool,
           include_bonus: bool, rng: random.Random) -> list[dict]:
    pool = []
    for qid, q in bank.items():
        if subject and q.get("subject") != subject:
            continue
        if not include_figures and q.get("has_figure"):
            continue
        if not include_bonus and q.get("answer") == "#":
            continue
        pool.append(q)
    if not pool:
        return []

    if mode == "exam":
        rng.shuffle(pool)
        return sorted(pool[:count], key=lambda q: q["number"])

    due_items, fresh = [], []
    t = today()
    for q in pool:
        it = state["items"].get(q["id"])
        if it is None:
            fresh.append(q)
            continue
        due = parse_date(it.get("due"))
        last = parse_date(it.get("last_ts"))
        if due and due <= t:
            due_items.append((due, q))
        elif last and (t - last).days < COOLDOWN_DAYS:
            continue                    # 冷卻期，跳過
        else:
            fresh.append(q)

    if mode == "review":
        due_items.sort(key=lambda p: p[0])
        return [q for _, q in due_items[:count]]

    picked: list[dict] = []
    seen: set[str] = set()

    # 到期錯題優先，但最多佔一半，避免整場都在複習舊題
    due_items.sort(key=lambda p: p[0])
    for _, q in due_items[: max(1, count // 2)]:
        picked.append(q)
        seen.add(q["id"])

    remaining = count - len(picked)
    if remaining > 0 and fresh:
        scored = []
        for q in fresh:
            if q["id"] in seen:
                continue
            subj = state["subjects"].get(q["subject"], {"theta": 0.0})
            it = state["items"].get(q["id"])
            b = it["b"] if it else (q.get("difficulty") if isinstance(q.get("difficulty"), (int, float)) else 0.0)
            p = predict(subj["theta"], float(b))
            score = -abs(p - target_p)
            if mode == "weak":
                score += weak_topic_bonus(state, q) * 2.0
            else:
                score += weak_topic_bonus(state, q)
            scored.append((score, q))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        # 從前 3 倍的候選裡隨機取，避免每次都出同一批題
        head = [q for _, q in scored[: max(remaining * 3, remaining)]]
        rng.shuffle(head)
        picked.extend(head[:remaining])

    return picked[:count]


# ---------------------------------------------------------------- 指令

def public_view(q: dict) -> dict:
    """給 NONO 出題用的視圖——不含答案。"""
    return {
        "id": q["id"],
        "subject": q["subject"],
        "year": q["year"],
        "session": q["session"],
        "number": q["number"],
        "stem": q["stem"],
        "options": q["options"],
        "topics": q.get("topics") or [],
    }


def cmd_next(args) -> int:
    bank = load_bank(Path(args.bank))
    if not bank:
        print(f"題庫是空的：{args.bank}\n請先讓珂洛把題目推上來，再跑 validate_bank.py 驗過。",
              file=sys.stderr)
        return 2
    state = load_state()
    rng = random.Random(args.seed)
    picked = select(state, bank, subject=args.subject, count=args.count,
                    mode=args.mode, target_p=args.target_p,
                    include_figures=args.include_figures,
                    include_bonus=args.include_bonus, rng=rng)
    if not picked:
        print("選不到題（可能被科目篩選、含圖題排除或冷卻期擋掉了）。", file=sys.stderr)
        return 3
    print(json.dumps([public_view(q) for q in picked], ensure_ascii=False, indent=2))
    return 0


def cmd_record(args) -> int:
    bank = load_bank(Path(args.bank))
    q = bank.get(args.qid)
    if q is None:
        print(f"題庫裡找不到 {args.qid}", file=sys.stderr)
        return 2
    chosen = args.chosen.strip().upper()
    if chosen not in ("A", "B", "C", "D"):
        print("--chosen 必須是 A/B/C/D", file=sys.stderr)
        return 2

    answer = q["answer"]
    correct = True if answer == "#" else (chosen == answer)
    attempt = {
        "ts": now_iso(), "qid": args.qid, "chosen": chosen,
        "correct": correct, "seconds": args.seconds, "mode": args.mode,
    }
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ATTEMPTS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(attempt, ensure_ascii=False) + "\n")

    state = load_state()
    apply_attempt(state, attempt, bank)
    save_state(state)

    subj = state["subjects"][q["subject"]]
    print(json.dumps({
        "qid": args.qid,
        "correct": correct,
        "answer": answer,
        "chosen": chosen,
        "subject": q["subject"],
        "theta": round(subj["theta"], 3),
        "subject_accuracy": round(subj["correct"] / subj["n"], 3) if subj["n"] else None,
        "next_due": state["items"][args.qid]["due"],
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_status(args) -> int:
    bank = load_bank(Path(args.bank))
    state = load_state()
    meta = load_subjects()
    names = {s["code"]: s["short"] for s in meta["subjects"]}
    t = today()

    due = 0
    for it in state["items"].values():
        d = parse_date(it.get("due"))
        if d and d <= t:
            due += 1

    rows = []
    for s in meta["subjects"]:
        code = s["code"]
        st = state["subjects"].get(code)
        in_bank = sum(1 for q in bank.values() if q.get("subject") == code)
        if st and st["n"]:
            acc = st["correct"] / st["n"]
            rows.append({
                "code": code, "name": names[code], "bank": in_bank,
                "answered": st["n"], "accuracy": round(acc, 3),
                "theta": round(st["theta"], 3),
                "est_score": round(acc * 100, 1),
            })
        else:
            rows.append({"code": code, "name": names[code], "bank": in_bank,
                         "answered": 0, "accuracy": None, "theta": 0.0, "est_score": None})

    weak = sorted(
        ({"topic": k, "n": v["n"], "accuracy": round(v["correct"] / v["n"], 3)}
         for k, v in state["topics"].items() if v["n"] >= 3),
        key=lambda r: r["accuracy"],
    )[:15]

    MIN_N = 10   # 樣本太少的科目不納入推估，避免用 3 題就宣稱程度
    scored = [(r["code"], r["est_score"]) for r in rows
              if r["est_score"] is not None and r["answered"] >= MIN_N]
    result = {
        "bank_size": len(bank),
        "total_attempts": sum(r["answered"] for r in rows),
        "due_for_review": due,
        "subjects": rows,
        "weakest_topics": weak,
        "estimated_average": round(sum(v for _, v in scored) / len(scored), 1) if scored else None,
        "estimated_over_subjects": [c for c, _ in scored],
        "min_attempts_for_estimate": MIN_N,
        "pass_line": 60,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"題庫 {len(bank)} 題／已作答 {result['total_attempts']} 題／待複習 {due} 題")
    print()
    print(pad("科目", 26) + f"{'題庫':>6}{'已答':>6}{'答對率':>9}{'能力θ':>9}")
    print("-" * 60)
    for r in rows:
        acc = f"{r['accuracy']*100:.1f}%" if r["accuracy"] is not None else "—"
        print(pad(f"{r['code']} {r['name']}", 26) + f"{r['bank']:>6}{r['answered']:>6}{acc:>9}{r['theta']:>9.2f}")
    if result["estimated_average"] is not None:
        avg = result["estimated_average"]
        covered = "".join(result["estimated_over_subjects"])
        verdict = "已達及格線" if avg >= 60 else f"距及格線還差 {60 - avg:.1f} 分"
        print(f"\n推估平均：{avg} 分（採計科目 {covered}，及格 60 分）→ {verdict}")
        if len(covered) < len(rows):
            print(f"※ 其餘科目作答未滿 {MIN_N} 題，尚不列入推估。")
        print("※ 這是依你目前作答紀錄的推估，不等同實際考試成績。")
    else:
        print(f"\n各科作答皆未滿 {MIN_N} 題，樣本不足以推估程度——先多練幾題。")
    if weak:
        print("\n最弱的知識點：")
        for w in weak[:8]:
            print(f"  - {w['topic']}：{w['accuracy']*100:.0f}%（{w['n']} 題）")
    return 0


def cmd_rebuild(args) -> int:
    bank = load_bank(Path(args.bank))
    attempts = read_attempts()
    state = blank_state()
    for a in attempts:
        if "qid" in a and "correct" in a:
            apply_attempt(state, a, bank)
    save_state(state)
    print(f"已由 {len(attempts)} 筆作答紀錄重建 state.json")
    return 0


def cmd_drill(args) -> int:
    """終端機互動練習：出題 → 作答 → 即時對答案並寫入紀錄。"""
    bank = load_bank(Path(args.bank))
    if not bank:
        print(f"題庫是空的：{args.bank}", file=sys.stderr)
        return 2
    state = load_state()
    rng = random.Random(args.seed)
    picked = select(state, bank, subject=args.subject, count=args.count,
                    mode=args.mode, target_p=args.target_p,
                    include_figures=args.include_figures,
                    include_bonus=args.include_bonus, rng=rng)
    if not picked:
        print("選不到題。", file=sys.stderr)
        return 3

    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    right = 0
    for i, q in enumerate(picked, 1):
        print(f"\n[{i}/{len(picked)}] {q['id']}　（{q['year']}年第{q['session']}次）")
        print(q["stem"])
        for k in ("A", "B", "C", "D"):
            print(f"  ({k}) {q['options'][k]}")
        try:
            chosen = input("你的答案 (A/B/C/D，直接 Enter 跳過，q 離開)： ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n中斷。")
            break
        if chosen == "Q":
            break
        if chosen not in ("A", "B", "C", "D"):
            print("跳過。")
            continue

        answer = q["answer"]
        correct = True if answer == "#" else (chosen == answer)
        right += int(correct)
        attempt = {"ts": now_iso(), "qid": q["id"], "chosen": chosen,
                   "correct": correct, "seconds": None, "mode": "drill"}
        with open(ATTEMPTS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(attempt, ensure_ascii=False) + "\n")
        apply_attempt(state, attempt, bank)
        print("✅ 答對" if correct else f"❌ 答錯，正確答案是 ({answer})")
        if q.get("answer_note"):
            print(f"   註：{q['answer_note']}")

    save_state(state)
    total_answered = sum(1 for a in read_attempts() if a.get("mode") == "drill")
    print(f"\n本次答對 {right} 題。累計 drill 作答 {total_answered} 題。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="NONO 醫放師國考自適應出題引擎")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, default_count=10):
        p.add_argument("--bank", default=str(BANK_DIR))
        p.add_argument("--subject", choices=list("ABCDEF"), help="限定科目")
        p.add_argument("--count", type=int, default=default_count)
        p.add_argument("--mode", default="adaptive",
                       choices=["adaptive", "weak", "review", "exam"],
                       help="adaptive=依程度出題／weak=主攻弱項／review=只複習到期錯題／exam=隨機模考")
        p.add_argument("--target-p", type=float, default=TARGET_P,
                       dest="target_p", help="目標答對率，預設 0.70")
        p.add_argument("--include-figures", action="store_true", help="納入含圖題")
        p.add_argument("--include-bonus", action="store_true", help="納入送分題")
        p.add_argument("--seed", type=int, default=None)

    p_next = sub.add_parser("next", help="選題並以 JSON 輸出（不含答案）")
    common(p_next)
    p_next.set_defaults(func=cmd_next)

    p_drill = sub.add_parser("drill", help="終端機互動練習")
    common(p_drill, default_count=5)
    p_drill.set_defaults(func=cmd_drill)

    p_rec = sub.add_parser("record", help="登錄一筆作答")
    p_rec.add_argument("--bank", default=str(BANK_DIR))
    p_rec.add_argument("--qid", required=True)
    p_rec.add_argument("--chosen", required=True)
    p_rec.add_argument("--seconds", type=float, default=None)
    p_rec.add_argument("--mode", default="adaptive")
    p_rec.set_defaults(func=cmd_record)

    p_st = sub.add_parser("status", help="顯示各科程度與弱項")
    p_st.add_argument("--bank", default=str(BANK_DIR))
    p_st.add_argument("--json", action="store_true")
    p_st.set_defaults(func=cmd_status)

    p_rb = sub.add_parser("rebuild", help="由 attempts.jsonl 重建 state.json")
    p_rb.add_argument("--bank", default=str(BANK_DIR))
    p_rb.set_defaults(func=cmd_rebuild)

    return ap


if __name__ == "__main__":
    parser = build_parser()
    ns = parser.parse_args()
    raise SystemExit(ns.func(ns))
