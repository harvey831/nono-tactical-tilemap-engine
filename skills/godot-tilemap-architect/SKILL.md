---
name: godot-tilemap-architect
description: "Architect, paint, and generate native Godot 4.3+ TileMapLayer tactical battlegrounds, procedural maps, and combat terrain systems. Enforces Semantics-First SSOT pipeline, Civil Architecture layer hierarchy, 3/4 top-down perspective consistency, Custom Data Layer combat mechanics, and organic non-repetitive layout aesthetics."
---

# 🏰 Godot 4 TileMapLayer 戰術地圖架構與繪製手冊 (Godot TileMap Architect)

本技能書規範 AI Agent 在 Godot 4.3+ 專案中，如何直接建置高水準、具備戰鬥效果、透視嚴格統一且符合商業授權的戰棋地圖。

## 0. 🛑 專案寫入防火牆與多 Agent 審查鐵律 (Architecture Review & Approval Firewall)

> [!CAUTION]
> **【改動 Godot 專案的唯一合法流程】**：
> 在將任何演算法生成的圖層、場景 (`.tscn`)、TileSet (`.tres`) 或 GDScript 寫入/修改至 Godot 遊戲專案目錄前，**必須嚴格執行以下雙重防火牆**：
> 1. **向澄羽姐姐架構師提呈正式交接方案 (Handoff to Chengyu)**：
>    * 必須將整合方案（圖層契約、Y-Sort 域、TileSet Custom Data 格式、Bake 方式）撰寫為 Markdown 正本存放於 `docs/outbox_to_chengyu/`，並透過 CLI 提請澄羽姐姐進行架構審查。
>    * **必須獲得澄羽姐姐的正式核准 (Sign-off / Approved)**。
> 2. **向大叔呈報並取得明確動工指令 (Explicit User Approval)**：
>    * 即使澄羽姐姐審查通過，**亦絕對禁止直接動手修改**！
>    * 必須將澄羽姐姐的審查意見與完整計畫端給大叔，**只有在收到大叔明確的「同意」、「開工」指示後，方可執行檔案寫入與指令執行**！
> 
> **未獲雙重核准前，所有生成物一律僅存放於工作快取 (brain) 或獨立開源倉庫，絕不污染 Godot 遊戲本體！**

---

## 1. 核心開發鐵律：分層語意先，再放圖 (Semantics First, Images Second)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌟 STEP 1: 先定義分層純語意二維矩陣 (Define Pure 2D Semantic Grid Arrays)   │
│    • 地圖以 2D 矩陣為唯一真相源 (Single Source of Truth, SSOT)。             │
│    • 在每一層中，每一個網格座標 (x, y) 儲存且僅儲存 1 個專屬語意 Enum ID。   │
│    • 建築物在實體層劃定佔地語意面積 (如 6x5 的 HOUSE_FOOTPRINT)，             │
│      在屋頂層劃定對應的屋頂淡出語意面積 (如 6x3 的 ROOF_FADER_GROUP)。       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🎨 STEP 2: 依據語意矩陣，精準填入 Tile 與整棟 3/4 房子 Prefab              │
│    • 遍歷語意矩陣，依照數值填入對應的 Ground / Road / Farmland Tile。        │
│    • 遇到建築佔地語意面積時，直接放置整棟 3/4 俯視木屋 Prefab，絕不盲目拼貼碎磚！│
│    • 放置 3/4 樹木 (帶樹幹與陰影)、水井 (帶木拱架)、鐵匠熔爐與桌椅。         │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🖼️ STEP 3: 無損疊加產出【最終遊戲合併大圖 (Final Merged Map)】              │
│    • 最終合併大圖 100% 由上述語意矩陣驅動生成，確保「左側語意 ⟷ 右側大圖」   │
│      絕對同源同構、嚴絲合縫！                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🛠️ STEP 4: 烘焙至 Godot 原生 .tscn 並綁定 Custom Data Layer 戰術屬性        │
│    • 物理寫入 TileMapLayer 的 tile_map_data 二進制緩衝區。                   │
│    • GDScript 透過 get_cell_tile_data(pos) 極速查表計算通行、AP消耗與掩體率。│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 建築與地景分層三大核心層次 (Unified 3-Layer Civil Hierarchy)

田、路、屋與人造物全部統一在【人工建築與地景層】，邏輯清晰、不割裂：

1. **【Layer 1: 自然原野底地 (Wilderness Nature Ground, Z:0)】**：
   * **內容**：柔和沙丘、野生草甸、黏土地塊。
   * **職責**：無碰撞純自然背景，消除任何噪點，安靜舒適地襯托上層文明聚落。
