# 📮 交接單：醫放師國考題抓題任務（NONO → 珂洛）

**發出者**：NONO（Claude Code on the web，跑在 Anthropic 雲端容器）
**執行者**：珂洛（大叔本機 Windows Claude Code）
**日期**：2026-09-10

---

## 1. 為什麼要麻煩你

我這個 session 跑在雲端容器裡，對外網路由組織的 egress policy 控管，實測結果：

```text
https://wwwq.moex.gov.tw/exam/wFrmExamQandA.aspx  → CONNECT tunnel failed, 403
https://wwwc.moex.gov.tw/                          → 403
WebFetch(wwwq.moex.gov.tw)                         → EGRESS_BLOCKED
```

只有 GitHub 與套件庫放行。**所以考畢網只能你在本機抓。**
抓完 push 到 GitHub，我這邊就讀得到，接手做正規化、驗證、標難度與出題。

另外：我也讀不到大叔本機的 `NONO基地/cloud/` 資料夾。這個 repo 是我們之間唯一的橋。

---

## 2. 第一優先：先確認澄羽那份到底有沒有 4800 題

大叔想知道澄羽之前做的是不是完整 4800 題。**這件事比重抓還優先**——如果澄羽那份是完整的，就不用重抓了。

```text
4800 題 = 5 年 × 2 次/年 × 6 科 × 80 題
```

請你：

1. 找出澄羽那份題庫檔（可能在 `C:\GPTfile\姐姐大人\` 或她的 sandbox 下）
2. 確認：**總題數**、**涵蓋哪些年度場次**、**每個場次是否各 480 題**
3. 轉成本 repo 的 JSONL 格式（見 `schema/question.schema.json`）推上來
4. 我會跑 `coverage_report.py` 產出「年度 × 科目」缺口矩陣，直接回答大叔

如果格式差太多轉不動，**先把原始檔推上來就好**，格式我來轉。

---

## 3. 要抓什麼

**平臺**：考選部 考畢試題查詢平臺 `https://wwwq.moex.gov.tw/exam/`
**考試**：專門職業及技術人員高等考試醫事人員考試 → **醫事放射師**
**建議範圍**：民國 **110 ～ 115 年**，每年第一次與第二次（12 個場次 = 5,760 題）

> 只要近 5 年就抓 111～115。多抓一年成本很低，題庫大一點選題品質更好。

每個場次需要兩種檔案：

| 檔案 | 說明 |
|---|---|
| 題本 PDF | 6 科各一份 |
| 測驗式試題**標準答案** | 通常另一份 PDF／網頁表格 |

⚠️ 考選部會另外公告**答案更正／送分**。如果有更正版，以更正版為準，並在該題 `answer_note` 註明、`answer_revised` 設 `true`。送分題 `answer` 填 `"#"`。

---

## 4. 檔案放哪、怎麼命名

```text
exam-bank/data/raw/{年}_{場次}_{科目代碼}.pdf          原始題本（已 gitignore，不會進 repo）
exam-bank/data/raw/{年}_{場次}_{科目代碼}_ans.txt      答案檔
exam-bank/data/bank/{年}-{場次}-{科目代碼}.jsonl       正規化題庫 ← 這個要 commit
```

科目代碼：`A` 基礎醫學／`B` 醫學物理與輻射安全／`C` 放射線設備學／`D` 放射診斷／`E` 放射治療／`F` 核子醫學（正本見 `schema/subjects.json`）

答案檔格式很寬鬆，以下兩種都吃：

```text
1 B          或直接一整串：   BBDAC ADBCA ...
2 B
3 D
```

---

## 5. 執行步驟

```bash
cd exam-bank

# ① 先看版面，確認解析命中率（不寫檔）
python3 tools/ingest_moex.py inspect --pdf data/raw/113_1_B.pdf --lines 60

# ② 命中率夠高再轉檔
python3 tools/ingest_moex.py convert --pdf data/raw/113_1_B.pdf \
    --year 113 --session 1 --subject B \
    --answers data/raw/113_1_B_ans.txt \
    --out data/bank/113-1-B.jsonl

# ③ 驗證（有錯會 exit 1）
python3 tools/validate_bank.py

# ④ 盤點覆蓋率
python3 tools/coverage_report.py
```

**版面校正是必要步驟**：不同年度題本排版會變。`inspect` 會印出命中率，如果偏低，請調整 `ingest_moex.py` 裡的 `QUESTION_RE` / `NOISE_RE` / `OPTION_SPLIT_RE`，改完把調整也一起 commit（下次抓別的年份就不用重來）。

`convert` 對任何可疑題目會標 `needs_review: true`（選項不足 4 個、題幹過短、答案缺漏），**不會默默吞掉**。請人工校對後改回 `false`。

### 含圖題怎麼辦

放射科考題有不少判讀圖的題目。純文字抽取抓不到圖，請：

* 該題 `has_figure` 設 `true`
* 圖檔存成 `exam-bank/data/figures/{題號}.png`，路徑填進 `figures`
* 出題引擎預設會排除含圖題（`--include-figures` 才納入），所以就算圖沒補齊也不會出錯題

---

## 6. 推上來

```bash
git checkout claude/exam-questions-organization-mr1mye
git add exam-bank/data/bank exam-bank/tools
git commit -m "feat(exam-bank): 匯入 113 年第 1 次醫事放射師題庫"
git push -u origin claude/exam-questions-organization-mr1mye
```

`data/raw/`（原始 PDF）與 `progress/`（大叔的作答紀錄）已在 `.gitignore` 排除。
**這個 repo 是公開的**，請不要把大叔的個人學習紀錄推上來。

---

## 7. 完成後的驗收清單

- [ ] 澄羽那份的總題數與年度場次分布已確認
- [ ] `python3 tools/validate_bank.py` 通過（exit 0）
- [ ] `python3 tools/coverage_report.py` 每個場次各科都是 80 題
- [ ] `needs_review: true` 的題目都已人工校對
- [ ] 送分題與更正答案都已反映
- [ ] 已 push 到 `claude/exam-questions-organization-mr1mye`

推上來之後跟我說一聲，我接手做知識點標註、難度標註，然後 NONO 就能開始照大叔的程度出題了。

— NONO
