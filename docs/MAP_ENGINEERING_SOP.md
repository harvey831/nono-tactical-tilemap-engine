# 📘 戰術地圖工程 SOP 與方法論 (Tactical Map Engineering SOP)

本手冊沉澱了開發 2D 像素戰棋地圖時的完整工程方法論，適用於人類開發者與 AI Agent 協同作業。

---

## 🌟 核心四大開發鐵律 (Core Protocols)

### 1. 分層語意先，再放圖 (Semantics First, Images Second)
* **單一真理源 (SSOT)**：地圖的本質是 2D 矩陣數據，而非單純的圖片。
* **步驟**：
  1. 先在二維矩陣中定義每一個網格 $(x, y)$ 的專屬語意 Enum Token（如 `[沙]`, `[路]`, `[田]`, `[溝]`, `[屋]`, `[井]`）。
  2. 在實體層劃定建築物的佔地面積（如 $6 	imes 5$），在屋頂層劃定淡出面積（如 $6 	imes 3$）。
  3. 依據語意矩陣遍歷填充對應的 Tile 或整棟 3/4 Prefab。
  4. 疊加輸出最終遊戲大圖，確保「左側語意 $\longleftrightarrow$ 右側大圖」100% 同源同構。

### 2. 建築與地景分層三大層次 (Unified 3-Layer Civil Hierarchy)
* **Layer 1: 自然原野底地 (Wilderness Ground, Z:0)**：純自然無碰撞背景（沙丘、草甸、黏土）。
* **Layer 2: 人工建築與地景層 (Built Civil Structures, Z:2 / Y-Sort)**：田、路、溝、屋、井、爐、桌椅、圍欄全部緊密咬合在同一個文明建築層，角色享受標準 Y-Sort 深度遮擋。
* **Layer 2.5: 雜草碎石飾物層 (Clutter Layer)**：枯黃荒草叢、碎石散礫堆，增強生活感與粗獷氣息。
* **Layer 3: 頭頂屋頂淡出層 (Roofs & Canopies, Z:10)**：3/4 俯視瓦頂或獸皮棚，進門 Area2D 自動平滑淡出。

### 3. 12~47 拓撲 Autotile 邊界過渡 (Autotile Transitions)
* 徹底摒棄 32x32 生硬階梯方塊！
* 依據周圍 8 鄰居（Bitmasking）自動生成：
  * **4 大外凸圓角切角** (Outer Corners: TL, TR, BL, BR)
  * **4 大內凹角自然咬合** (Inner Corners: TL, TR, BL, BR)
  * **4 大平邊邊界齒狀過渡** (Straight Edges: Top, Bottom, Left, Right)

### 4. 物理水文閉環系統 (Connected Hydrology)
* 拒絕斷頭水溝與突兀現代藍色線條！
* 水系必須具備完整物理閉環：**水井/泉眼源頭 $\longrightarrow$ 灌溉主渠 $\longrightarrow$ 田間分水閘門 $\longrightarrow$ 地圖邊界排出**。

---

## 📊 標準交付報告三大要素 (Mandatory Delivery Format)
每次地圖交付必須產出獨立自包含 HTML 報告（Base64 內嵌 100% 防破圖）：
1. 🖼️ **最終合併大圖 (Merged View)**
2. 📑 **每格文字標籤分層語意圖 (Per-Cell Text Labels)**
3. 📐 **四大分層獨立展示圖 (4 Discrete Layer Views)**
4. 🔍 **全圖 Lightbox 1000% 像素級無損滾輪放大 ＋ 即時圖層疊加沙盒**