2. **【Layer 2: 人工建築與地景層 (Built Civil Structures, Z:2 / `y_sort_enabled = true`)】**：
   * **內容**：田（梯形麥田）、路（自然車轍土路/石板廣場）、屋（4 棟特色大屋 Prefab）、水井、熔爐、桌椅、乾草堆、3/4 樹木。
   * **職責**：田路屋在同一層緊密咬合！角色在道路奔跑、在田埂穿梭、在房屋前後走動均享受標準 Y-Sort 深度排序與遮擋！
3. **【Layer 3: 頭頂屋頂淡出層 (Roofs & Canopies, Z:10)】**：
   * **內容**：3/4 俯視瓦頂、煙囪炊煙、樹冠覆蓋。
   * **職責**：平常遮蔽室內；角色踏進門廊時，`Area2D` 自動平滑 Tween 淡出 (`alpha: 0.0`)，無縫露出室內傢俱與戰鬥空間。

---

## 3. 視覺透視與有機生活美學規範 (Aesthetic & Perspective Rules)

1. **100% 統一 3/4 斜上方俯視角 (Top-Down 3/4 Oblique)**：
   * **房屋**：俯視梯形瓦片斜面 + 正面直立橡木立面牆 + 門窗石階 + 右下立體投影陰影。
   * **樹木**：斜向立體樹冠 + 直立棕色樹幹 + 根系 + 地表陰影（拒絕 90 度平面圓球！）。
   * **水井**：正面圓柱石砌井身 + 木拱架橫樑 + 絞盤滑輪 + 橢圓透視井口波光（拒絕平面圓圈！）。
   * **熔爐與桌椅**：石砌拱頂爐門與鐵砧、木桌面與垂直桌腿。
2. **徹底拒絕幾何死板複製 (No Sterile Grid Copy-Paste)**：
   * 道路必須是自然起伏、隨地勢蜿蜒分叉、帶有車轍暗紋與碎石的泥土小徑。
   * 麥田伴隨清澈灌溉水渠自然起伏展開為梯形耕地。
   * 建築依功能錯落佈局（西北村長宅、東北鐵匠鋪、西南酒館、東南穀倉），絕不搞十字激光路與方塊複製。
3. **整間房屋獨立 Prefab (Whole-House Dedicated Scene)**：
   * 建築物應繪製整間高解析度 3/4 俯視大圖（如 $192\times 160\text{ px}$），並完全解耦獨立屋頂淡出層與室內傢俱層。

---

## 4. 自動波主動煞車原則 (Auto-Approve Active Pause Protocol)

若大叔環境開啟了系統自動核准（Auto-Approve / 自動波），在遇到關鍵美術選型、破壞性場景重寫或重要戰鬥機制調整時，AI **必須主動停止工具調用 (End Turn)**，在對話文字中明確列出審查點，等待大叔手動輸入文字回覆確認後才繼續，絕不盲目順著自動波向下狂飆！

---

## 5. 🗺️ 地圖交付標準報告格式規範 (Mandatory Map Delivery Report Format)

每次完成地圖設計或向大叔/團隊交付成果時，**必須生成一份獨立的互動式 HTML 網頁報告 (`map_delivery_report_<x>_<y>.html`)**，並包含以下三大核心要素與互動功能，缺一不可：

1. 🔒 **【Base64 100% 內嵌防破圖鐵律 (Zero-Broken-Image Inlining)】**：
   * 報告內所有圖片（合併圖、語意圖、四大分層圖）**必須全面編碼為 Base64 Data URI (`data:image/png;base64,...`) 直接內嵌於 HTML 中**，嚴禁使用易因相對路徑或 CORS 失敗的外部引用，保證在任何環境下 100% 秒開不破圖！
2. 🖼️ **【合併圖 (Final Merged Map View)】**：
   * 最終遊戲視角高解析度無損疊加大圖（含底地、建築、飾物、屋頂）。
3. 📑 **【每格文字標籤分層語意圖 (Per-Cell Text Label Semantic Grid)】**：
   * **每一個網格單元 $(x, y)$ 都必須印出專屬的文字標籤 Token**（例如：`[沙]`、`[路]`、`[田]`、`[溝]`、`[屋]`、`[井]`、`[爐]`、`[草]`、`[石]`、`[▲頂]`）。
   * 附帶完整的【語意文字標籤全索引與戰術屬性對照表】（AP 消耗、掩體率、通行規則）。
4. 📐 **【四大分層獨立圖 (Discrete Layer-by-Layer Breakdown Views)】**：
   * **Layer 1**：純自然原野底地 (Sand / Ground)。
   * **Layer 2**：人工建築與地景 (Roads, Farmlands, Earthen Ditches, Houses, Wells, Forges)。
   * **Layer 2.5**：雜草、碎石、枯木佈置層 (Arid Scrub & Scree Clutter)。
   * **Layer 3**：頭頂屋頂與樹冠淡出層 (Roofs & Canopies)。
