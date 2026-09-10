# 🩻 醫事放射師國考題庫（NONO 出題基地）

讓 NONO 依大叔的實際程度出題的題庫與自適應出題引擎。
純 Python 標準庫，無外部相依，可直接放進 `NONO基地/cloud`（Google Cloud 同步資料夾）內執行。

---

## 📊 先把「4800 題」這個數字算清楚

專技高考醫事放射師是 **6 科、每科 80 題四選一、全部電腦化測驗**，成績採六科平均 60 分及格制、無單科門檻。

```text
每次考試   = 6 科 × 80 題  =   480 題
每年       = 480 題 × 2 次 =   960 題
5 年       = 960 題 × 5    = 4,800 題   ← 澄羽那份 4800 題的來源
```

所以 **4800 題 = 剛好近 5 年（10 個場次）的完整題目**，不多不少。判讀方式：

| 澄羽那份的狀況 | 代表什麼 |
|---|---|
| 剛好 4800 題且 10 個場次各 480 題 | 近 5 年完整，沒有缺 |
| 4800 題但場次分布不平均 | 有些年份缺題、有些重複，需補 |
| 少於 4800 題 | 直接缺題 |
| 多於 4800 題 | 收錄超過 5 年，或含重複 |

跑 `coverage_report.py` 就會列出「年度 × 科目」矩陣與缺口明細，一眼看出到底缺哪裡。
**在題庫實際匯入之前，無法只憑「4800」這個數字判定完整——必須看場次分布。**

### 六科科目代碼

| 代碼 | 科目 |
|---|---|
| A | 基礎醫學（包括解剖學、生理學、病理學） |
| B | 醫學物理與輻射安全 |
| C | 放射線設備學（包括磁振造影及超音波） |
| D | 放射診斷原理與技術學 |
| E | 放射治療原理與技術學 |
| F | 核子醫學診斷與治療原理及技術學 |

> 科目名稱以考選部命題大綱為準，正本存於 `schema/subjects.json`。珂洛抓題時請以實際題本封面覆核。

---

## 🔄 資料流

```text
考選部考畢試題查詢平臺（PDF 題本 ＋ 標準答案）
        │
        │  ⚠ 雲端 session 連不上 moex.gov.tw（組織 egress policy 擋 403）
        │     必須由珂洛在大叔本機執行
        ▼
  ingest_moex.py inspect   ← 先看版面、確認解析命中率
        ▼
  ingest_moex.py convert   ← 轉成 JSONL，可疑題標 needs_review
        ▼
  data/bank/{年}-{場次}-{科}.jsonl
        ▼
  validate_bank.py         ← fail-closed：有錯就 exit 1
  coverage_report.py       ← 缺口矩陣，回答「收齊了沒」
        ▼
  quiz_engine.py           ← NONO 依程度選題 → 大叔作答 → 更新能力估計
        ▼
  progress/attempts.jsonl  ← 只留本機（Google Cloud 同步），不進公開 repo
```

---

## 📁 目錄

```text
exam-bank/
├── README.md                 本檔
├── HANDOFF_KELUO.md          給珂洛的抓題交接單
├── schema/
│   ├── subjects.json         六科代碼與題數（SSOT）
│   └── question.schema.json  單題 JSON Schema
├── data/
│   ├── raw/                  考選部原始 PDF（本機暫存，不入庫）
│   ├── bank/                 正規化題庫 JSONL ← 題目放這裡
│   └── samples/              格式示範檔（非真實考題，切勿匯入 bank/）
├── tools/
│   ├── ingest_moex.py        PDF → JSONL
│   ├── validate_bank.py      格式與完整性驗證（fail-closed）
│   ├── coverage_report.py    覆蓋率矩陣
│   └── quiz_engine.py        自適應出題引擎
└── progress/                 作答紀錄與能力估計（已 gitignore）
```

---

## 🚀 用法

```bash
# 抓題（珂洛在本機跑）
python3 tools/ingest_moex.py inspect --pdf data/raw/113_1_B.pdf --lines 60
python3 tools/ingest_moex.py convert --pdf data/raw/113_1_B.pdf \
    --year 113 --session 1 --subject B \
    --answers data/raw/113_1_B_ans.txt --out data/bank/113-1-B.jsonl

# 驗證與盤點
python3 tools/validate_bank.py
python3 tools/coverage_report.py
python3 tools/coverage_report.py --markdown > COVERAGE.md

# 出題與作答
python3 tools/quiz_engine.py next   --subject B --count 10   # 給 NONO 讀（不含答案）
python3 tools/quiz_engine.py drill  --subject B --count 5    # 終端機自己練
python3 tools/quiz_engine.py record --qid 113-1-B-042 --chosen C
python3 tools/quiz_engine.py status                          # 看各科程度與弱項
python3 tools/quiz_engine.py rebuild                         # 由作答紀錄重建狀態
```

出題模式：

| `--mode` | 行為 |
|---|---|
| `adaptive`（預設） | 挑預測答對率 ≈ 70% 的題，落在學習效率最高的區間 |
| `weak` | 主攻答對率最低的知識點 |
| `review` | 只出間隔重複到期的錯題 |
| `exam` | 隨機模考，不看程度（模擬真實考場） |

---

## 🧠 能力模型與實測

採 **1PL (Rasch) ＋ 四選一猜對修正**：

```text
P(答對) = 0.25 + 0.75 × sigmoid(θ − b)
θ = 你在該科的能力    b = 題目難度   （同一 logit 尺度）
```

每答一題，θ 依「實際結果 − 預測結果」修正，步長隨作答數遞減（答越多越穩）。
錯題另走 SM-2 lite 間隔重複，到期會被優先排回。

### 為什麼 NONO 應該幫題目標難度

用 4800 題規模的合成題庫、模擬 600 次作答（目標答對率 70%）實測：

| 難度標註狀況 | 穩定後實際答對率 | θ 平均誤差 |
|---|---|---|
| 未標註（`difficulty: null`） | 65.0% | 0.26 |
| 已標註，完全準確 | 69.8% | 0.22 |
| 已標註，±0.5 誤差 | **70.4%** | 0.24 |
| 已標註，±1.0 誤差 | 69.0% | 0.68 |

結論：**難度標得粗略也沒關係，有標就顯著命中學習區**。因為題目第一次出現時引擎不知道它難不難，只能靠科目能力猜；一旦有了 `difficulty`，選題就精準了。所以 NONO 應該分批把題目的 `difficulty` 補上（見 `skills/nono-exam-tutor/SKILL.md`）。

> 上表為合成資料的模擬結果，用來驗證引擎行為，不是真實考生數據。

---

## ⚖️ 授權與隱私

* **考題**：依著作權法第 9 條，「依法令舉行之各類考試試題及其備用試題」不得為著作權之標的，因此考選部歷屆試題可自由重製使用。考選部本身也公開提供考畢試題下載。
* **作答紀錄**：`progress/` 是大叔的個人學習資料，**本 repo 為公開倉庫**，已在 `.gitignore` 排除。實際紀錄請留在本機 `NONO基地/cloud/`，由 Google Cloud 同步。
