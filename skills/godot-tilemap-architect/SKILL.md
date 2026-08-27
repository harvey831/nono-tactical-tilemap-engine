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
> 3. **【交付前強制實機驗證鐵律】(Mandatory Pre-Delivery Verification)**：
>    * 在向大叔回報交付、完成任何修改前，**必須先執行實體引擎自動化驗證**（包含使用 Godot engine headless 實際 `load()` / 實例化所有修改的場景與資源，或執行 TDD 測試），確認 0 解析錯誤 (Parse Error)、0 資源 ID 遺失 (Broken Reference)、0 缺失依賴！未經實機驗證通過前，**絕對禁止**宣告交付！
> 
> **未獲核准或未經實機驗證前，所有生成物一律僅存放於工作快取 (brain) 或獨立開源倉庫，絕不交付不完整的成果！**

---

## 1. 核心開發鐵律：分層語意先，再放圖 (Semantics First, Images Second)

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌟 STEP 1: 定義四層獨立純語意二維矩陣 (4-Layer Pure Semantic Grid Arrays)   │
│    • 地圖以 4 組獨立 2D 矩陣為唯一真相源 (Single Source of Truth, SSOT)：    │
│      1. Layer 1 自然底地語意 ([沙] [路] [石] [田] [渠])                       │
│      2. Layer 2 建築店內佔地語意 (下半部 4~5 行：[吧台] [武架] [藥架] [熔爐]) │
│      3. Layer 2.5 環境雜物語意 ([碎石] [枯草] [木箱] [木桶] [木橋])           │
│      4. Layer 3 屋頂懸垂淡出語意 (上半部 2~3 行：[▲店頂] [▲鐵頂] [▲酒頂])    │
│    • 空間物理語意徹底解耦：屋頂與店內佔地分開獨立行，絕不粗暴全框共用！     │
│    • 建立全局唯一的 BUILDINGS 幾何字典，像素坐標嚴格等於 (gx * 32, gy * 32)！ │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🎨 STEP 2: 建築進店前後雙態徹底解耦 ＆ 100% 統一地基原則                    │
│    • 進店前 (外觀層)：正面木板實體外牆 ＋ 雙開閉合木門 ＋ 門楣大 Logo 招牌   │
│      ＋ 自然人字瓦簷 3/4 俯視斜坡屋頂 (消除死板水平切線，招牌牢固固定)！     │
│    • 進店後 (店內層)：踏入門檻觸發 Roof_Fader 淡出，展現室內人字拼木地板、   │
│      吧台、壁爐、兵器架、鐵砧、藥水貨架與金庫箱！                           │
│    • 100% 統一地基原則：外圈石砌基座、接地陰影與迎賓石階在進店前後完全同源， │
│      切換時保持 0 像素位移與 0 抖動！                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🏬 STEP 3: 建築全面封裝為獨立子場景 (Dedicated Sub-Scene Architecture)       │
│    • 存放於 res://場景/地圖/建築/ 目錄下。                                   │
│    • 內部封裝：店內層 (Sprite2D)、Roof_Fader (Area2D + class_屋頂淡出器)、   │
│      Roof_Exterior_Sprite、CollisionShape2D 門檻感應區與門楣大招牌。         │
│    • 主場景 Visual_Structures_YSort 直接實例化掛載這些子場景！              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🖼️ STEP 4: 無損疊加產出【最終遊戲合併大圖 (Final Merged Map)】              │
│    • 最終合併大圖 100% 由上述四層語意矩陣驅動生成，確保「語意 ⟷ 大圖」       │
│      絕對同源同構、嚴絲合縫！                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 🛠️ STEP 5: 烘焙至 Godot 原生 .tscn 並綁定 Custom Data Layer 戰術屬性        │
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
   * **內容**：田（梯形麥田）、路（自然車轍土路/石板廣場）、屋（店內層 Prefab）、水井、熔爐、桌椅、乾草堆、3/4 樹木。
   * **空間語意規則**：僅覆蓋建築物的實際地基佔地與室內活動行（如 8×6 酒館的下半部 4 行），上方屋頂懸垂區域留空 `[ · ]`，支援標準 Y-Sort 深度排序與遮擋！
3. **【Layer 3: 頭頂屋頂淡出層 (Roofs & Canopies, Z:10)】**：
   * **內容**：3/4 俯視瓦頂、煙囪炊煙、樹冠覆蓋、門楣大招牌。
   * **空間語意規則**：僅覆蓋建築物上半部的屋頂遮蔽投影行（如 8×6 酒館的上半部 3 行），下方外牆立面與大門門廊留空 `[ · ]`！角色踏進門廊時，`Area2D` 平滑 Tween 淡出 (`alpha: 0.0`)。