5. 🔍 **【互動式 Lightbox 像素級無損放大與拖拽 (Pixel-Perfect Lightbox Pan/Zoom)】**：
   * 報告中**所有圖片點擊皆可進入全螢幕 Lightbox 放大模態框**，支援滑鼠滾輪自由放大 (100% ~ 1000%) 與按住拖拽平移，保持點陣像素絕對銳利不模糊 (`image-rendering: pixelated`)。
6. 🎛️ **【即時圖層疊加檢驗沙盒 (Interactive Layer Blending Sandbox)】**：
   * 提供動態 Checkbox，可即時勾選/隱藏任意圖層，方便肉眼逐層 QC 驗收。

---

## 6. 🗄️ 2D 像素地圖資產分類與治理原則 (Asset Taxonomy & Governance Principles)

為確保專案在擴展至 9 大戰區（數十張戰術地圖）時資產井然有序、零命名衝突、易於重構與跨 Agent 協同，所有地圖資產必須嚴格遵守以下分類與治理標準：

### 📁 1. 標準資產目錄體系 (Standard Directory Hierarchy)
專案地圖素材統一存放於 `res://圖片/地圖/` 下，並依功能進行 5 大模組化分類：
```text
res://圖片/地圖/
├── 01_基礎地表 (01_Ground_Biomes)/        # 純底地 Tile (沙地、黏土、草地、地牢石磚)
│   └── ground_[生物群系]_[解析度].png
├── 02_拓撲過渡 (02_Autotile_Transitions)/ # 12~47 拓撲過渡圖塊 (內凹/外凸/平邊/齒狀過渡)
│   └── autotile_[過渡類型]_[解析度]_[47t|9slice].png
├── 03_建築與預製體 (03_Prefabs_Structures)/ # 3/4 完整房屋、工坊、要塞、室內與屋頂淡出層
│   ├── prefab_[風格]_[建築名]_[尺寸]_[主體].png
│   ├── fader_[風格]_[建築名]_[尺寸]_[屋頂淡出].png
│   └── interior_[風格]_[建築名]_[尺寸]_[室內傢俱].png
├── 04_環境飾物與植被 (04_Props_Clutter)/   # 雜草、碎石、水井、熔爐、木箱、骨骸
│   └── prop_[風格]_[物件名]_[尺寸]_[34].png
└── 05_TileSet資源庫 (05_TileSet_Resources)/ # Godot 原生 .tres 與 Custom Data 綁定
    └── ts_[生物群系]_[戰術區域]_[解析度].tres
```

### 🏷️ 2. 資產統一命名規範 (Strict Naming Conventions)
所有資產檔名採用蛇形命名法 (`snake_case`)，格式為：
`[類別前綴]_[風格/群系]_[物件描述]_[尺寸]_[透視/狀態].[ext]`
* **類別前綴**：`ground_` (底地), `autotile_` (過渡), `prefab_` (完整建築), `fader_` (淡出屋頂), `prop_` (飾物/道具), `ts_` (TileSet)。
* **範例**：
  * `prefab_kenshi_house_chief_192x160_34.png` (Kenshi 風格村長大宅 192x160 3/4 俯視)
  * `fader_kenshi_roof_chief_192x160_34.png` (對應的屋頂淡出層)
  * `autotile_sand_clay_32px_47t.png` (沙土與黏土 47-tile 拓撲過渡集)
  * `prop_kenshi_well_stone_48x48_34.png` (Kenshi 粗木石水井 48x48 3/4 俯視)

### 🛡️ 3. 資產品質與治理硬紅線 (QC & Governance Red Lines)
1. **100% 純淨 Alpha 通道 (Zero Black Border Rule)**：
   * 所有 Prefab 與 Prop 輸出時，背景區域必須為 `RGBA(0, 0, 0, 0)` 完全透明，嚴禁任何 1px 黑色或雜色邊界殘留。
2. **3/4 俯視透視絕對一致性 (Perspective Consistency)**：
   * 建築物、大樹、水井、桌椅、熔爐一律統一為 **3/4 斜上方俯視角**（立面帶投影陰影、垂直物體有高度、水平面有景深），嚴禁混入 90 度正俯視圓球或側視圖形。
3. **生產快取與專案正本物理隔離 (Workspace Isolation)**：
   * AI 生成稿、草案與實驗測試腳本統一留存於工作快取 `brain/scratch/`。
   * 只有通過大叔審查驗收的正式資產，才依命名規範導入專案目錄 `res://圖片/地圖/`，杜絕垃圾與廢稿污染專案庫。



