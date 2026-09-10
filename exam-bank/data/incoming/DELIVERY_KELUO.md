# 投遞說明（珂洛 → NONO，2026-09-10）

依 `incoming/README.md` 把澄羽既有題庫原樣送來。目錄結構與檔名保持她原本的樣子，沒有重新命名或合併。

來源：大叔本機 `C:\GPTfile\姐姐大人\study_radiographer\`

## 送了什麼

```text
study_radiographer/
  index/              ← 正規化要用的主檔
    questions.jsonl        4,800 題（id / exam / subject / number / text_extracted / figure_keyword …）
    teacher_answers.jsonl  4,800 答案（answer_token，送分題為 "#"，含 correction_notes）
    papers.json            60 卷的來源與頁碼對照
    corrections.json       答案更正彙整
    question_topics.csv    自動關鍵字候選標籤（僅候選，需核對主考點）
    validation.json        她的驗證摘要
  text/               145 份 PDF 的純文字抽取（60 原卷 + 60 答案 + 25 更正）
  readable_full_bank/ 六科的人可讀版（questions / teacher_answers 各一份）
  work/               index_sources.py（她的索引腳本）、download_sources.ps1（她的下載腳本）
  CATALOG.md          10 場 × 6 科的官方來源頁與檔案對照
  VALIDATION.md       她自己的檢查紀錄與「尚未宣稱完成」的誠實清單
  README.md / TOPICS.md / PHYSICS_TOPIC_INDEX.md / NONO_TUTOR_BRIEF.md
```

共 173 檔、8.7 MB。

## 沒送什麼，為什麼

| 沒送 | 原因 |
|---|---|
| `sources/` 的 145 份原始 PDF（58 MB） | 二進位進公開 repo 是不可逆的歷史膨脹，而正規化用不到——`text/` 已有全部抽取文字，`index/` 已有結構化題與答案。**你要的話跟大叔說一聲，我隨時補推**（例如要處理那 22 題圖／公式選項時） |
| `attempts.csv`、`learning_progress.csv` | 大叔的個人作答與學習進度，依 `incoming/README.md` 與交接單第 6 節不入公開 repo |

## 我另外做了轉檔，你可以直接用或整包丟掉

看到 `incoming/README.md` 之前我已經照 `schema/question.schema.json` 轉好並驗過了，就一起留著：

* `data/bank/*.jsonl` 60 檔 4,800 題
* `tools/import_chengyu_bank.py` 轉檔腳本（純標準庫，可重跑）
* `IMPORT_REPORT_KELUO.md` 完整報告

`validate_bank.py` 通過（exit 0），`coverage_report.py` 4800/4800 剛好達標。

**轉檔規則的所有權還是你的**：如果你的規則跟我不一樣，`incoming/` 這份原始資料是完整的，
直接重跑你自己的正規化覆蓋 `data/bank/` 就好，不用問我。我不會再動 `data/bank/`。

要看我怎麼切的，重點只有一條：`text_extracted` 形如 `{題號}.{題幹}\nA.{選項}\nB....`，
以行首 `[A-D].` 為界切；切出來選項是空的那 21 題，是**選項本身為圖或公式**（sinogram、影像遮罩、
假體影像、照野平坦性公式），我填了佔位並標 `has_figure` + `needs_review`。細節在 `IMPORT_REPORT_KELUO.md`。

— 珂洛
