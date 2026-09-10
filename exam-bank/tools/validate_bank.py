#!/usr/bin/env python3
"""題庫驗證器（fail-closed）。

掃描 exam-bank/data/bank/*.jsonl，逐題檢查格式、欄位一致性與場次完整性。
只要有任何 ERROR 就以 exit code 1 結束——題庫不完整時絕不宣告通過。

用法：
    python3 exam-bank/tools/validate_bank.py
    python3 exam-bank/tools/validate_bank.py --bank <目錄> --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# 讓輸出接 head/less 時不要噴 BrokenPipeError
try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError, ValueError):  # Windows 沒有 SIGPIPE
    pass

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^(\d{2,3})-([12])-([A-F])-(\d{3})$")
OPTION_KEYS = ("A", "B", "C", "D")
VALID_ANSWERS = {"A", "B", "C", "D", "#"}

REQUIRED = ("id", "year", "session", "subject", "number", "stem", "options", "answer")
ALLOWED = set(REQUIRED) | {
    "answer_note", "answer_revised", "topics", "difficulty",
    "has_figure", "figures", "source", "ingested_at", "needs_review",
}


def load_subjects() -> dict:
    with open(ROOT / "schema" / "subjects.json", encoding="utf-8") as fh:
        return json.load(fh)


def check_question(rec: dict, where: str, errors: list, warnings: list) -> None:
    """把單題的所有問題累積到 errors / warnings，不提早 return。"""
    missing = [k for k in REQUIRED if k not in rec]
    if missing:
        errors.append(f"{where}: 缺少必填欄位 {missing}")
        return

    unknown = set(rec) - ALLOWED
    if unknown:
        errors.append(f"{where}: 出現未定義欄位 {sorted(unknown)}")

    qid = rec["id"]
    m = ID_RE.match(qid) if isinstance(qid, str) else None
    if not m:
        errors.append(f"{where}: id 格式錯誤 {qid!r}（應為 113-1-B-042）")
        return

    y, s, subj, num = int(m.group(1)), int(m.group(2)), m.group(3), int(m.group(4))
    for field, from_id, label in (
        ("year", y, "年度"), ("session", s, "場次"),
        ("subject", subj, "科目"), ("number", num, "題號"),
    ):
        if rec[field] != from_id:
            errors.append(
                f"{where} [{qid}]: {label}欄位 {rec[field]!r} 與 id 內含值 {from_id!r} 不一致"
            )

    if not isinstance(rec["number"], int) or not 1 <= rec["number"] <= 80:
        errors.append(f"{where} [{qid}]: 題號須為 1-80，實得 {rec['number']!r}")

    stem = rec["stem"]
    if not isinstance(stem, str) or not stem.strip():
        errors.append(f"{where} [{qid}]: 題幹為空")
    elif len(stem.strip()) < 8:
        warnings.append(f"{where} [{qid}]: 題幹僅 {len(stem.strip())} 字，疑似抽取不完整")

    opts = rec["options"]
    if not isinstance(opts, dict):
        errors.append(f"{where} [{qid}]: options 須為物件")
    else:
        if set(opts) != set(OPTION_KEYS):
            errors.append(f"{where} [{qid}]: 選項鍵須恰為 A/B/C/D，實得 {sorted(opts)}")
        for k, v in opts.items():
            if not isinstance(v, str) or not v.strip():
                errors.append(f"{where} [{qid}]: 選項 {k} 為空")
        texts = [v.strip() for v in opts.values() if isinstance(v, str)]
        if len(texts) == len(set(texts)) is False or len(set(texts)) < len(texts):
            warnings.append(f"{where} [{qid}]: 有重複的選項文字")

    ans = rec["answer"]
    if ans not in VALID_ANSWERS:
        errors.append(f"{where} [{qid}]: answer 須為 A/B/C/D 或 '#'（送分），實得 {ans!r}")
    elif ans != "#" and isinstance(opts, dict) and ans not in opts:
        errors.append(f"{where} [{qid}]: 標準答案 {ans} 不在選項中")

    diff = rec.get("difficulty")
    if diff is not None and not (isinstance(diff, (int, float)) and -3 <= diff <= 3):
        errors.append(f"{where} [{qid}]: difficulty 須為 -3~3 或 null，實得 {diff!r}")

    if rec.get("has_figure") and not rec.get("figures"):
        warnings.append(f"{where} [{qid}]: 標記為含圖題但 figures 為空")

    for field in ("topics", "figures"):
        val = rec.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"{where} [{qid}]: {field} 須為陣列")


def main() -> int:
    ap = argparse.ArgumentParser(description="醫事放射師題庫驗證器")
    ap.add_argument("--bank", default=str(ROOT / "data" / "bank"), help="題庫目錄")
    ap.add_argument("--json", action="store_true", help="以 JSON 輸出結果")
    ap.add_argument("--strict", action="store_true", help="把 warning 也視為失敗")
    args = ap.parse_args()

    subjects = load_subjects()
    per_subject = subjects["questions_per_subject"]
    valid_codes = {s["code"] for s in subjects["subjects"]}

    bank_dir = Path(args.bank)
    files = sorted(bank_dir.glob("*.jsonl")) if bank_dir.is_dir() else []

    errors: list[str] = []
    warnings: list[str] = []
    seen_ids: dict[str, str] = {}
    sittings: dict[tuple, set] = defaultdict(set)
    total = 0

    if not files:
        warnings.append(f"{bank_dir} 內沒有任何 .jsonl 題庫檔——題庫尚未匯入。")

    for path in files:
        with open(path, encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                where = f"{path.name}:{lineno}"
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    errors.append(f"{where}: JSON 解析失敗 — {exc}")
                    continue
                if not isinstance(rec, dict):
                    errors.append(f"{where}: 每行須為 JSON 物件")
                    continue

                total += 1
                check_question(rec, where, errors, warnings)

                # id 只要解析得出來就登記，重複與缺題檢查不因其他欄位有錯而失效
                qid = rec.get("id")
                m = ID_RE.match(qid) if isinstance(qid, str) else None
                if not m:
                    continue
                if qid in seen_ids:
                    errors.append(f"{where} [{qid}]: id 重複（先前出現於 {seen_ids[qid]}）")
                else:
                    seen_ids[qid] = where
                subj = m.group(3)
                if subj not in valid_codes:
                    errors.append(f"{where} [{qid}]: 未知科目代碼 {subj!r}")
                sittings[(int(m.group(1)), int(m.group(2)), subj)].add(int(m.group(4)))

    # 場次完整性：每科應有 1-80 題
    incomplete = []
    for key in sorted(sittings):
        nums = sittings[key]
        missing = sorted(set(range(1, per_subject + 1)) - nums)
        extra = sorted(n for n in nums if n > per_subject)
        label = f"{key[0]}年第{key[1]}次 科目{key[2]}"
        if missing:
            incomplete.append(f"{label}: 缺 {len(missing)} 題 → {missing[:12]}{' …' if len(missing) > 12 else ''}")
        if extra:
            errors.append(f"{label}: 出現超出 1-{per_subject} 的題號 {extra}")
    warnings.extend(incomplete)

    ok = not errors and (not args.strict or not warnings)
    result = {
        "ok": ok,
        "files": len(files),
        "questions": total,
        "unique_ids": len(seen_ids),
        "sittings": len(sittings),
        "errors": errors,
        "warnings": warnings,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"題庫目錄：{bank_dir}")
        print(f"檔案 {len(files)} 個 / 題目 {total} 題 / 不重複 id {len(seen_ids)} 個 / 涵蓋 {len(sittings)} 個科次")
        for w in warnings:
            print(f"  [WARN ] {w}")
        for e in errors:
            print(f"  [ERROR] {e}")
        print("結果：" + ("通過 ✅" if ok else "未通過 ❌"))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
