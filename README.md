# 🎨 `tactical-tilemap-architect` (TileSet Generation Logic & AI Skill)

[![AI Skill: tactical-tilemap-architect](https://img.shields.io/badge/AI%20Skill-tactical--tilemap--architect-8a2be2.svg)](skills/tactical-tilemap-architect/SKILL.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Assets: CC0-1.0](https://img.shields.io/badge/Assets-CC0--1.0-green.svg)](LICENSE)

> 📐 **A Semantics-First, 3/4 Oblique 2D Pixel Art Tactical Map & Autotile Generation Engine**  
> 專注於 **「2D 像素戰術地圖繪製邏輯」、「分層語意拓撲矩陣」與「12~47 拓撲 Autotile 演算法」** 之純演算法開源工具與 AI Agent 技能庫。

---

## 🎨 這是什麼 Skill 與繪圖邏輯？(Core Logic & Architecture)

本專案將 2D 像素戰棋地圖的繪製流程升級為一套嚴密的 **「SSOT 語意優先繪製管線 (Semantics-First Painting Pipeline)」**，徹底告別傳統手繪拼貼容易產生的斷邊、透視混亂與死板幾何感：

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌟 2D 像素地圖繪製 5 大核心演算法邏輯：                                     │
│ 1. 🎯 【SSOT 語意矩陣先行】➔ 每格嚴格配置單一語意 Token，先算結構再填圖形。  │
│ 2. ⚔️ 【3/4 俯視角微觀像素雕琢】➔ 6 階色相偏移 (Hue-Shift)、光影體積感、無黑邊。│
│ 3. 📐 【12~47 拓撲 Autotile 演算】➔ 8 鄰居二進制遮罩，自動內凹/外凸/平邊齒狀。│
│ 4. 🌊 【水文閉環流動邏輯】➔ 泉眼/水井源頭 ➔ 水道分流 ➔ 邊界自然排出。       │
│ 5. 📊 【Base64 自包含驗收報告】➔ 1000% 像素級滾輪放大 ＋ 即時圖層疊加沙盒。  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📐 核心繪製演算法解析 (Algorithmic Breakdown)

### 1. 分層語意優先管線 (Semantics-First SSOT)
地圖的底層是 2D 矩陣數據：
* 先在二維矩陣中定義每一個網格 $(x, y)$ 的語意 Token（如 `[沙]`, `[路]`, `[田]`, `[溝]`, `[屋]`, `[井]`）。
* 劃定建築佔地面積與屋頂淡出區域。
* 遍歷語意矩陣，依照數值自動驅動對應的像素 Tile 或 3/4 大 Prefab 填充。
* 無損疊加輸出合併大圖，保證「語意矩陣 $\longleftrightarrow$ 遊戲大圖」100% 同源同構！

### 2. 標準 12~47 拓撲 Autotile 邊界過渡 (Autotile Transitions)
徹底消除 32x32 生硬階梯方塊！
* **外凸圓角 (Outer Corners)**：TL, TR, BL, BR（自然外弧切角）
* **內凹角 (Inner Corners)**：TL, TR, BL, BR（自然咬合補齊）
* **平邊邊界 (Straight Edges)**：Top, Bottom, Left, Right（齒狀散沙過渡）

### 3. 三大建築與地景分層邏輯 (Civil Hierarchy)
* **Layer 1: 自然原野底地 (Wilderness Ground)**：純背景自然地表（沙丘、草甸、黏土）。
* **Layer 2: 人工建築與地景層 (Built Civil Structures)**：田、路、溝、屋、井、爐緊密咬合在同一層，支援 Y-Sort 深度遮擋。
* **Layer 2.5: 雜草碎石飾物層 (Clutter Layer)**：枯黃草叢、碎石散礫堆，增強粗獷自然質感。
* **Layer 3: 頭頂屋頂淡出層 (Roofs & Canopies)**：3/4 俯視瓦頂或獸皮棚，進門時平滑淡出。

---

## 🖼️ 成果展示 (Showcase)

| 1. 最終合併大圖 (1280x1280) | 2. 1,600 格每格文字標籤分層語意圖 (SSOT) |
| :---: | :---: |
| ![Merged Map](assets/kenshi_village_merged_1280.png) | ![Semantic Grid](assets/kenshi_village_per_cell_text_labels.png) |
| **3/4 廢土風貌與連通水系** | **每格標註 [沙][路][田][溝][屋][井][爐][草][石][▲頂]** |

---

## 🚀 快速開始 (Quick Start)

### 執行地圖生成演算法
```bash
pip install pillow numpy
python src/nono_tilemap_engine.py
# 開啟 reports/map_delivery_report_0_0_village.html 查看可放大成果
```

---

## 📜 開源協議 (License)

* **演算法與代碼 (Code)**：採用 [MIT License](LICENSE) 開源。
* **像素美術資產 (Pixel Assets)**：採用 [CC0 1.0 Universal (Public Domain)](https://creativecommons.org/publicdomain/zero/1.0/) 全球公有領域授權，任何人皆可免費商用、修改與發布！

---
*Created with ❤️ and Pure Code by Nova (Nono) - Extreme Aesthetics AI Software Architect.*
