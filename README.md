# 🎨 `tactical-tilemap-architect` (TileSet Generation Logic & AI Skill)

[![AI Skill: godot-tilemap-architect](https://img.shields.io/badge/AI%20Skill-godot--tilemap--architect-8a2be2.svg)](skills/godot-tilemap-architect/SKILL.md)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Assets: CC0-1.0](https://img.shields.io/badge/Assets-CC0--1.0-green.svg)](LICENSE)

> 📐 **A Semantics-First, 3/4 Oblique 2D Pixel Art Tactical Map & Autotile Generation Engine**  
> 專注於 **「2D 像素戰術地圖繪製邏輯」、「真高程柱體拓撲分層矩陣」與「12~47 拓撲 Autotile 演算法」** 之純演算法開源工具與 AI Agent 技能庫。

---

## 🎨 這是什麼 Skill 與繪圖邏輯？(Core Logic & Architecture)

本專案將 2D 像素戰棋地圖的繪製流程升級為一套嚴密的 **「真高程柱體拓撲投影管線 ＋ 店內/外觀雙態解耦 ＋ 100% 統一地基」** 之全套原生 Godot 4 戰術地圖架構體系：

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🌟 2D 像素地圖繪製 6 大核心演算法邏輯：                                     │
│ 1. 🎯 【真高程柱體拓撲 SSOT】➔ 40×40 高程網格，每格獨立高度 H，柱體拓撲投影。│
│ 2. 🚪 【進店前後雙態徹底解耦】➔ 外觀 (封閉木牆/閉合木門/門楣大招牌) vs       │
│      店內層 (吧台/壁爐/武器架/藥水架/金庫箱)，踏入大門自動 Roof_Fader 淡出！ │
│ 3. 🧱 【100% 統一地基原則】➔ 外圈石砌基座、接地陰影與迎賓石階完全同源 0 偏移！│
│ 4. 🛖 【黃金比例 3/4 俯視透視】➔ 屋簷精確搭接於木牆頂部，為正面留出 60% 立面。│
│ 5. 🏬 【獨立建築子場景架構】➔ res://場景/地圖/建築/*.tscn 封裝店內層與淡出器。│
│ 6. 📊 【全規格 Base64 交付報告】➔ 800% 像素級滾輪放大 ＋ 14 張圖 0 漏底驗收。 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📐 核心繪製管線：v2 真高程柱體拓撲 (v2 Pipeline Breakdown)

> [!CAUTION]
> **【歷史版本作廢聲明】**：
> 2026-08 舊版的 `nono_layered_village_builder.py` 以及使用 CSS 暴力位移推位置的舊版 HTML report **已全數作廢**！
> 舊版純依賴 2D 平面圖層疊加與 CSS 偏移，無法呈現物理高差遮擋、側壁立面 run 與真實剖面。

現已全面升級為 **v2 真高程柱體拓撲管線 (v2 Column & Run Elevation Pipeline)**：

### 1. 真高程資料流 (True Heightfield SSOT)
地圖的底層核心是 40×40 的整數高程矩陣（$H \in [-2, 6]$）：
* **負高程地景**：`H-2`（深水）、`H-1`（淺水/水渠）。
* **基準地表**：`H0`（荒漠平原/農田/車道）。
* **戰術高地**：`H1`~`H3`（岩石高台/扼守北門哨塔/斷崖立面）。
* **建築與屋頂**：`H2`~`H6`（民居、鐵匠鋪、酒館之立面、室內樓板與平台甲板）。

### 2. 幾何投影與光柵化 (Column & Run Projection)
* **頂點級微移投影**：$\Delta Y = 0.72 \times \text{tile\_h} \times H$，隨視角傾斜微移 $\Delta X = 0.12 \times \text{tile\_w} \times H$，光柵化時整數取整杜絕撕裂。
* **側壁立面豎向 Run (R13/R14)**：高差立面統一歸較高格繪製，立面圖塊採用 BOX 壓縮切片（每級 23px 高），片與片之間零插值。
* **剖面即時切片**：同一三維語意模型，以高度為界動態切開柱芯，暴露底層室內與地貌，非人工繪製假圖。

---

## 🚀 快速開始與執行方式 (Quick Start: Run v2 Pipeline)

執行完整的 v2 規格組裝器與像素渲染引擎：

```bash
# 1. 執行規格組裝器：由高程網格與語意 Prefabs 編譯生成 chunk_spec_v2.json
python src/build_chunk_0_0_spec_v2.py

# 2. 執行像素渲染引擎：計算 2.5D 柱體投影，輸出 14 張完整交付圖與互動式 HTML 驗收報告
python src/render_chunk_0_0_v2.py
```

### 產出套件 (Artifacts)
* **交付視圖 (4 張)**：`reports/v2_all.png` (全景合成)、`reports/v2_exterior.png` (完整外觀)、`reports/v2_interior.png` (店內透視)、`reports/v2_base.png` (純底地)。
* **全剖面切片 (11 張)**：`reports/v2_cut_H*.png` (從 $H=-2$ 到 $H=6$ 逐層切片)。
* **多視角檢驗 (2 張)**：`reports/v2_cam_left.png`、`reports/v2_cam_right.png` (左右角度走查)。
* **驗收檢視器**：`reports/v2_report.html` (Base64 內嵌圖檔、800% Lightbox 放大、14 張圖 0 洞掃描認證)。

---

## 📜 開源協議 (License)

* **演算法與代碼 (Code)**：採用 [MIT License](LICENSE) 開源。
* **像素美術資產 (Pixel Assets)**：採用 [CC0 1.0 Universal (Public Domain)](https://creativecommons.org/publicdomain/zero/1.0/) 全球公有領域授權，任何人皆可免費商用、修改與發布！

---
*Created with ❤️ and Pure Code by Nova (Nono) - Extreme Aesthetics AI Software Architect.*
