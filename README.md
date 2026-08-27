# 🎨 `tactical-tilemap-architect` (TileSet Generation Logic & AI Skill)

[![AI Skill: tactical-tilemap-architect](https://img.shields.io/badge/AI%20Skill-tactical--tilemap--architect-8a2be2.svg)](skills/tactical-tilemap-architect/SKILL.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Assets: CC0-1.0](https://img.shields.io/badge/Assets-CC0--1.0-green.svg)](LICENSE)

> 📐 **A Semantics-First, 3/4 Oblique 2D Pixel Art Tactical Map & Autotile Generation Engine**  
> 專注於 **「2D 像素戰術地圖繪製邏輯」、「分層語意拓撲矩陣」與「12~47 拓撲 Autotile 演算法」** 之純演算法開源工具與 AI Agent 技能庫。

---

## 🎨 這是什麼 Skill 與繪圖邏輯？(Core Logic & Architecture)

本專案將 2D 像素戰棋地圖的繪製流程升級為一套嚴密的 **「四層獨立純語意 SSOT 管線 ＋ 店內/外觀雙態解耦 ＋ 100% 統一地基」** 之全套原生 Godot 4 戰術地圖架構體系：

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌟 2D 像素地圖繪製 6 大核心演算法邏輯：                                     │
│ 1. 🎯 【四層獨立純語意 SSOT 矩陣】➔ 底地、店內/本體、雜物、屋頂 4 組獨立矩陣。│
│ 2. 🚪 【進店前後雙態徹底解耦】➔ 外觀 (封閉木牆/閉合木門/門楣大招牌) vs       │
│      店內層 (吧台/壁爐/武器架/藥水架/金庫箱)，踏入大門自動 Roof_Fader 淡出！ │
│ 3. 🧱 【100% 統一地基原則】➔ 外圈石砌基座、接地陰影與迎賓石階完全同源 0 偏移！│
│ 4. 🛖 【黃金比例 3/4 俯視透視】➔ 屋簷精確搭接於木牆頂部，為正面留出 60% 立面。│
│ 5. 🏬 【獨立建築子場景架構】➔ res://場景/地圖/建築/*.tscn 封裝店內層與淡出器。│
│ 6. 📊 【全規格 Base64 交付報告】➔ 800% 像素級滾輪放大 ＋ 即時圖層疊加沙盒。   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📐 核心繪製演算法解析 (Algorithmic Breakdown)

### 1. 四層獨立純語意優先管線 (4-Layer Semantics-First SSOT)
地圖的底層是 4 組完全解耦的 2D 矩陣數據：
* **Layer 1 自然原野底地**：`[沙]`, `[路]`, `[石]`, `[田]`, `[渠]`。
* **Layer 2 建築店內層與本體**：`[吧台]`, `[武架]`, `[藥架]`, `[鐵砧]`, `[熔爐]`, `[水井]`, `[果攤]`。
* **Layer 2.5 環境雜物佈置層**：`[碎石]`, `[枯草]`, `[木箱]`, `[酒桶]`, `[木橋]`。
* **Layer 3 頭頂屋頂淡出層**：`[▲店頂]`, `[▲鐵頂]`, `[▲酒頂]`, `[▲塔頂]`, `[▲棚頂]`。
* 建立全局唯一的 `BUILDINGS` 幾何字典，**像素座標嚴格對齊 `(gx * 32, gy * 32)`**，保證「語意矩陣 $\longleftrightarrow$ 遊戲大圖」100% 數學級同源同構！

### 2. 建築進店前後雙態解耦 ＆ 100% 統一地基原則 (Exterior vs Interior Decoupling)
* **進店前（完整封閉外觀·Roofs ON）**：擁有正面木板實體外牆、雙開加固閉合木門、發光窗戶、門楣牢固大 Logo 招牌（啤酒杯/戰鎚/魔藥）與 3/4 屋頂，絕非露天，招牌絕不浮空！
* **進店後（店內層·Roofs OFF / Faded）**：角色踏入門檻觸發 `Roof_Fader` 淡出，露出室內精緻木地板、吧台、長桌、壁爐、武器架、鐵砧、藥水貨架與掌櫃天秤！
* **100% 統一地基**：外圈石砌基座、接地陰影與迎賓石階在進店前後完全同源，切換時保持 0 像素偏移與 0 抖動！

### 3. 獨立建築子場景封裝 (Dedicated Sub-Scene Architecture)
* 所有建築全面封裝為 Godot 獨立子場景（存放於 `res://場景/地圖/建築/*.tscn`）。
* 內部封裝：`店內層_Interior` (Sprite2D)、`Roof_Fader` (Area2D + `class_屋頂淡出器`)、`Roof_Exterior_Sprite`、`CollisionShape2D` 門檻感應區與門楣大招牌。
* 主場景 `Visual_Structures_YSort` 直接實例化掛載，架構清晰模組化！

### 4. 標準 12~47 拓撲 Autotile 邊界過渡 (Autotile Transitions)
徹底消除 32x32 生硬階梯方塊！
* **外凸圓角 (Outer Corners)**：TL, TR, BL, BR（自然外弧切角）
* **內凹角 (Inner Corners)**：TL, TR, BL, BR（自然咬合補齊）
* **平邊邊界 (Straight Edges)**：Top, Bottom, Left, Right（齒狀散沙過渡）

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
