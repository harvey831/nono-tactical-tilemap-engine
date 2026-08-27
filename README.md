# 🏰 Nono Tactical TileMap Engine (`nono-tactical-tilemap-engine`)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Assets: CC0-1.0](https://img.shields.io/badge/Assets-CC0--1.0-green.svg)](https://creativecommons.org/publicdomain/zero/1.0/)
[![Godot Engine](https://img.shields.io/badge/Godot-4.3%2B-blue.svg)](https://godotengine.org/)
[![AI Agent Skill](https://img.shields.io/badge/AI%20Skill-Ready-purple.svg)](skills/godot-tilemap-architect/SKILL.md)

> **A Semantics-First, 3/4 Oblique Pixel Art Tactical Map & Autotile Generation Engine for Godot 4.x.**  
> 由 AI 軟體架構師 **諾瓦 (Nova / Nono)** 親手設計並 100% 演算法程序繪製之開源像素戰棋地圖引擎，內建完整 AI Agent 技能卡片與方法論。

---

## 🌟 核心特色 (Key Features)

1. 🎯 **SSOT 分層語意優先管線 (Semantics-First SSOT Pipeline)**：
   * 嚴格以 2D 純數值/文字標籤矩陣為 Single Source of Truth。
   * 每格單一語意 Token（`[沙]`, `[路]`, `[田]`, `[溝]`, `[屋]`, `[井]`, `[爐]`, `[草]`, `[石]`, `[▲頂]`）。
   * 先定義語意邊界與佔地面積 ➔ 再驅動填充 Tile/Prefab ➔ 100% 同源同構無損渲染！
2. ⚔️ **正統 Kenshi 廢土風格美學 (Authentic Wasteland Pixel Art)**：
   * 風化曬白厚木板、斜拉獸皮遮陽帆布、泥磚地基、鏽鐵修補補丁、木百葉氣窗。
   * 100% 純淨 Alpha 透明通道，徹底杜絕任何黑邊死角。
3. 📐 **標準 12~47 拓撲 Autotile 過渡 (Autotile Terrain Transition Engine)**：
   * 徹底消滅 32×32 生硬階梯方塊！
   * 內建 4 大外凸圓角 (Outer Corners)、4 大內凹角 (Inner Corners)、4 大平邊齒狀過渡 (Straight Edges)。
4. 🌊 **真實物理閉環水系拓撲 (Connected Hydrology)**：
   * 蓄水石井源頭 ➔ 風化引水木槽 ➔ 梯形耕地分水閘門 ➔ 地圖邊界自然排出。
5. 📊 **獨立 Base64 自包含 HTML 驗收報告 (Interactive HTML Map Report)**：
   * 內建全螢幕 Lightbox 像素級無損放大 (支援 100% ~ 1000% 滾輪放大與平移拖拽)。
   * 內建即時圖層疊加 QC 沙盒，動態開關圖層。
   * 100% Base64 內嵌，零外部依賴，永遠不破圖！
6. 🤖 **開箱即用之 AI Agent 技能卡片與協同 SOP (AI Agent Skill & SOPs)**：
   * 附帶標準 `skills/godot-tilemap-architect/SKILL.md`，可供 Gemini CLI / Claude Code / Cursor 一鍵掛載調用。
   * 沉澱完整地圖工程 SOP 與 AI 結對編程工作守則。

---

## 📁 目錄架構 (Repository Structure)

```text
nono-tactical-tilemap-engine/
├── assets/                          # 100% 原創 32x32 像素素材 (CC0 開源)
│   ├── 01_ground/                   # 純底地 Tile (黃沙、黏土)
│   ├── 02_autotile/                 # 47-tile 拓撲過渡圖塊集
│   ├── 03_prefabs/                  # 3/4 完整大屋 Prefab、屋頂淡出層
│   ├── 04_props/                    # 枯草、碎石、水井、熔爐
│   ├── kenshi_village_merged_1280.png
│   └── kenshi_village_per_cell_text_labels.png
├── skills/                          # AI Agent 技能卡片 (可直接掛載)
│   └── godot-tilemap-architect/
│       └── SKILL.md                 # 完整地圖架構師 Skill 規範
├── src/                             # Python 核心生成器源碼
│   └── nono_tilemap_engine.py       # SSOT 語意矩陣構建、Autotile 演算與無損合成
├── reports/                         # 獨立可放大 HTML 交付驗收報告
│   └── map_delivery_report_0_0_village.html
├── docs/                            # 核心工程文檔與方法論
│   ├── MAP_ENGINEERING_SOP.md       # 地圖工程標準 SOP 與 4 大鐵律
│   └── AI_AGENT_PAIR_PROGRAMMING_GUIDE.md # AI Agent 結對編程與主動煞車守則
├── LICENSE                          # MIT + CC0 雙重開源協議
├── .gitignore                       # 乾淨的 Git 忽略清單
└── README.md                        # 完整中英文開源文檔
```

---

## 🚀 快速開始 (Quick Start)

### 1. 執行地圖生成器
```bash
# 安裝依賴 (僅需 Pillow 與 NumPy)
pip install pillow numpy

# 運行主生成器，一鍵輸出全景大圖、語意矩陣與 Base64 獨立 HTML 報告
python src/nono_tilemap_engine.py
```

### 2. 掛載 AI Agent Skill
將 `skills/godot-tilemap-architect/` 複製到您的 Agent 配置目錄（如 `~/.gemini/config/skills/` 或 `.claude/skills/`），即可讓 AI Agent 自動獲取頂級地圖架構與繪製能力！

---

## 📜 開源協議 (License)

* **程式碼 (Code)**：採用 [MIT License](LICENSE) 開源。
* **美術與地圖資產 (Pixel Assets)**：採用 [CC0 1.0 Universal (Public Domain)](https://creativecommons.org/publicdomain/zero/1.0/) 全球公有領域授權，任何人皆可免費商用、修改與發布，無需擔心版權問題！

---
*Created with ❤️ and Pure Code by Nova (Nono) - Extreme Aesthetics AI Software Architect.*
