#!/usr/bin/env python3
"""題庫覆蓋率報表 — 直接回答「到底收齊了幾年、缺哪幾科、離 4800 題還差多少」。

用法：
    python3 exam-bank/tools/coverage_report.py
    python3 exam-bank/tools/coverage_report.py --markdown > exam-bank/COVERAGE.md
    python3 exam-bank/tools/coverage_report.py --target-years 5
"""
from __future__ import annotations

import argparse
import json
import re
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


def scan(bank_dir: Path) -> dict[tuple[int, int, str], set[int]]:
    grid: dict[tuple[int, int, str], set[int]] = defaultdict(set)
    if not bank_dir.is_dir():
        return grid
    for path in sorted(bank_dir.glob("*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                m = ID_RE.match(str(rec.get("id", "")))
                if m:
                    grid[(int(m.group(1)), int(m.group(2)), m.group(3))].add(int(m.group(4)))
    return grid


def main() -> int:
    ap = argparse.ArgumentParser(description="題庫覆蓋率報表")
    ap.add_argument("--bank", default=str(ROOT / "data" / "bank"))
    ap.add_argument("--markdown", action="store_true", help="輸出 Markdown 表格")
    ap.add_argument("--target-years", type=int, default=5,
                    help="目標收錄年數（預設 5 年 = 10 次考試 = 4800 題）")
    args = ap.parse_args()

    with open(ROOT / "schema" / "subjects.json", encoding="utf-8") as fh:
        meta = json.load(fh)
    per_subject = meta["questions_per_subject"]
    per_sitting = meta["questions_per_sitting"]
    subjects = meta["subjects"]
    codes = [s["code"] for s in subjects]
    names = {s["code"]: s["short"] for s in subjects}

    grid = scan(Path(args.bank))
    sittings = sorted({(y, s) for (y, s, _) in grid}, reverse=True)
    total = sum(len(v) for v in grid.values())
    target_total = args.target_years * meta["sittings_per_year"] * per_sitting

    lines: list[str] = []
    emit = lines.append

    if args.markdown:
        emit("# 題庫覆蓋率")
        emit("")
        emit(f"> 目標：{args.target_years} 年 × {meta['sittings_per_year']} 次 × "
             f"{len(codes)} 科 × {per_subject} 題 = **{target_total} 題**")
        emit("")
        emit("| 年度場次 | " + " | ".join(f"{c} {names[c]}" for c in codes) + " | 小計 |")
        emit("|---|" + "---|" * (len(codes) + 1))
    else:
        print(f"題庫目錄：{args.bank}")
        print(f"目標：{args.target_years} 年 × {meta['sittings_per_year']} 次 × "
              f"{len(codes)} 科 × {per_subject} 題 = {target_total} 題")
        print()
        header = "年度場次   " + "".join(f"{c:>8}" for c in codes) + f"{'小計':>10}"
        print(header)
        print("-" * 70)

    for (y, s) in sittings:
        cells = []
        row_total = 0
        for c in codes:
            n = len(grid.get((y, s, c), ()))
            row_total += n
            if n == 0:
                cells.append("—")
            elif n == per_subject:
                cells.append(f"{n}")
            else:
                cells.append(f"{n}⚠")
        label = f"{y}年第{s}次"
        if args.markdown:
            emit(f"| {label} | " + " | ".join(cells) + f" | {row_total}/{per_sitting} |")
        else:
            print(f"{label:<10}" + "".join(f"{c:>8}" for c in cells) + f"{f'{row_total}/{per_sitting}':>12}")

    gap = target_total - total
    summary = [
        "",
        f"已收錄：{total} 題（{len(sittings)} 個場次）",
        f"目標 {target_total} 題 → " + (
            f"還差 {gap} 題" if gap > 0 else
            f"已達標，超出 {-gap} 題" if gap < 0 else "剛好達標"),
    ]

    holes = []
    for (y, s) in sittings:
        for c in codes:
            nums = grid.get((y, s, c), set())
            if not nums:
                holes.append(f"{y}年第{s}次 {c}({names[c]})：整科缺")
            elif len(nums) < per_subject:
                missing = sorted(set(range(1, per_subject + 1)) - nums)
                preview = ", ".join(map(str, missing[:10])) + (" …" if len(missing) > 10 else "")
                holes.append(f"{y}年第{s}次 {c}({names[c]})：缺 {len(missing)} 題 [{preview}]")

    if args.markdown:
        emit("")
        for ln in summary[1:]:
            emit(f"- {ln}")
        if holes:
            emit("")
            emit("## 缺口明細")
            emit("")
            for h in holes:
                emit(f"- {h}")
        print("\n".join(lines))
    else:
        for ln in summary:
            print(ln)
        if holes:
            print("\n缺口明細：")
            for h in holes:
                print(f"  - {h}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