---

## 3. 視覺透視與有機生活美學規範 (Aesthetic & Perspective Rules)

1. **100% 統一 3/4 斜上方俯視角 (Top-Down 3/4 Oblique)**：
   * **房屋**：俯視梯形瓦片斜面 + 正面直立橡木立面牆 + 雙開閉合木門石階 + 門楣大 Logo 招牌 + 右下立體投影陰影。
   * **樹木**：斜向立體樹冠 + 直立棕色樹幹 + 根系 + 地表陰影（拒絕 90 度平面圓球！）。
   * **水井**：正面圓柱石砌井身 + 木拱架橫樑 + 絞盤滑輪 + 橢圓透視井口波光（拒絕平面圓圈！）。
   * **熔爐與桌椅**：石砌拱頂爐門與鐵砧、木桌面與垂直桌腿。
2. **屋頂與正面立面黃金分割比例 (Golden Ratio Roof & Facade Proportions)**：
   * 屋頂下緣屋簷高度必須精確搭接在正面立面牆頂部（約占總高 40%~50%），為下方的正面木牆、閉合大門、發光窗台與門楣招牌保留 50%~60% 的舒展空間，絕不壓迫大門！
3. **徹底拒絕幾何死板複製 (No Sterile Grid Copy-Paste)**：
   * 道路必須是自然起伏、隨地勢蜿蜒分叉、帶有車轍暗紋與碎石的泥土小徑。
   * 麥田伴隨清澈灌溉水渠自然起伏展開為梯形耕地。
   * 建築依功能錯落佈局（西北雜貨鋪、東北鐵匠鋪、西南酒館、東南農舍），絕不搞十字激光路與方塊複製。
4. **高密度 32×32 像素藝術防退化與 Autotile 禁令 (High-Density 32px Anti-Degradation Rule)**：
   * **【嚴禁 16×16 粗暴平塗降維】**：在 $32\times 32$ 像素網格下，每個單元均相當於高密度微縮畫布（scale * 0.5 像素密度）。**絕對禁止在程式碼中將格子暴力拆成 16×16 平塗色塊或死板 45 度幾何切角**，破壞原本精雕細琢的微風沙紋、石板 1px 倒角高光與勾縫！
   * **【外觀層立面防遺漏強制檢查】**：外觀全景大圖合成時，必須包含「正面厚重半木構造立面牆 ＋ 鉚釘 ＋ 閉合雙開木門 ＋ 鍛鐵合頁」，嚴禁因圖層組裝漏貼而使外牆憑空消失！

---

## 4. 自動波主動煞車原則 (Auto-Approve Active Pause Protocol)

若大叔環境開啟了系統自動核准（Auto-Approve / 自動波），在遇到關鍵美術選型、破壞性場景重寫或重要戰鬥機制調整時，AI **必須主動停止工具調用 (End Turn)**，在對話文字中明確列出審查點，等待大叔手動輸入文字回覆確認後才繼續，絕不盲目順著自動波向下狂飆！

---

## 5. 🗺️ 地圖交付標準報告格式規範 (Mandatory Map Delivery Report Format)

每次完成地圖設計或向大叔/團隊交付成果時，**必須生成一份獨立的互動式 HTML 網頁報告 (`map_delivery_report_<x>_<y>.html`)**，並包含以下核心要素與互動功能，缺一不可：

1. 🔒 **【Base64 100% 內嵌防破圖鐵律 (Zero-Broken-Image Inlining)】**：
   * 報告內所有圖片（合併圖、語意圖、四大分層圖）**必須全面編碼為 Base64 Data URI (`data:image/png;base64,...`) 直接內嵌於 HTML 中**，嚴禁使用外部相對路徑，保證在任何環境下 100% 秒開不破圖！
2. 🖼️ **【合併圖 (Final Merged Map View)】**：
   * 提供「進去前·完整外觀層全景 (Roofs ON)」與「進去後·店內層全景 (Roofs OFF)」一鍵雙態切換！
3. 📑 **【五態切換分層視覺化語意圖 (5-State Visual Semantic Grid SSOT)】**：
   * **徹底取代純字串 ASCII 文本區塊**！以 $1280\times 1280$ 專屬色塊與置中中文 Token 渲染獨立視覺大圖（綜合 SSOT、Layer 1 底地、Layer 2 建築店內、Layer 2.5 雜物、Layer 3 屋頂），支援 Lightbox 800% 逐格放大驗收！
