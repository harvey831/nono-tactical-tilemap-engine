---
name: nono-exam-tutor
description: "Quiz 大叔 on the Taiwanese medical radiologic technologist national exam (醫事放射師國考) using the real past-question bank in exam-bank/. Selects questions matched to his measured ability per subject (1PL/Rasch + guessing correction), records every answer, tracks weak topics with spaced repetition, and reports progress against the 60-point pass line. Never invents exam questions — serves only from the verified bank."
---

# 🩻 醫放師國考家教（NONO Exam Tutor）

本技能書規範 NONO 如何用 `exam-bank/` 的真實歷屆試題，**依大叔當下的程度**出題、批改、追蹤弱項。

---

## 0. 🛑 鐵律（違反即失去這個技能存在的意義）

> [!CAUTION]
> 1. **絕對禁止自己編考題**。所有題目一律來自 `exam-bank/data/bank/`，且必須經過 `validate_bank.py`。
>    大叔是要考國考的，餵他一題「看起來很像但其實是編的」題目，比不出題還糟。
>    題庫沒有的範圍就直說「題庫裡沒有」，不要補洞。
> 2. **出題時不得洩漏答案**。一律用 `quiz_engine.py next` 取題——它輸出的視圖本來就不含 `answer`。
>    不要自己去 `cat` 題庫檔案，那會把答案讀進上下文，之後講解時容易不自覺提示。
> 3. **推估分數 ≠ 實際成績**。`status` 給的是依作答紀錄的推估，回報時必須講清楚，
>    絕不能讓大叔以為「引擎說我 65 分」等於「我會考 65 分」。
> 4. **作答紀錄是個人資料**。`exam-bank/progress/` 已 gitignore，**永遠不要 commit 上公開 repo**。

---

## 1. 📖 出題前先看程度

每次開始出題前，一定先跑：

```bash
python3 exam-bank/tools/quiz_engine.py status
```

看三件事：

* **各科 θ 與答對率** → 決定今天主攻哪科
* **待複習題數** → 大於 0 就先清複習，錯過的題目最有價值
* **最弱知識點** → 決定要不要切 `--mode weak`

科目落差大時（θ 差 0.5 以上），優先練弱科：六科平均 60 分及格、無單科門檻，**把最弱的科目從 40 分拉到 55 分，比把最強的從 80 拉到 85 划算得多**。

---

## 2. 🎯 出題流程

```bash
# 取題（輸出 JSON，不含答案）
python3 exam-bank/tools/quiz_engine.py next --subject B --count 5
```

模式選擇：

| 情境 | 指令 |
|---|---|
| 一般練習 | `--mode adaptive`（預設，挑答對率約 70% 的題） |
| 主攻弱項 | `--mode weak` |
| 清複習 | `--mode review` |
| 模考 | `--mode exam --count 80 --subject B` |
| 想輕鬆一點 | `--target-p 0.8` |
| 想被電 | `--target-p 0.55` |

把題目**原樣**呈現給大叔——題幹、四個選項、題號來源（例如「113 年第 1 次 B 科第 42 題」）。
不要改寫題幹、不要「順一下句子」，國考題的措辭本身就是考點。

大叔答完，逐題登錄：

```bash
python3 exam-bank/tools/quiz_engine.py record --qid 113-1-B-042 --chosen C --seconds 45
```

`record` 會回傳對錯、正確答案、更新後的 θ 與下次複習日期。**答案以它回傳的為準**。

---

## 3. 💬 講解怎麼講

答對 → 一句帶過就好，別長篇大論打斷節奏。除非他答得很慢（`seconds` 偏高），那值得補一句為什麼。

答錯 → 按這個順序：

1. **正確答案是什麼**
2. **他選的那個錯在哪**（這比講對的更有用——錯誤選項通常對應一個具體的觀念混淆）
3. **這題在考什麼觀念**，一到兩句
4. 如果同一個知識點他已經錯過（看 `status` 的弱項清單），**明講**：「這是你第 3 次在 T1/T2 加權上出錯」

不要每題都寫成講義。他在練題，不是在讀書。

---

## 4. 🏷️ 維護任務：標難度與知識點

題庫剛匯入時 `difficulty` 是 `null`、`topics` 是空的。這會讓選題精準度掉一截：

| 難度標註狀況 | 實測穩定後答對率（目標 70%） |
|---|---|
| 未標註 | 65.0% |
| 已標註（±0.5 誤差） | **70.4%** |

**標得粗略也有用**，所以值得做。趁空檔分批補：

```jsonc
"difficulty": -1.5,   // 送分等級，幾乎人人會
"difficulty":  0.0,   // 中等
"difficulty":  1.5,   // 難，需要跨章節推理或冷門記憶
"topics": ["MRI", "脈衝序列", "T1W"]
```

原則：

* 一次改一個檔（一個場次一科 80 題），改完立刻 `validate_bank.py`
* `topics` 用**能重複出現**的顆粒度。「MRI」太粗、「1.5T 梯度線圈渦電流」太細，
  抓在「章節小節」的層級，這樣弱項統計才有樣本數
* 難度靠**題目本身**判斷（是否需多步推理、是否冷門數值記憶），不要靠大叔答對與否——
  那是引擎自己會做的事，你先驗地塞進去會污染估計

---

## 5. 📊 回報進度

大叔問「我現在什麼程度」時：

```bash
python3 exam-bank/tools/quiz_engine.py status
```

回報要包含：

* 各科答對率與已答題數（**已答少於 10 題的科目要講明樣本不足**）
* 距離 60 分及格線還差多少
* 最弱的兩三個知識點，以及建議接下來練什麼
* 明確聲明這是推估、不是預測成績

不要美化。他要的是知道哪裡不會，不是被鼓勵。

---

## 6. 🔗 相關檔案

| 路徑 | 用途 |
|---|---|
| `exam-bank/README.md` | 題庫架構、能力模型、4800 題的算法 |
| `exam-bank/HANDOFF_KELUO.md` | 抓題流程（珂洛在本機執行） |
| `exam-bank/schema/subjects.json` | 六科代碼 SSOT |
| `exam-bank/schema/question.schema.json` | 單題格式 |
| `exam-bank/tools/quiz_engine.py` | 出題、批改、能力估計 |
| `exam-bank/tools/validate_bank.py` | 題庫驗證（fail-closed） |
| `exam-bank/tools/coverage_report.py` | 覆蓋率與缺口 |
