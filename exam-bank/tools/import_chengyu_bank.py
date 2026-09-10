# -*- coding: utf-8 -*-
"""澄羽 study_radiographer 題庫 → nono-tactical-tilemap-engine/exam-bank 的 JSONL 格式。

來源：C:/GPTfile/姐姐大人/study_radiographer/index/{questions,teacher_answers}.jsonl（4800 題，10 場 × 6 科 × 80）
輸出：exam-bank/data/bank/{年}-{場次}-{科目代碼}.jsonl

切分規則：text_extracted 形如 "{題號}.{題幹}\nA.{選項}\nB....\nC....\nD...."，
以行首 [A-D]. 為界切出四個選項，其餘為題幹。切不出來的標 needs_review。
"""
import argparse, io, json, os, re, sys, collections
from datetime import datetime, timezone

DEFAULT_SRC = r"C:/GPTfile/姐姐大人/study_radiographer/index"   # 澄羽本機題庫（大叔 Windows）

# 澄羽用考選部題本上的科目全名；對到 exam-bank schema/subjects.json 的 A-F
SUBJECT_TO_CODE = {
    "基礎醫學（包括解剖學、生理學與病理學）": "A",
    "醫學物理學與輻射安全": "B",
    "放射線器材學（包括磁振學與超音波學）": "C",
    "放射線診斷原理與技術學": "D",
    "放射線治療原理與技術學": "E",
    "核子醫學診療原理與技術學": "F",
}

OPTION_LINE = re.compile(r"(?m)^[ \t]*([A-D])[.．][ \t]*")


FIGURE_OPTION = "（此選項為圖／公式，請看原卷 PDF）"


def split_stem_options(text: str):
    """回 (stem, {A..D}, 失敗原因或 None)。四個選項標記必須依序 A B C D 各出現一次。"""
    marks = [(m.start(), m.end(), m.group(1)) for m in OPTION_LINE.finditer(text)]
    firsts = {}
    for start, end, letter in marks:
        firsts.setdefault(letter, (start, end))
    if set(firsts) != {"A", "B", "C", "D"}:
        return None, None, f"選項標記不全（找到 {sorted(firsts)}）"
    order = sorted(firsts.items(), key=lambda kv: kv[1][0])
    if [k for k, _ in order] != ["A", "B", "C", "D"]:
        return None, None, "選項順序非 A→B→C→D"
    stem = text[: order[0][1][0]].strip()
    opts = {}
    for i, (letter, (start, end)) in enumerate(order):
        stop = order[i + 1][1][0] if i + 1 < len(order) else len(text)
        opts[letter] = re.sub(r"\s+", " ", text[end:stop]).strip()
    # 題幹開頭的 "12." 題號去掉
    stem = re.sub(r"^\d{1,3}[.．]\s*", "", stem)
    stem = re.sub(r"[ \t]+", " ", stem).strip()
    if not stem:
        return None, None, "題幹為空"
    empty = [k for k, v in opts.items() if not v]
    if empty:
        # 選項本身是圖或公式（sinogram／遮罩／假體影像／數學式），純文字抽不出來。
        # 依交接單：填佔位、標 has_figure 與 needs_review，出題引擎預設排除含圖題，不會出錯題。
        for k in empty:
            opts[k] = FIGURE_OPTION
        return stem, opts, "figure_options"
    return stem, opts, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", help="輸出 data/bank 目錄；不給就只做 inspect 不寫檔")
    ap.add_argument("--src", default=DEFAULT_SRC, help="澄羽 index 目錄（questions.jsonl / teacher_answers.jsonl）")
    args = ap.parse_args()

    qs = [json.loads(l) for l in io.open(os.path.join(args.src, "questions.jsonl"), encoding="utf-8") if l.strip()]
    ans = {}
    for l in io.open(os.path.join(args.src, "teacher_answers.jsonl"), encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            ans[r["id"]] = r

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    out = collections.defaultdict(list)
    fails, reviews = [], []

    for q in qs:
        src_id = q["id"]
        year_s, session_s = src_id.split("-")[0], src_id.split("-")[1]
        year, session = int(year_s), int(session_s)
        code = SUBJECT_TO_CODE.get(q["subject"])
        if code is None:
            fails.append((src_id, f"未知科目 {q['subject']!r}"))
            continue
        number = int(q["number"])
        stem, opts, why = split_stem_options(q["text_extracted"])
        needs_review = False
        figure_options = why == "figure_options"
        if why and not figure_options:
            fails.append((src_id, why))
            continue
        if figure_options:
            needs_review = True
            reviews.append(src_id)
        a = ans.get(src_id, {})
        token = (a.get("answer_token") or "").strip().upper()
        note = (a.get("correction_notes") or "").strip() or None
        if token not in {"A", "B", "C", "D", "#"}:
            fails.append((src_id, f"答案不合法 {token!r}"))
            continue
        # 澄羽已標：全庫需人工看原卷（PDF 抽取可能漏上下標／圖）
        if q.get("unreadable_characters") or len(stem) < 8:
            needs_review = True
            if src_id not in reviews: reviews.append(src_id)
        rec = {
            "id": f"{year}-{session}-{code}-{number:03d}",
            "year": year,
            "session": session,
            "subject": code,
            "number": number,
            "stem": stem,
            "options": opts,
            "answer": token,
            "answer_note": note,
            "answer_revised": bool(note),
            "topics": [],
            "difficulty": None,
            "has_figure": bool(q.get("figure_keyword")) or figure_options,
            "figures": [],
            "source": q.get("pdf"),
            "ingested_at": now,
            "needs_review": needs_review,
        }
        out[(year, session, code)].append(rec)

    total = sum(len(v) for v in out.values())
    print(f"來源 {len(qs)} 題 → 轉出 {total} 題，切分失敗 {len(fails)} 題，標 needs_review {len(reviews)} 題")
    if fails:
        print("失敗樣本：")
        for i, (qid, why) in enumerate(fails[:15]):
            print(f"  {qid}  {why}")
        c = collections.Counter(w for _, w in fails)
        print("失敗原因分布：", dict(c.most_common(8)))
    bad = {k: len(v) for k, v in out.items() if len(v) != 80}
    print("非 80 題的卷：", bad if bad else "無（60 卷全部 80 題）")

    if not args.out_dir:
        print("\n（inspect 模式，未寫檔。加 --out-dir 才輸出）")
        return 0 if not fails else 1

    os.makedirs(args.out_dir, exist_ok=True)
    for (year, session, code), recs in sorted(out.items()):
        recs.sort(key=lambda r: r["number"])
        path = os.path.join(args.out_dir, f"{year}-{session}-{code}.jsonl")
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"已寫出 {len(out)} 個檔到 {args.out_dir}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