4. 📊 **【戰術屬性對照表 (Tactical Custom Data Layer Table)】**：
   * 完整列出各語意 Token 的 AP 移動消耗、戰術掩體率 (Cover %)、通行規則與特殊機制。
5. 📐 **【四大分層獨立圖 (Discrete Layer-by-Layer Breakdown Views)】**：
   * **Layer 1**：純自然原野底地 (Sand / Ground)。
   * **Layer 2**：人工建築與地景 (Roads, Farmlands, Earthen Ditches, Houses, Wells, Forges, Interiors)。
   * **Layer 2.5**：雜草、碎石、枯木佈置層 (Arid Scrub & Scree Clutter)。
   * **Layer 3**：頭頂屋頂與樹冠淡出層 (Roofs, Canopies, Signboards)。
6. 🔍 **【互動式 Lightbox 像素級無損放大與拖拽 (Pixel-Perfect Lightbox Pan/Zoom)】**：
   * 報告中**所有圖片點擊皆可進入全螢幕 Lightbox 放大模態框**，支援滑鼠滾輪自由放大 (100% ~ 800%) 與按住拖拽平移，保持點陣像素絕對銳利不模糊 (`image-rendering: pixelated`)。
7. 🎛️ **【即時圖層疊加檢驗沙盒 (Interactive Layer Blending Sandbox)】**：
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
│   ├── exterior_[風格]_[建築名]_[尺寸].png  # 進店前完整外觀
│   ├── interior_[風格]_[建築名]_[尺寸].png  # 進店後室內傢俱
│   ├── fader_[風格]_[建築名]_[尺寸].png     # 屋頂淡出層
│   └── sign_[風格]_[建築名]_[尺寸].png      # 門楣大 Logo 招牌
├── 04_環境飾物與植被 (04_Props_Clutter)/   # 雜草、碎石、水井、熔爐、木箱、骨骸
│   └── prop_[風格]_[物件名]_[尺寸]_[34].png
└── 05_TileSet資源庫 (05_TileSet_Resources)/ # Godot 原生 .tres 與 Custom Data 綁定
    └── ts_[生物群系]_[戰術區域]_[解析度].tres
```

### 🏷️ 2. 資產統一命名規範 (Strict Naming Conventions)
所有資產檔名採用蛇形命名法 (`snake_case`)，格式為：
`[類別前綴]_[風格/群系]_[物件描述]_[尺寸]_[透視/狀態].[ext]`
* **類別前綴**：`ground_` (底地), `autotile_` (過渡), `exterior_` (外觀), `interior_` (店內層), `fader_` (淡出屋頂), `sign_` (招牌), `prop_` (飾物/道具), `ts_` (TileSet)。
* **範例**：
  * `exterior_kenshi_tavern_256x192.png` (進店前完整封閉外觀)
  * `interior_kenshi_tavern_256x192.png` (進店後室內吧台與壁爐)
  * `fader_kenshi_tavern_256x192.png` (對應的屋頂淡出層)
  * `sign_kenshi_tavern_beer_64x64.png` (門楣大啤酒杯 Logo 招牌)
  * `prop_kenshi_well_stone_48x48_34.png` (Kenshi 粗木石水井 48x48 3/4 俯視)

### 🛡️ 3. 資產品質與治理硬紅線 (QC & Governance Red Lines)
1. **100% 純淨 Alpha 通道 (Zero Black Border Rule)**：
   * 所有 Prefab 與 Prop 輸出時，背景區域必須為 `RGBA(0, 0, 0, 0)` 完全透明，嚴禁任何 1px 黑色或雜色邊界殘留。
2. **3/4 俯視透視絕對一致性 (Perspective Consistency)**：
   * 建築物、大樹、水井、桌椅、熔爐一律統一為 **3/4 斜上方俯視角**（立面帶投影陰影、垂直物體有高度、水平面有景深），嚴禁混入 90 度正俯視圓球或側視圖形。
3. **生產快取與專案正本物理隔離 (Workspace Isolation)**：
   * AI 生成稿、草案與實驗測試腳本統一留存於工作快取 `brain/scratch/`。
   * 只有通過大叔審查驗收的正式資產，才依命名規範導入專案目錄 `res://圖片/地圖/`，杜絕垃圾與廢稿污染專案庫。



