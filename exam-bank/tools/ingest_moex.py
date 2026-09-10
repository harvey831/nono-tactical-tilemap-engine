#!/usr/bin/env python3
"""考選部題本 → 題庫 JSONL 抽取器（珂洛在本機執行，這裡沒有網路）。

考畢試題查詢平臺提供的是 PDF 題本 ＋ 另一份「測驗式試題標準答案」。
本工具把題本轉成 exam-bank/data/bank/{年}-{場次}-{科目}.jsonl。

⚠️ 版面校正是必要步驟：不同年度的題本排版會變。請務必先跑 inspect
   看抽出來的純文字長什麼樣，確認 regex 命中率，再跑 convert。
   convert 對任何可疑題目會標 needs_review=true，不會默默吞掉。

用法：
    # 1) 先看版面（不寫檔）
    python3 ingest_moex.py inspect --pdf 113_1_B.pdf --lines 60

    # 2) 轉檔（答案另給）
    python3 ingest_moex.py convert --pdf 113_1_B.pdf \
        --year 113 --session 1 --subject B \
        --answers answers_113_1_B.txt --out ../data/bank/113-1-B.jsonl

    # 3) 驗證
    python3 validate_bank.py

答案檔格式（擇一）：
    * 純文字："1 B" 或 "1,B" 或 "1:B" 一行一題；送分題寫 "#"
    * 一整串連續字母："BCDA ACBD ..."（依題號順序，空白會被忽略）
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError, ValueError):
    pass

# 頁首頁尾雜訊：考選部題本每頁都有的欄位
NOISE_RE = re.compile(
    r"^\s*(代號[:：]|頁次[:：]|等別[:：]|類科[:：]|科目[:：]|考試時間[:：]|"
    r"全一張|全一頁|請翻頁|背面尚有試題|禁止使用電子計算器|"
    r"注意[:：]|本試題共|\d+\s*[-－]\s*\d+\s*$)"
)
QUESTION_RE = re.compile(r"^\s*(\d{1,2})\s*[.、．]?\s+(\S.*)$")
OPTION_SPLIT_RE = re.compile(r"[(（]\s*([ABCD])\s*[)）]")


def extract_text(pdf: Path) -> str:
    """優先用 pdftotext -layout（保版面），沒有就退回 pypdf。"""
    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"],
            capture_output=True, text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
        print(f"[warn] pdftotext 失敗（rc={proc.returncode}），改用 pypdf", file=sys.stderr)
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("找不到 pdftotext，也沒安裝 pypdf。請 `pip install pypdf` 或安裝 poppler-utils。")
    reader = PdfReader(str(pdf))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def clean_lines(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        line = raw.replace("　", " ").rstrip()
        if not line.strip() or NOISE_RE.match(line):
            continue
        out.append(line)
    return out


def parse_options(blob: str) -> tuple[str, dict[str, str]]:
    """把『題幹 (A)… (B)… (C)… (D)…』切成題幹與四個選項。"""
    marks = list(OPTION_SPLIT_RE.finditer(blob))
    if not marks:
        return blob.strip(), {}
    stem = blob[: marks[0].start()].strip()
    opts: dict[str, str] = {}
    for i, m in enumerate(marks):
        key = m.group(1)
        end = marks[i + 1].start() if i + 1 < len(marks) else len(blob)
        value = blob[m.end(): end].strip()
        if key not in opts:          # 同一題若重複出現以第一次為準
            opts[key] = value
    return stem, opts


def parse_questions(lines: list[str]) -> list[dict]:
    """依題號切塊，再各自切選項。題號必須遞增才視為新題，避免選項內數字誤判。"""
    blocks: list[tuple[int, list[str]]] = []
    expected = 1
    for line in lines:
        m = QUESTION_RE.match(line)
        if m and int(m.group(1)) == expected:
            blocks.append((expected, [m.group(2)]))
            expected += 1
        elif blocks:
            blocks[-1][1].append(line.strip())

    parsed = []
    for number, body in blocks:
        blob = " ".join(body)
        blob = re.sub(r"\s{2,}", " ", blob)
        stem, opts = parse_options(blob)
        parsed.append({"number": number, "stem": stem, "options": opts})
    return parsed


def load_answers(path: Path, count: int) -> dict[int, str]:
    text = path.read_text(encoding="utf-8")
    answers: dict[int, str] = {}

    pairs = re.findall(r"(\d{1,2})\s*[,:：、.．\s]\s*([ABCD#])", text)
    for num, ans in pairs:
        answers[int(num)] = ans
    if len(answers) >= count * 0.9:
        return answers

    # 退路：一整串連續答案字母
    letters = re.findall(r"[ABCD#]", text)
    if len(letters) >= count:
        return {i + 1: letters[i] for i in range(count)}
    if answers:
        return answers
    sys.exit(f"答案檔解析失敗：只認出 {len(answers)} 題（預期 {count} 題）。請檢查 {path}")


def cmd_inspect(args) -> int:
    text = extract_text(Path(args.pdf))
    lines = clean_lines(text)
    print(f"# 純文字共 {len(text.splitlines())} 行，濾掉頁首頁尾後剩 {len(lines)} 行")
    parsed = parse_questions(lines)
    good = sum(1 for q in parsed if len(q["options"]) == 4)
    print(f"# 切出 {len(parsed)} 題，其中 {good} 題四個選項齊全"
          f"（命中率 {good / len(parsed):.0%}）" if parsed else "# 切不出任何題目")
    print("#" + "-" * 70)
    for line in lines[: args.lines]:
        print(line)
    if parsed:
        print("#" + "-" * 70)
        print("# 第一題解析結果：")
        print(json.dumps(parsed[0], ensure_ascii=False, indent=2))
    return 0


def cmd_convert(args) -> int:
    pdf = Path(args.pdf)
    lines = clean_lines(extract_text(pdf))
    parsed = parse_questions(lines)
    if not parsed:
        sys.exit("切不出任何題目——請先跑 inspect 檢查版面，必要時調整 QUESTION_RE。")

    expected = args.expect
    if len(parsed) != expected:
        print(f"[warn] 切出 {len(parsed)} 題，與預期 {expected} 題不符——"
              f"轉出的檔會標 needs_review，請人工校對。", file=sys.stderr)

    answers = load_answers(Path(args.answers), expected) if args.answers else {}
    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    records, flagged = [], 0
    for q in parsed:
        n = q["number"]
        opts = q["options"]
        suspect = (
            len(opts) != 4
            or any(not v.strip() for v in opts.values())
            or len(q["stem"].strip()) < 8
            or n not in answers
        )
        flagged += suspect
        records.append({
            "id": f"{args.year}-{args.session}-{args.subject}-{n:03d}",
            "year": args.year, "session": args.session,
            "subject": args.subject, "number": n,
            "stem": q["stem"],
            "options": {k: opts.get(k, "") for k in "ABCD"},
            "answer": answers.get(n, "A"),
            "answer_note": None if n in answers else "答案缺漏，暫填 A，待人工補正",
            "answer_revised": False,
            "topics": [], "difficulty": None,
            "has_figure": False, "figures": [],
            "source": pdf.name, "ingested_at": stamp,
            "needs_review": bool(suspect),
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"寫入 {out}：{len(records)} 題，其中 {flagged} 題標記 needs_review")
    if flagged:
        print("→ 請搜尋 needs_review 為 true 的題目人工校對後再改回 false。")
    print("→ 接著跑：python3 validate_bank.py")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="考選部題本 PDF → 題庫 JSONL")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_i = sub.add_parser("inspect", help="只看抽出來的純文字與解析命中率，不寫檔")
    p_i.add_argument("--pdf", required=True)
    p_i.add_argument("--lines", type=int, default=40)
    p_i.set_defaults(func=cmd_inspect)

    p_c = sub.add_parser("convert", help="轉成題庫 JSONL")
    p_c.add_argument("--pdf", required=True)
    p_c.add_argument("--year", type=int, required=True, help="民國年，例如 113")
    p_c.add_argument("--session", type=int, choices=[1, 2], required=True)
    p_c.add_argument("--subject", choices=list("ABCDEF"), required=True)
    p_c.add_argument("--answers", help="標準答案檔")
    p_c.add_argument("--out", required=True)
    p_c.add_argument("--expect", type=int, default=80, help="預期題數，預設 80")
    p_c.set_defaults(func=cmd_convert)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
