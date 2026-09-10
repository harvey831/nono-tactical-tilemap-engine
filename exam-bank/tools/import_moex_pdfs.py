# -*- coding: utf-8 -*-
"""考選部題本 PDF → exam-bank JSONL（珂洛在大叔本機執行；雲端容器連不到考選部）。

跟 import_chengyu_bank.py 的差別：那支是吃澄羽已經抽好的 index/*.jsonl，
這支直接吃考畢試題查詢平臺下載回來的 PDF（題本 Q／標準答案 S／答案更正 M），
所以之後要再補年度，只要把 PDF 抓下來放進 sources/{年}_{場次}/ 就能重跑。

目錄慣例（跟澄羽既有的 study_radiographer 一致）：
    sources/{民國年}_{場次}/{科目代碼}_{Q|S|M}.pdf
    科目代碼 111～113 年是 11/22/33/44/55/66，114 年起改成 0104/0601～0605

答案語意（跟 IMPORT_REPORT_KELUO.md 第 4 節同一套規則）：
    一律給分  → answer "#"，任何作答皆給分
    部分給分  → answer 仍是 "#"（schema 只能放單一字母），可給分選項寫進 answer_note
                與 data/corrections_parsed.json，批改時必須看註記
    答案更正  → 公告只給一個字母（例：「第52題答Ｃ給分」）＝改標準答案，不是送分

用法：
    # 1) 只檢查不寫檔
    python import_moex_pdfs.py --sources "C:/GPTfile/姐姐大人/study_radiographer/sources" --years 106-110

    # 2) 寫出題庫
    python import_moex_pdfs.py --sources ... --years 106-110 \
        --out-dir ../data/bank --text-out ../data/incoming/moex_106_110/text \
        --corrections-out ../data/corrections_parsed.json --report ../progress/import_106_110.json
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from import_chengyu_bank import SUBJECT_TO_CODE, split_stem_options  # noqa: E402

CATEGORY = "醫事放射師"

# 檔名上的科目代碼 → schema 的 A-F；仍會拿題本上的「科目名稱」交叉驗證
FILE_CODE_TO_LETTER = {
    "11": "A", "22": "B", "33": "C", "44": "D", "55": "E", "66": "F",
    "0104": "A", "0108": "A", "0601": "B", "0602": "C", "0603": "D", "0604": "E", "0605": "F",
}

QUESTION_MARK = re.compile(r"(?m)^\s*(\d{1,2})\s*[.．、]\s*")
FIGURE_KEYWORD = re.compile(r"如圖|下圖|附圖|圖中|下表|圖示")
ANSWER_LINE = re.compile(r"^\s*答案\s+")
SITTING_IN_HEADER = re.compile(r"(\d{3})\s*年第([一二三])次")
SITTING_WORDS = {"一": 1, "二": 2, "三": 3}
CLAUSE = re.compile(r"第\s*(\d{1,3})\s*題([^第]*)")
GIVE_CREDIT = re.compile(r"答([A-D、或\s]+?)者?均?給分")


def extract_text(pdf: Path, cache: Path | None) -> str:
    """pypdf 抽字；有 cache 就寫一份純文字（方便雲端的 NONO 核對，她讀不到 PDF）。"""
    from pypdf import PdfReader

    pages = [re.sub(r"[\ud800-\udfff]", "\uFFFD", page.extract_text() or "") for page in PdfReader(str(pdf)).pages]
    text = "\n\n".join(f"=== PDF PAGE {i + 1} ===\n{p}" for i, p in enumerate(pages))
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(text, encoding="utf-8")
    return "\n".join(pages)


def parse_answer_table(text: str) -> list[str]:
    """標準答案／更正答案 PDF 的『答案 Ｂ Ｃ …』表格；回傳 80 個 token。"""
    tokens: list[str] = []
    for line in text.splitlines():
        if ANSWER_LINE.match(line):
            body = unicodedata.normalize("NFKC", line.split("答案", 1)[1])
            tokens.extend(re.findall(r"[ABCD#]", body))
    return tokens


def parse_notices(text: str) -> dict[int, dict]:
    """『備註』區的更正公告 → {題號: {kind, accepted, notice}}。看不懂的一律拋錯，不猜。"""
    normalized = unicodedata.normalize("NFKC", text)
    tail = normalized[normalized.rfind("備 註") if "備 註" in normalized else 0:]
    start = re.search(r"第\s*\d{1,3}\s*題", tail)
    if not start:
        return {}
    body = tail[start.start():].strip()
    out: dict[int, dict] = {}
    for m in CLAUSE.finditer(body):
        number = int(m.group(1))
        clause_body = m.group(2).strip()
        notice = f"第{number}題{clause_body}".rstrip("，,。 ")
        if "一律給分" in clause_body:
            out[number] = {"kind": "一律給分", "accepted": ["A", "B", "C", "D"], "notice": notice}
            continue
        credit = GIVE_CREDIT.search(clause_body)
        if credit:
            letters = re.findall(r"[A-D]", credit.group(1))
            if not letters:
                raise ValueError(f"更正公告看不出可給分選項：{notice!r}")
            kind = "部分給分" if len(letters) > 1 else "答案更正"
            out[number] = {"kind": kind, "accepted": letters, "notice": notice}
            continue
        raise ValueError(f"無法判讀的更正公告：{notice!r}")
    return out


def build_note(entry: dict, original: str) -> str:
    """跟 111-115 那批同一套措辭，讓兩批註記可以互相比對。"""
    if entry["kind"] == "一律給分":
        return f"考選部更正公告：{entry['notice']}（本題一律給分，任何作答皆給分）"
    if entry["kind"] == "部分給分":
        accepted = "".join(entry["accepted"])
        return (f"考選部更正公告：{entry['notice']}（原標準答案 {original}；可給分選項＝{accepted}。"
                f"本 schema 的 answer 無法表達複數正解，暫以 \"#\" 標記，批改請依本註記，勿當成一律給分）")
    return (f"考選部更正公告：{entry['notice']}（原標準答案 {original}，已更正為 {entry['accepted'][0]}，"
            f"非送分題）")


def parse_years(spec: str) -> set[int]:
    years: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            years.update(range(int(lo), int(hi) + 1))
        else:
            years.add(int(part))
    return years


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", required=True, help="sources 目錄（底下是 {年}_{場次}/）")
    ap.add_argument("--years", default="", help="只處理這些民國年，例 106-110 或 106,108")
    ap.add_argument("--out-dir", help="輸出 data/bank；不給就只檢查不寫檔")
    ap.add_argument("--text-out", help="順便輸出每份 PDF 的純文字（給讀不到 PDF 的人核對）")
    ap.add_argument("--corrections-out", help="更正公告逐題表；已存在就合併（同 id 覆蓋）")
    ap.add_argument("--report", help="輸出這次匯入的統計 JSON")
    args = ap.parse_args()

    sources = Path(args.sources)
    wanted = parse_years(args.years) if args.years else None
    text_out = Path(args.text_out) if args.text_out else None
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    papers, fails, reviews = [], [], []
    corrections: list[dict] = []
    out: dict[tuple, list] = collections.defaultdict(list)

    for folder in sorted(p for p in sources.iterdir() if p.is_dir() and re.fullmatch(r"\d{3}_\d", p.name)):
        year, sitting = (int(x) for x in folder.name.split("_"))
        if wanted and year not in wanted:
            continue
        for qpdf in sorted(folder.glob("*_Q.pdf")):
            file_code = qpdf.name[:-6]
            letter = FILE_CODE_TO_LETTER.get(file_code)
            if letter is None:
                fails.append((f"{folder.name}/{qpdf.name}", f"未知科目代碼 {file_code}"))
                continue
            cache = (text_out / f"{year}_{sitting}_{file_code}_Q.txt") if text_out else None
            text = extract_text(qpdf, cache)

            # 題本標頭的粗體字會被重複描好幾次（106-110 尤其明顯），所以比對前先把空白清掉、
            # 也不能用「(」切字串——科目名稱自己就帶括號。
            head = re.sub(r"\s", "", text[:3000])
            if re.sub(r"\s", "", CATEGORY) not in head:
                fails.append((f"{folder.name}/{qpdf.name}", f"題本標頭找不到類科名稱 {CATEGORY}"))
                continue
            subject_name = next((n for n, c in SUBJECT_TO_CODE.items() if c == letter), "")
            # 有幾份題本（例：110_2/33）連科目名稱都是逐段重複描的，整串比對會落空，
            # 所以只比括號前那段（六個科目的前綴互不重複）。
            subject_key = re.sub(r"\s", "", subject_name.split("（")[0])
            if not subject_name or subject_key not in head:
                printed = re.search(r"科目名稱[：:]\s*([^\n]+)", text)
                fails.append((f"{folder.name}/{qpdf.name}",
                              f"科目代碼 {file_code}→{letter} 對不上題本科目名稱："
                              f"{printed.group(1).strip() if printed else '(題本沒有科目名稱)'!r}"))
                continue
            header = SITTING_IN_HEADER.search(text)
            if header:
                header_year, header_sitting = int(header.group(1)), SITTING_WORDS[header.group(2)]
                if (header_year, header_sitting) != (year, sitting):
                    fails.append((f"{folder.name}/{qpdf.name}",f"資料夾 {year}_{sitting} 與題本標頭 {header_year}_{header_sitting} 不符"))
                    continue

            marks = list(QUESTION_MARK.finditer(text))
            kept, discarded = [], []
            for m in marks:
                if int(m.group(1)) == len(kept) + 1:
                    kept.append(m)
                else:
                    discarded.append(text[m.start():m.start() + 60])
            odd = [frag for frag in discarded if not re.match(r"\s*\d+[.．]\d", frag)]
            numbers = [int(m.group(1)) for m in kept]
            sequential = numbers == list(range(1, 81))

            spdf = qpdf.with_name(f"{file_code}_S.pdf")
            mpdf = qpdf.with_name(f"{file_code}_M.pdf")
            if not spdf.exists():
                fails.append((f"{folder.name}/{qpdf.name}","缺標準答案 PDF"))
                continue
            s_text = extract_text(spdf, (text_out / f"{year}_{sitting}_{file_code}_S.txt") if text_out else None)
            original_tokens = parse_answer_table(s_text)
            tokens, notices = original_tokens, {}
            if mpdf.exists():
                m_text = extract_text(mpdf, (text_out / f"{year}_{sitting}_{file_code}_M.txt") if text_out else None)
                tokens = parse_answer_table(m_text)
                notices = parse_notices(m_text)

            papers.append({
                "exam": f"{year}_{sitting}", "subject_code": file_code, "subject": subject_name,
                "letter": letter, "pdf": f"sources/{folder.name}/{qpdf.name}", "found_questions": len(kept),
                "sequence_1_80": sequential, "answer_tokens": len(tokens),
                "original_answer_tokens": len(original_tokens), "corrections": len(notices),
                "discarded_fragments": odd,
            })
            if odd:
                fails.append((f"{folder.name}/{qpdf.name}",f"疑似多餘題號標記 {odd[:3]}"))
                continue
            if not sequential:
                fails.append((f"{folder.name}/{qpdf.name}",f"題號非 1-80（抓到 {len(kept)} 題）"))
                continue
            if len(tokens) != 80 or (original_tokens and len(original_tokens) != 80):
                fails.append((f"{folder.name}/{qpdf.name}",f"答案表不是 80 個（更正 {len(tokens)}／原始 {len(original_tokens)}）"))
                continue

            for i, m in enumerate(kept):
                number = i + 1
                end = kept[i + 1].start() if i + 1 < len(kept) else len(text)
                body = text[m.start():end].strip()
                qid = f"{year}-{sitting}-{letter}-{number:03d}"
                stem, opts, why = split_stem_options(body)
                figure_options = why == "figure_options"
                if why and not figure_options:
                    fails.append((qid, why))
                    continue
                token = tokens[i]
                original = original_tokens[i] if original_tokens else token
                note = None
                revised = False
                entry = notices.get(number)
                if entry:
                    note = build_note(entry, original)
                    revised = True
                    if entry["kind"] == "答案更正":
                        token = entry["accepted"][0]
                    elif token != "#":
                        fails.append((qid, f"公告是{entry['kind']}但更正答案表寫 {token!r}"))
                        continue
                    corrections.append({
                        "id": qid, "kind": entry["kind"], "accepted": entry["accepted"],
                        "notice": entry["notice"], "original_answer": original,
                        "answer_table_len": len(tokens),
                    })
                elif token == "#":
                    fails.append((qid, "答案是 # 但備註裡沒有對應的更正公告"))
                    continue
                if token not in {"A", "B", "C", "D", "#"}:
                    fails.append((qid, f"答案不合法 {token!r}"))
                    continue
                needs_review = bool(figure_options) or body.count("\uFFFD") > 0 or len(stem) < 8
                if needs_review:
                    reviews.append(qid)
                out[(year, sitting, letter)].append({
                    "id": qid, "year": year, "session": sitting, "subject": letter, "number": number,
                    "stem": stem, "options": opts, "answer": token, "answer_note": note,
                    "answer_revised": revised, "topics": [], "difficulty": None,
                    "has_figure": bool(FIGURE_KEYWORD.search(body)) or figure_options, "figures": [],
                    "source": f"sources/{folder.name}/{qpdf.name}", "ingested_at": now,
                    "needs_review": needs_review,
                })

    total = sum(len(v) for v in out.values())
    print(f"題本 {len(papers)} 卷 → 轉出 {total} 題，失敗 {len(fails)} 件，needs_review {len(reviews)} 題，"
          f"更正公告逐題 {len(corrections)} 題")
    bad = {f"{y}-{s}-{c}": len(v) for (y, s, c), v in out.items() if len(v) != 80}
    print("非 80 題的卷：", bad if bad else "無")
    kinds = collections.Counter(c["kind"] for c in corrections)
    print("更正公告分類：", dict(kinds) if kinds else "無")
    for qid, why in fails[:20]:
        print("  失敗", qid, why)

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps({
            "generated_at": now, "papers": papers, "questions": total,
            "failures": [{"id": q, "reason": w} for q, w in fails],
            "needs_review": reviews, "corrections": corrections,
            "correction_kinds": dict(kinds),
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    if not args.out_dir:
        print("（inspect 模式，未寫檔）")
        return 1 if fails else 0
    if fails:
        print("有失敗，先修好再寫檔")
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for (year, sitting, letter), recs in sorted(out.items()):
        recs.sort(key=lambda r: r["number"])
        path = out_dir / f"{year}-{sitting}-{letter}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"已寫出 {len(out)} 個檔到 {out_dir}")

    if args.corrections_out:
        path = Path(args.corrections_out)
        merged: dict[str, dict] = {}
        if path.exists():
            for row in json.loads(path.read_text(encoding="utf-8")):
                merged[row["id"]] = row
        for row in corrections:
            merged[row["id"]] = row
        path.write_text(json.dumps([merged[k] for k in sorted(merged)], ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"更正公告表合併後 {len(merged)} 題 → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
