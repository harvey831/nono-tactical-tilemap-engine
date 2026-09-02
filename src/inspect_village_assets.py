import sys
from pathlib import Path
from PIL import Image

godot_dir = Path("C:/GPTfile/godot/adventure-of-self-realization-v-0.5/圖片/地圖/荒原九大戰區_正式資產/00_邊境村落")

names = [
    'layer_1_ground.png',
    'layer_2_structures.png',
    'layer_2_5_clutter.png',
    'layer_3_roofs.png',
    'interior_tavern_256x192.png',
    'fader_tavern_256x192.png',
    'exterior_tavern_256x192.png',
    'map_0_0_village_interior_1280.png',
    'map_0_0_village_merged_1280.png'
]

for name in names:
    p = godot_dir / name
    if p.exists():
        im = Image.open(p)
        print(f"{name}: size={im.size}, mode={im.mode}")
    else:
        print(f"MISSING: {name}")
