// viewer.js — 邊境村落分層範例的 canvas 互動檢視器（與 village_layered_example.py 同一套規則）
// 讀 window.PLM_SPEC（chunk_spec.json）、window.PLM_ATLASES（tileset base64）、window.PLM_PROPS（道具圖 base64）
(() => {
  const S = window.PLM_SPEC;
  const CELL = S.grid.cell_px, COLS = S.grid.cols, ROWS = S.grid.rows;
  const PJ = S.projection_presentation_only;
  const RISE = CELL * PJ.rise_ratio, SHIFT = CELL * PJ.side_shift_ratio, SPREAD = CELL * PJ.side_spread_cells;
  const FACE_H = Math.round(RISE);
  const WORLD_W = COLS * CELL, WORLD_H = ROWS * CELL;
  const ELEV = S.elevation_rows;
  const key = (c, r) => c + ',' + r;
  const setOf = (arr) => new Set(arr.map(([c, r]) => key(c, r)));
  const ROAD = setOf(S.road_cells), PLAZA = setOf(S.plaza_cells), FIELD = setOf(S.field_cells);
  const WATER = setOf(S.water_cells || []), BRIDGE = setOf(S.bridge_cells || []), DITCH = setOf(S.ditch_cells || []);   // R39 水系／R45 溝
  // R44：水體共用一個水面。BED 是河床（深淺用），ELEV 的水格改成水體的水面高度（幾何用）
  const BED = ELEV.map((row) => row.slice());
  {
    const seen = new Set();
    for (const k0 of WATER) {
      if (seen.has(k0)) continue;
      const body = [], stack = [k0]; seen.add(k0);
      while (stack.length) {
        const k = stack.pop(); body.push(k);
        const [c, r] = k.split(',').map(Number);
        for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const n = (c + dc) + ',' + (r + dr);
          if (WATER.has(n) && !seen.has(n)) { seen.add(n); stack.push(n); }
        }
      }
      // R44（更正）：水面＝四周岸格最低高度（岸不得低於水面）；河床在水面之下；水方塊佔 [level-1, level]
      let level = Infinity;
      for (const k of body) {
        const [c, r] = k.split(',').map(Number);
        for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
          const nc = c + dc, nr = r + dr;
          if (WATER.has(key(nc, nr))) continue;
          const h = (nc < 0 || nr < 0 || nc >= COLS || nr >= ROWS) ? 0 : BED[nr][nc];
          level = Math.min(level, h);
        }
      }
      if (level === Infinity) level = 0;
      for (const k of body) { const [c, r] = k.split(',').map(Number); ELEV[r][c] = level; }
    }
  }
  const T = S.tiles;
  const rowH = (n) => (S.atlas_row_h && S.atlas_row_h[n]) || CELL;   // kenshi atlas 每列 48px

  // ---- 建築前處理：牆環、室內、門 ----
  const buildings = S.buildings.map((b) => {
    const cells = [];
    for (let r = 0; r < b.footprint.rows; r += 1) for (let c = 0; c < b.footprint.cols; c += 1) cells.push([c, r]);
    const cellset = new Set(cells.map(([c, r]) => key(c, r)));
    const has = (c, r) => cellset.has(key(c, r));
    const walls = cells.filter(([c, r]) => [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => !has(c + dx, r + dy)));
    const wallset = new Set(walls.map(([c, r]) => key(c, r)));
    const interior = new Set(cells.filter(([c, r]) => !wallset.has(key(c, r))).map(([c, r]) => key(c, r)));
    const doors = new Map(b.doors_local.map(([c, r]) => [key(c, r), b.door_height_units]));
    return { ...b, cells, has, walls, wallset, interior, doors, ox: b.footprint.origin[0], oy: b.footprint.origin[1], H: b.height_units, base: b.base_elevation };
  });
  const buildingAt = new Map();
  buildings.forEach((b) => b.cells.forEach(([c, r]) => buildingAt.set(key(b.ox + c, b.oy + r), b)));

  const elevAt = (c, r) => (c < 0 || r < 0 || c >= COLS || r >= ROWS) ? null : ELEV[r][c];
  const neighborElev = (c, r, dx, dy, dflt) => {
    let v = elevAt(c + dx, r + dy);
    if (v === null) v = 0;                            // R40：chunk 外面視為 H0 的地
    const b = buildingAt.get(key(c + dx, r + dy));
    if (b) v = b.base;
    if (cut !== null && v > cut) return cut;          // 鄰格若被剖面截掉，畫出來的高度是 cut
    return v;
  };

  // ---- 圖片 ----
  const atlas = {};
  const props = {};
  const pending = [];
  const load = (src) => new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.src = src; });
  Object.entries(window.PLM_ATLASES).forEach(([n, src]) => pending.push(load(src).then((im) => { atlas[n] = im; })));
  Object.entries(window.PLM_PROPS).forEach(([n, src]) => pending.push(load(src).then((im) => { props[n] = im; })));

  // ---- 狀態 ----
  const canvas = document.getElementById('plm-canvas');
  const ctx = canvas.getContext('2d');
  const root = canvas.parentElement;
  const posText = root.querySelector('[data-status-pos]');
  const stateText = root.querySelector('[data-status-state]');
  let cut = null, mode = 'camera', zoom = 1, panX = 0, panY = 0;
  let showGrid = false, showLabels = false, showSurfaces = false;
  let cssW = 800, cssH = 600, dpr = 1;
  let dragging = false, lastX = 0, lastY = 0, pending_frame = false;

  const resize = () => {
    const rect = canvas.getBoundingClientRect();
    cssW = rect.width; cssH = rect.height; dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(cssW * dpr); canvas.height = Math.round(cssH * dpr);
    request();
  };
  const resetPan = () => { zoom = 1; panX = cssW / 2 - WORLD_W / 2; panY = cssH / 2 - WORLD_H / 2 + RISE * 2; request(); };
  const camWorldX = () => (cssW / 2 - panX) / zoom;
  const sideFor = (wx) => mode === 'fixed' ? 1 : Math.max(-1, Math.min(1, (wx - camWorldX()) / SPREAD));
  // R19：投影作用在頂點。同一個世界頂點永遠得到同一個螢幕位置，side 只是 x 的連續函數
  const sideAt = (wx) => sideFor(wx);
  // R19 推論：某道垂直面可不可見，看它所在格邊 x 的 side。左面（法線 −x）鏡頭在左才看得到；右面（法線 +x）鏡頭在右
  const faceVisible = (which, xEdge) => { const sd = sideAt(xEdge); return which === 'left' ? sd > 0.03 : sd < -0.03; };
  const PV = (x, y, h) => [x + sideAt(x) * h * SHIFT, y - h * RISE];
  const proj = (c, r, h) => PV(c * CELL, r * CELL, h);
  const vec = (a, b) => [b[0] - a[0], b[1] - a[1]];
  const surfaceSide = (cells) => sideFor((cells.reduce((s, [c]) => s + c, 0) / cells.length + 0.5) * CELL);

  // ---- 貼圖工具 ----
  const tintCache = new Map();
  const tintedTile = (ref, h) => {
    const k = ref.join(',') + '@' + h;
    if (tintCache.has(k)) return tintCache.get(k);
    const cv = document.createElement('canvas'); cv.width = CELL; cv.height = CELL;
    const g = cv.getContext('2d'); g.imageSmoothingEnabled = false;
    const [n, c, r] = ref;
    g.drawImage(atlas[n], c * CELL, r * rowH(n), CELL, CELL, 0, 0, CELL, CELL);
    const tint = S.plateau_tint;
    g.globalCompositeOperation = 'source-atop';
    g.fillStyle = `rgba(${tint.color.join(',')},${tint.alpha[String(h)]})`;
    g.fillRect(0, 0, CELL, CELL);
    tintCache.set(k, cv);
    return cv;
  };
  // 頂面：左上與右上頂點各自投影，寬度 = 兩者之差（side 連續變化時可能比 32 多零點幾 px）
  const drawTop = (ref, wx, wy, h, tintH = 0) => {
    const p0 = PV(wx, wy, h), p1 = PV(wx + CELL, wy, h);
    if (tintH > 0) { drawPara(tintedTile(ref, tintH), 0, 0, CELL, CELL, p0, vec(p0, p1), [0, CELL]); return; }
    const [n, c, r] = ref;
    drawPara(atlas[n], c * CELL, r * rowH(n), CELL, CELL, p0, vec(p0, p1), [0, CELL]);
  };
  // 把 src(img 的 sx,sy,sw,sh) 貼成平行四邊形 p0 + (u/sw)·U + (v/sh)·V
  const drawPara = (img, sx, sy, sw, sh, p0, U, V) => {
    if (!img || sw <= 0 || sh <= 0) return;
    ctx.save();
    ctx.transform(U[0] / sw, U[1] / sw, V[0] / sh, V[1] / sh, p0[0], p0[1]);
    ctx.drawImage(img, sx, sy, sw, sh, 0, 0, sw, sh);
    ctx.restore();
  };
  const faceY0 = (ref) => (S.face_crop_y0 && S.face_crop_y0[ref.join(',')] !== undefined) ? S.face_crop_y0[ref.join(',')] : 4;   // R16
  const facePara = (ref, p0, U, V) => { const [n, c, r] = ref; drawPara(atlas[n], c * CELL, r * rowH(n) + faceY0(ref), CELL, FACE_H, p0, U, V); };
  // R14 側面來源：正面貼圖沿牆長平鋪 n 格（1:1），高度方向逐步減半（帶平滑＝BOX）壓到投影高度向量長度，再壓暗
  const sideCache = new Map();
  const sideSource = (img, sx, sy, sw, sh, nTiles, vLen, shade, ck) => {
    const targetH = Math.max(1, Math.round(vLen));
    const k = ck + '|' + nTiles + '|' + targetH + '|' + shade;
    if (sideCache.has(k)) return sideCache.get(k);
    let cur = document.createElement('canvas'); cur.width = sw * nTiles; cur.height = sh;
    let g = cur.getContext('2d'); g.imageSmoothingEnabled = false;
    for (let i = 0; i < nTiles; i += 1) g.drawImage(img, sx, sy, sw, sh, i * sw, 0, sw, sh);
    let h = sh;
    while (h > targetH) {
      const nh = Math.max(targetH, Math.floor(h / 2));
      const next = document.createElement('canvas'); next.width = cur.width; next.height = nh;
      const ng = next.getContext('2d'); ng.imageSmoothingEnabled = true; ng.imageSmoothingQuality = 'high';
      ng.drawImage(cur, 0, 0, cur.width, nh);
      cur = next; h = nh;
    }
    g = cur.getContext('2d'); g.globalCompositeOperation = 'source-atop'; g.fillStyle = `rgba(0,0,0,${shade})`; g.fillRect(0, 0, cur.width, cur.height);
    sideCache.set(k, cur);
    return cur;
  };
  // 側面四邊形：p0 上緣起點，U=(0,depth) 沿格深，V 沿投影高度向量
  const pasteSide = (img, sx, sy, sw, sh, nTiles, p0, depth, V, shade, ck) => {
    const vLen = Math.hypot(V[0], V[1]);
    if (vLen < 0.5) return;
    const cv = sideSource(img, sx, sy, sw, sh, nTiles, vLen, shade, ck);
    drawPara(cv, 0, 0, cv.width, cv.height, p0, [0, depth], V);
  };
  // R15：南向立面每級一片；k≤0 坑壁石材、k>0 岩壁（最底一級帶地基）
  // R41：面的材質跟著擁有它的頂面走
  const topMaterial = (c, r) => BRIDGE.has(key(c, r)) ? 'bridge' : WATER.has(key(c, r)) ? 'water' : PLAZA.has(key(c, r)) ? 'stone' : (FIELD.has(key(c, r)) || (elevAt(c, r) !== null && elevAt(c, r) < 0)) ? 'earth' : 'sand';
  const faceRef = (c, r, k, hBottom, sideFace) => {
    const m = topMaterial(c, r);
    if (m === 'bridge') return T.bridge_face;
    if (m === 'water') return sideFace ? T.pit_wall_side : T.pit_wall;   // R41 改：水下的面是土岸
    if (m === 'stone') return T.face_stone;
    if (m === 'earth' || k <= 0) return sideFace ? T.pit_wall_side : T.pit_wall;
    if (sideFace) return T.cliff_side;
    return k === Math.max(hBottom, 0) + 1 ? T.cliff_face_base : T.cliff_face;
  };
  const frontFaces = (c, r, hTop, hBottom, side) => {
    const x = c * CELL, yb = r * CELL + CELL;
    for (let k = hTop; k > hBottom; k -= 1) {
      const p0 = PV(x, yb, k);
      const ref = faceRef(c, r, k, hBottom, false);
      facePara(ref, p0, vec(p0, PV(x + CELL, yb, k)), vec(p0, PV(x, yb, k - 1)));
    }
  };
  // R13：同一列同一級連續 nRows 格的側面 = 一個四邊形
  const sideRun = (c, r0, nRows, k, side, which) => {
    const xe = c * CELL + (which === 'right' ? CELL : 0);
    const p0 = PV(xe, r0 * CELL, k);
    const ref = faceRef(c, r0, k, k - 1, true);   // R41
    pasteSide(atlas[ref[0]], ref[1] * CELL, ref[2] * rowH(ref[0]) + faceY0(ref), CELL, FACE_H, nRows, p0, nRows * CELL, vec(p0, PV(xe, r0 * CELL, k - 1)), 0.10, 'tile:' + ref.join(','));
  };
  const groundTile = (c, r, h) => {
    if (BRIDGE.has(key(c, r))) return T.bridge_top;
    if (WATER.has(key(c, r))) return BED[r][c] <= -2 ? T.water_deep : T.water;   // R44：深淺看河床
    if (DITCH.has(key(c, r))) {                                                   // R45 autotile
      let m = 0;
      for (const [bit, dx, dy] of [[1, 0, -1], [2, 1, 0], [4, 0, 1], [8, -1, 0]]) { const nk = key(c + dx, r + dy); if (DITCH.has(nk) || WATER.has(nk)) m |= bit; }
      const [tc, tr] = S.ditch_autotile[String(m)];
      return ['kenshi', tc, tr];
    }
    if (h < 0) return T.pit_floor;
    const k = key(c, r);
    if (ROAD.has(k)) {
      let m = 0;
      if (ROAD.has(key(c, r - 1))) m |= 1;
      if (ROAD.has(key(c + 1, r))) m |= 2;
      if (ROAD.has(key(c, r + 1))) m |= 4;
      if (ROAD.has(key(c - 1, r))) m |= 8;
      const [tc, tr] = S.road_autotile[String(m)];
      return ['kenshi', tc, tr];
    }
    if (PLAZA.has(k)) return T.plaza;
    if (FIELD.has(k)) return T.field;
    return T.sand[(((c * 73856093) ^ (r * 19349663)) & 0xffff) % T.sand.length];   // 非線性雜湊，線性式會出斜向條紋
  };

  // ---- 戶外：一格一格畫，呼叫順序必須是 row 由北到南 ----
  const surfaceOf = new Map();
  S.surfaces.forEach((sf) => sf.cells.forEach(([c, r]) => surfaceOf.set(key(c, r), sf)));
  let sideCacheFrame = new Map();
  const surfaceSideCached = (sf) => {
    if (!sideCacheFrame.has(sf.surface_id)) sideCacheFrame.set(sf.surface_id, surfaceSide(sf.cells));
    return sideCacheFrame.get(sf.surface_id);
  };
  // R10：站在 surface 上的東西一律用所站 surface 的 side；建築腳印格沒有 surface，往外找同基底高度的相鄰 surface
  const sideOwnerCache = new Map();
  const sideOwnerSurface = (c, r) => {
    const k0 = key(c, r);
    if (surfaceOf.has(k0)) return surfaceOf.get(k0);
    if (sideOwnerCache.has(k0)) return sideOwnerCache.get(k0);
    const b = buildingAt.get(k0);
    const want = b ? b.base : ELEV[r][c];
    const q = [[c, r]], seen = new Set([k0]);
    let found = S.surfaces[0];
    outer: while (q.length) {
      const [x, y] = q.shift();
      for (const [dx, dy] of [[0, 1], [1, 0], [-1, 0], [0, -1]]) {
        const n = [x + dx, y + dy], nk = key(n[0], n[1]);
        if (seen.has(nk) || elevAt(n[0], n[1]) === null) continue;
        if (surfaceOf.has(nk) && surfaceOf.get(nk).elevation === want) { found = surfaceOf.get(nk); break outer; }
        seen.add(nk); q.push(n);
      }
    }
    sideOwnerCache.set(k0, found);
    return found;
  };
  // R10：站在高處 surface 的物件繼承該 surface 的 side；站在 H0 的底盤錯位為 0，用自己中心算
  const objectSide = (c, r, ownCenterX) => {
    const sf = sideOwnerSurface(c, r);
    return sf.elevation !== 0 ? surfaceSideCached(sf) : sideFor(ownCenterX);
  };
  // 剖面格＝高度被截到 cut 的柱子：頂面貼剖面岩層，側面照畫
  const cellElev = (c, r, sf) => WATER.has(key(c, r)) ? ELEV[r][c] : sf.elevation;   // R44：水格用水面高度（河床+1），不用 surface 記的河床
  const cellDrawHeight = (c, r) => {
    const sf = surfaceOf.get(key(c, r));
    if (!sf) return null;
    const e = cellElev(c, r, sf);
    if (cut !== null && e > cut) return cut;
    return e;
  };
  const sideLevels = (c, r, which) => {
    const h = cellDrawHeight(c, r);
    if (h === null) return new Set();
    const nb = neighborElev(c, r, which === 'left' ? -1 : 1, 0, h);
    const out = new Set();
    for (let k = nb + 1; k <= h; k += 1) out.add(k);
    return out;
  };
  // R49：水格 = 河床（bed 高度）→ 水下岸壁 → 半透明水面
  const drawWaterCell = (c, r, level, side, withSurface = true) => {
    const bed = BED[r][c], x = c * CELL, y = r * CELL;
    drawTop(T.pit_floor, x, y, bed);
    if (bed <= -2) { const p0 = PV(x, y, bed), p1 = PV(x + CELL, y, bed); ctx.save(); ctx.fillStyle = 'rgba(0,0,0,0.43)'; ctx.beginPath(); ctx.moveTo(p0[0], p0[1]); ctx.lineTo(p1[0], p1[1]); ctx.lineTo(p1[0], p1[1] + CELL); ctx.lineTo(p0[0], p0[1] + CELL); ctx.closePath(); ctx.fill(); ctx.restore(); }
    const nbH = (dc, dr) => { const nk = key(c + dc, r + dr); if (WATER.has(nk)) return Math.min(level, BED[r + dr][c + dc]); return Math.min(level, neighborElev(c, r, dc, dr, level)); };   // 面頂不高於 level（剖面時＝cut）
    const hn = nbH(0, -1), hw = nbH(-1, 0), he = nbH(1, 0);      // 只有鄰格比自己河床高才有水下岸壁
    if (hn > bed) frontFaces(c, r - 1, hn, bed, side);
    if (hw > bed && faceVisible('right', x)) for (let k = hw; k > bed; k -= 1) sideRun(c - 1, r, 1, k, side, 'right');
    if (he > bed && faceVisible('left', x + CELL)) for (let k = he; k > bed; k -= 1) sideRun(c + 1, r, 1, k, side, 'left');
    const southBed = WATER.has(key(c, r + 1)) ? BED[r + 1][c] : bed;
    if (southBed < bed && bed <= level) frontFaces(c, r, bed, southBed, side);
    if (!withSurface) return;
    ctx.save(); ctx.globalAlpha = 0.7; drawTop(T.water, x, y, level - 0.15); ctx.restore();   // 水面比 H0 低 0.15 級
  };
  const drawOutdoorCell = (c, r) => {
    const sf = surfaceOf.get(key(c, r));
    if (!sf) {
      // 建築腳印格：剖面低於建築基底時，腳印下面是地，跟地形一樣畫剖面平面；否則交給建築自己畫
      const bld = buildingAt.get(key(c, r));
      if (bld && cut !== null && cut < bld.base) drawTop(T.cut_plane, c * CELL, r * CELL, cut);
      return;
    }
    const side = sideAt((c + 0.5) * CELL);          // 只決定看得到左側面還是右側面
    const h = cellDrawHeight(c, r);
    const isCutCell = cut !== null && cellElev(c, r, sf) > cut;
    const south = neighborElev(c, r, 0, 1, h);
    if (south < h) frontFaces(c, r, h, south, side);
    for (const which of ['left', 'right']) {
      if (!faceVisible(which, c * CELL + (which === 'right' ? CELL : 0))) continue;
      const levels = sideLevels(c, r, which), above = r > 0 ? sideLevels(c, r - 1, which) : new Set();
      [...levels].filter((k) => !above.has(k)).sort((a, b) => b - a).forEach((k) => {
        let n = 1;
        while (!buildingAt.has(key(c, r + n)) && sideLevels(c, r + n, which).has(k)) n += 1;
        sideRun(c, r, n, k, side, which);
      });
    }
    if (isCutCell) { if (WATER.has(key(c, r)) && BED[r][c] <= cut) { drawWaterCell(c, r, cut, side, false); } else { drawTop(T.cut_plane, c * CELL, r * CELL, h); } drawTransition(c, r, h); return; }   // 切掉水就露河床
    // R40：較高鄰格若不在地形 pass 裡（建築腳印、chunk 外面），由這格代畫它朝這邊的面
    const absent = (cc, rr) => buildingAt.has(key(cc, rr)) || elevAt(cc, rr) === null;
    const nb = neighborElev(c, r, 0, -1, h);
    if (absent(c, r - 1) && nb > h) frontFaces(c, r - 1, nb, h, side);
    const wb = neighborElev(c, r, -1, 0, h);
    if (absent(c - 1, r) && wb > h && faceVisible('right', c * CELL)) for (let k = wb; k > h; k -= 1) sideRun(c - 1, r, 1, k, side, 'right');
    const eb = neighborElev(c, r, 1, 0, h);
    if (absent(c + 1, r) && eb > h && faceVisible('left', (c + 1) * CELL)) for (let k = eb; k > h; k -= 1) sideRun(c + 1, r, 1, k, side, 'left');
    if (WATER.has(key(c, r))) drawWaterCell(c, r, h, side); else drawTop(groundTile(c, r, h), c * CELL, r * CELL, h, h);   // R49
    drawTransition(c, r, h);
  };
  const northIsHigher = (c, r, h) => {
    if (buildingAt.has(key(c, r - 1))) return true;
    let v = elevAt(c, r - 1);
    if (v === null) return false;
    if (cut !== null && v > cut) v = cut;
    return v > h;
  };
  // R35：平面與垂直面的過渡由幾何決定：落差邊的南緣受光亮線＋暗稜線；北鄰／側鄰較高處的接地陰影
  const drawTransition = (c, r, h) => {
    const x = c * CELL, y = r * CELL;
    const p0 = PV(x, y, h), p1 = PV(x + CELL, y, h);
    ctx.save();
    ctx.transform((p1[0] - p0[0]) / CELL, 0, 0, 1, p0[0], p0[1]);
    if (neighborElev(c, r, 0, 1, h) < h) {
      ctx.fillStyle = 'rgba(255,236,190,0.27)'; ctx.fillRect(0, CELL - 2, CELL, 1);
      ctx.fillStyle = 'rgba(60,40,20,0.47)'; ctx.fillRect(0, CELL - 1, CELL, 1);
    }
    if (northIsHigher(c, r, h)) for (let k = 0; k < 4; k += 1) { ctx.fillStyle = `rgba(40,26,14,${(110 - k * 26) / 255})`; ctx.fillRect(0, k, CELL, 1); }
    if (neighborElev(c, r, -1, 0, h) > h && faceVisible('right', x)) for (let k = 0; k < 3; k += 1) { ctx.fillStyle = `rgba(40,26,14,${(100 - k * 30) / 255})`; ctx.fillRect(k, 0, 1, CELL); }
    if (neighborElev(c, r, 1, 0, h) > h && faceVisible('left', x + CELL)) for (let k = 0; k < 3; k += 1) { ctx.fillStyle = `rgba(40,26,14,${(100 - k * 30) / 255})`; ctx.fillRect(CELL - 1 - k, 0, 1, CELL); }
    ctx.restore();
  };
  const drawSurfaceLabels = () => {
    for (const sf of S.surfaces) {
      const h = sf.elevation;
      if (cut !== null && cut < 0 && h > cut) continue;
      const isCut = cut !== null && cut >= 0 && h > cut;
      const disp = isCut ? cut : h;
      const cells = [...sf.cells].sort((a, b) => a[1] - b[1] || a[0] - b[0]);
      const [x, y] = proj(cells[0][0], cells[0][1], disp);
      label(`${sf.surface_id} H${h}`, x + 3, y + 11);
    }
  };

  // ---- 建築 ----
  const bandCache = {};
  // R32：牆帶依 style 表：牆面 tile、石基有無、門 sprite、窗 sprite
  const wallBand = (floorIndex, kind, styleName, floorH = 3) => {
    const st = S.styles[styleName];
    const ck = (floorIndex > 0 ? 'up:' : 'gf:') + kind + ':' + styleName + ':' + floorH;
    if (bandCache[ck]) return bandCache[ck];
    const bandH = Math.round(Math.max(3, floorH) * RISE);
    const cv = document.createElement('canvas'); cv.width = CELL; cv.height = bandH;
    const g = cv.getContext('2d'); g.imageSmoothingEnabled = false;
    const wall = st.wall, img = atlas[wall[0]], px = wall[1] * CELL, py = wall[2] * rowH(wall[0]);
    const stripH = st.base ? 24 : 32;
    let y = bandH;
    if (floorIndex === 0 && st.base) { y -= 8; g.drawImage(img, px, py + 24, CELL, 8, 0, y, CELL, 8); }   // 石基只在一樓
    while (y > 0) { y -= stripH; g.drawImage(img, px, py, CELL, stripH, 0, y, CELL, stripH); }
    if (kind === 'door') {
      const [n, dc, dr, dw, dh] = st.door;                                                       // R30：一整扇 32×46 的兩格高門
      g.drawImage(atlas[n], dc * CELL, dr * rowH(n), dw, dh, 0, bandH - dh, dw, dh);
    }
    else if (kind === 'window') { const [n, wc, wr, ww, wh] = st.window; g.drawImage(atlas[n], wc * CELL, wr * rowH(n), ww, wh, 0, bandH - 46 - 12, ww, wh); }   // 玻璃跨 H1.65–H2.2
    if (floorIndex > 0) { g.fillStyle = '#48301a'; g.fillRect(0, bandH - 3, CELL, 3); }        // 樓上底部只畫樓層樑
    bandCache[ck] = cv;
    return cv;
  };
  // R33：門面元件。wall：掛在南牆面上，底邊在高度 h；roof：放在屋頂格上。被剖面切過的不畫
  const drawFacade = (b, kind, P) => {
    for (const fp of (b.facade || [])) {
      if (fp.kind !== kind) continue;
      let img, sx = 0, sy = 0, sw, sh;
      if (fp.img_id) { img = props[fp.img_id]; if (!img) continue; sw = img.width; sh = img.height; }
      else { const [n, tc, tr, tw, th] = fp.tile; img = atlas[n]; sx = tc * CELL; sy = tr * rowH(n); sw = tw; sh = th; }
      if (kind === 'wall') {
        const h0 = fp.h, h1 = h0 + sh / RISE;
        if (cut !== null && cut - b.base < h1) continue;
        const topH = cut === null ? b.H : Math.min(cut - b.base, b.H);   // R34：門面元件只能在牆帶內
        const wallTop = P(fp.cell, b.footprint.rows, topH)[1], wallBot = P(fp.cell, b.footprint.rows, 0)[1];
        ctx.save(); ctx.beginPath(); ctx.rect(-1e5, wallTop, 2e5, wallBot - wallTop); ctx.clip();
        const dxc = (fp.dx || 0) / CELL, cc = fp.cell + dxc;          // 貼在牆「面」上：跟牆帶一樣走頂點投影，鏡頭移動才同步
        const p0 = P(cc, b.footprint.rows, h1);
        drawPara(img, sx, sy, sw, sh, p0, vec(p0, P(cc + sw / CELL, b.footprint.rows, h1)), vec(p0, P(cc, b.footprint.rows, h0)));
        ctx.restore();
      } else {
        const [c, r] = fp.cell;
        const [x, y] = P(c, r, b.height_units);
        ctx.drawImage(img, sx, sy, sw, sh, Math.round(x + (CELL - sw) / 2), Math.round(y + CELL - sh), sw, sh);
      }
    }
  };
  const drawBuilding = (b, indoorActors = []) => {
    const st = S.styles[b.style];                                       // R32：這棟的材質組
    if (cut !== null && cut < b.base) return;
    const H = b.H, floors = b.floors, floorH = H / floors;
    const localCut = cut === null ? null : cut - b.base;
    const isCut = localCut !== null && localCut >= 0 && localCut < H;
    const disp = isCut ? localCut : H;
    const layerSel = localCut !== null && localCut >= 0 && localCut <= H;
    const visibleFloor = localCut === null ? H : Math.min(H, Math.floor(Math.max(0, localCut) / floorH) * floorH);
    const side = sideAt((b.ox + b.footprint.cols / 2) * CELL);   // 只決定看得到哪一側
    const P = (c, r, h) => PV((b.ox + c) * CELL, (b.oy + r) * CELL, b.base + h);   // R19
    const top = (ref, c, r, h) => { const p0 = P(c, r, h); const [n, tc, tr] = ref; drawPara(atlas[n], tc * CELL, tr * rowH(n), CELL, CELL, p0, vec(p0, P(c + 1, r, h)), [0, CELL]); };
    const stair = b.stair;
    const steps = [];
    let stairBase = 0;
    const walk = Boolean(b.roof && b.roof.walkable);
    if (stair && disp > 0 && (disp < H || walk)) {
      const idx = Math.min(floors - (walk ? 1 : 2), Math.ceil(disp / floorH) - 1);   // R31：可站屋頂時最上層樓梯直通屋頂
      if (idx >= 0) { stairBase = idx * floorH; stair.flight_local.forEach((f) => { const hh = stairBase + f.step_offset; if (hh <= disp) steps.push([f.col, f.row, hh]); }); }
    }
    const floorHasOpening = Boolean(stair) && visibleFloor > 0 && (visibleFloor < H || walk);   // R31：屋頂天窗
    const opening = new Set(floorHasOpening ? stair.opening_local_on_upper_floor.map(([c, r]) => key(c, r)) : []);
    // 梯洞豎井：洞口內容，在樓板之前畫（R25）；豎井側面比洞格多出一級的斜下截，洞外部分由樓板蓋住
    if (floorHasOpening) {
      const stepH = new Map(steps.map(([c, r, hh]) => [key(c, r), hh]));
      for (const k of opening) {
        const [c, r] = k.split(',').map(Number);
        const bottom = stairBase;                                             // R25：豎井面一路落到這層樓板；梯級之後畫在上面蓋住
        const nLv = Math.max(1, Math.round(visibleFloor - bottom));
        const wp = st.wall;
        if (!opening.has(key(c, r - 1))) for (let q = 0; q < nLv; q += 1) { const p0 = P(c, r, visibleFloor - q); facePara(wp, p0, vec(p0, P(c + 1, r, visibleFloor - q)), vec(p0, P(c, r, visibleFloor - q - 1))); }
        if (!opening.has(key(c - 1, r)) && faceVisible('right', (b.ox + c) * CELL)) { const q0 = P(c, r, visibleFloor); pasteSide(atlas[wp[0]], wp[1] * CELL, wp[2] * rowH(wp[0]) + faceY0(wp), CELL, FACE_H, 1, q0, CELL, vec(q0, P(c, r, bottom)), 0.22, 'tile:' + wp.join(',')); }
        if (!opening.has(key(c + 1, r)) && faceVisible('left', (b.ox + c + 1) * CELL)) { const q0 = P(c + 1, r, visibleFloor); pasteSide(atlas[wp[0]], wp[1] * CELL, wp[2] * rowH(wp[0]) + faceY0(wp), CELL, FACE_H, 1, q0, CELL, vec(q0, P(c + 1, r, bottom)), 0.22, 'tile:' + wp.join(',')); }
      }
    }
    // R11：牆格永遠不鋪樓面；剖面時牆格＝立面＋在 disp 的 cap；cut≥H 時 cap 就是屋頂
    const visibleWalls = (layerSel && disp < H) ? b.walls.filter(([c, r]) => !b.doors.has(key(c, r)) || disp > b.doors.get(key(c, r))) : [];
    const openCells = new Set(b.interior);                                                     // 牆格朝這些格有內側面（含門框）
    b.doors.forEach((dh, k) => { if (disp <= dh) openCells.add(k); });
    const band = (c, r, lo, hi, kind) => {
      const f = Math.floor(lo / floorH), flHi = (f + 1) * floorH;
      const src = wallBand(f, kind, b.style, floorH);
      const y0 = Math.max(0, Math.round((flHi - hi) * RISE)), y1 = Math.min(src.height, Math.max(y0, Math.round((flHi - lo) * RISE)));
      if (y1 <= y0) return;
      const p0 = P(c, r + 1, hi);
      drawPara(src, 0, y0, CELL, y1 - y0, p0, vec(p0, P(c + 1, r + 1, hi)), vec(p0, P(c, r + 1, lo)));
    };
    // 剖面內牆：南向面逐格（垂直接縫看不見）；側向面 R13 合併成連續段
    const vwSet = new Set(visibleWalls.map(([c, r]) => key(c, r)));
    const wp = st.wall;
    for (const [c, r] of visibleWalls) {
      for (let k = Math.floor(disp); k > visibleFloor; k -= 1) {
        if (openCells.has(key(c, r + 1))) { const p0 = P(c, r + 1, k); facePara(wp, p0, vec(p0, P(c + 1, r + 1, k)), vec(p0, P(c, r + 1, k - 1))); }
      }
    }
    for (const innerWhich of ['right', 'left']) {
      const dx = innerWhich === 'right' ? 1 : -1, ce = (c) => c + (innerWhich === 'right' ? 1 : 0);
      for (let c = 0; c < b.footprint.cols; c += 1) {
        if (!faceVisible(innerWhich, (b.ox + ce(c)) * CELL)) continue;
        const ok = (rr) => vwSet.has(key(c, rr)) && openCells.has(key(c + dx, rr));
        let r = 0;
        while (r < b.footprint.rows) {
          if (!ok(r)) { r += 1; continue; }
          let n = 1;
          while (r + n < b.footprint.rows && ok(r + n)) n += 1;
          for (let k = Math.floor(disp); k > visibleFloor; k -= 1) {
            const p0 = P(ce(c), r, k);
            pasteSide(atlas[wp[0]], wp[1] * CELL, wp[2] * rowH(wp[0]) + faceY0(wp), CELL, FACE_H, n, p0, n * CELL, vec(p0, P(ce(c), r, k - 1)), 0.22, 'tile:' + wp.join(','));
          }
          r += n;
        }
      }
    }
    const drawSteps = () => {
      for (const [c, r, hh] of steps) {
        const wp = st.wall;
        if (faceVisible('left', (b.ox + c) * CELL)) { const q0 = P(c, r, hh); pasteSide(atlas[wp[0]], wp[1] * CELL, wp[2] * rowH(wp[0]) + faceY0(wp), CELL, FACE_H, 1, q0, CELL, vec(q0, P(c, r, hh - 1)), 0.22, 'tile:' + wp.join(',')); }
        if (faceVisible('right', (b.ox + c + 1) * CELL)) { const q0 = P(c + 1, r, hh); pasteSide(atlas[wp[0]], wp[1] * CELL, wp[2] * rowH(wp[0]) + faceY0(wp), CELL, FACE_H, 1, q0, CELL, vec(q0, P(c + 1, r, hh - 1)), 0.22, 'tile:' + wp.join(',')); }
        for (let k = 0; k < 3; k += 1) {                               // R0：一格三階
          const hTop = hh - 1 + (k + 1) / 3, hBot = hh - 1 + k / 3, ys = r + 1 - k / 3, yn = r + 1 - (k + 1) / 3;
          const p0 = P(c, ys, hTop);
          drawPara(atlas[wp[0]], wp[1] * CELL, wp[2] * rowH(wp[0]) + faceY0(wp), CELL, 8, p0, vec(p0, P(c + 1, ys, hTop)), vec(p0, P(c, ys, hBot)));
          const q0 = P(c, yn, hTop);
          drawPara(atlas[st.step[0]], st.step[1] * CELL, st.step[2] * rowH(st.step[0]) + Math.floor(k * CELL / 3), CELL, Math.floor((k + 1) * CELL / 3) - Math.floor(k * CELL / 3), q0, vec(q0, P(c + 1, yn, hTop)), [0, (ys - yn) * CELL]);
        }
        const [tx, ty] = P(c, r, hh);
        label(`H${b.base + hh}`, tx + 4, ty + 19);
      }
    };
    // 梯級所屬樓層在「目前顯示樓板」之下 → 先畫、被樓板蓋住、只從梯洞露出；同一層 → 樓板之後畫
    const stairsBelow = stairBase < visibleFloor;
    if (stairsBelow) drawSteps();
    // 樓板下面的演員在樓板之前畫：樓板跳過洞格，洞裡自然透視看到他（畫序，不是遮罩）
    const belowFloor = indoorActors.filter((a) => a.cells[0][2] < b.base + visibleFloor);
    belowFloor.forEach(drawActor);
    // 樓面／屋頂
    for (const [c, r] of b.cells) {
      if (opening.has(key(c, r))) continue;
      const [x, y] = P(c, r, visibleFloor);
      if (layerSel && disp < H) {
        const isDoorway = b.doors.has(key(c, r)) && disp <= b.doors.get(key(c, r));   // 門格在剖面低於門高時是開口，露出門檻地板
        if (!b.wallset.has(key(c, r)) || isDoorway) top(st.floor, c, r, visibleFloor);       // R11：牆格不鋪樓面
      } else if (walk) {
        top(st.deck, c, r, visibleFloor);          // R31：可站屋頂＝甲板 surface
      } else {
        let k = (r === 0 ? 't' : r === b.footprint.rows - 1 ? 'b' : '') + (c === 0 ? 'l' : c === b.footprint.cols - 1 ? 'r' : '');
        top(st.roof.all ? st.roof.all : st.roof[k || 'c'], c, r, visibleFloor);
      }
    }
    if (!(layerSel && disp < H)) drawFacade(b, 'roof', P);           // R33：煙囪等屋頂元件
    if (!(layerSel && disp < H) && !walk) {
      // 屋簷：屋頂底邊畫一條深色簷線（tile 本身沒有）
      const [x0, y0] = P(0, b.footprint.rows - 1, visibleFloor), [x1] = P(b.footprint.cols - 1, b.footprint.rows - 1, visibleFloor);
      ctx.fillStyle = `rgb(${st.eave.join(',')})`; ctx.fillRect(x0, y0 + CELL - 3, x1 + CELL - x0, 3);
      const [rx, ry] = P(0, 0, visibleFloor);
      ctx.fillRect(rx, ry, x1 + CELL - rx, 2);   // 屋脊線：依幾何頂邊畫
    }
    if (!stairsBelow) drawSteps();
    indoorActors.filter((a) => !belowFloor.includes(a)).forEach(drawActor);   // 樓板上的室內演員也在外牆之前
    // R28：外牆立面在室內內容之後畫（牆在鏡頭與室內之間，要蓋住樓面／梯級／室內演員）
    // 外牆南面
    for (const [c, r] of b.cells) {
      if (!(disp > 0 && !b.has(c, r + 1))) continue;
      for (let f = 0; f < floors; f += 1) {
        const lo = f * floorH; let hi = Math.min(H, (f + 1) * floorH);
        if (lo >= disp) break;
        hi = Math.min(hi, disp);
        const wins = (b.windows_local && b.windows_local[String(f)]) || [];
        const kind = (b.doors.has(key(c, r)) && f === 0) ? 'door' : (wins.includes(c) ? 'window' : 'plain');
        band(c, r, lo, hi, kind);
      }
    }
    // 外牆側面：R13 整面牆一個四邊形、R14 牆帶長度沿格深、高度沿投影向量壓縮
    const sideBand = (c, r0, nRows, lo, hi, which) => {
      const f = Math.floor(lo / floorH), flHi = (f + 1) * floorH;
      const band = wallBand(f, 'plain', b.style, floorH);
      const y0 = Math.max(0, Math.round((flHi - hi) * RISE)), y1 = Math.min(band.height, Math.max(y0, Math.round((flHi - lo) * RISE)));
      if (y1 <= y0) return;
      const ce = c + (which === 'right' ? 1 : 0);
      const p0 = P(ce, r0, hi);
      pasteSide(band, 0, y0, band.width, y1 - y0, nRows, p0, nRows * CELL, vec(p0, P(ce, r0, lo)), 0.22, 'band:' + b.style + ':' + (f > 0 ? 'up' : 'gf') + ':' + y0 + ':' + y1);   // 快取鍵要含 style，否則石屋拿到木屋的側面帶
    };
    if (disp > 0) {
      for (const which of ['right', 'left']) for (let c = 0; c < b.footprint.cols; c += 1) {
        if (!faceVisible(which, (b.ox + c + (which === 'right' ? 1 : 0)) * CELL)) continue;
        const exposed = (rr) => b.has(c, rr) && !b.has(c + (which === 'right' ? 1 : -1), rr);
        let r = 0;
        while (r < b.footprint.rows) {
          if (!exposed(r)) { r += 1; continue; }
          let n = 1;
          while (r + n < b.footprint.rows && exposed(r + n)) n += 1;
          for (let f = 0; f < floors; f += 1) {
            const lo = f * floorH, hi = Math.min(H, (f + 1) * floorH);
            if (lo >= disp) break;
            sideBand(c, r, n, lo, Math.min(hi, disp), which);
          }
          r += n;
        }
      }
    }
    drawFacade(b, 'wall', P);                                           // R33：招牌／燈籠／布棚貼在外牆立面之上
    for (const [c, r] of visibleWalls) top(st.cap, c, r, disp);
    const [lx, ly] = P(0, 0, disp);
    label((b.label || b.building_id || b.id || '建築') + (isCut ? ` H${b.base + disp} 剖面` : ` 屋頂 H${b.base + H}`), lx + 3, ly - 4);   // 沒給 label 就退回 id，不要印 undefined
  };

  // ---- 道具、演員、標籤 ----
  const label = (text, x, y, color = '#fff') => {
    ctx.font = '11px "Noto Sans TC","Microsoft JhengHei",sans-serif';
    ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(0,0,0,.75)'; ctx.strokeText(text, x, y);
    ctx.fillStyle = color; ctx.fillText(text, x, y);
  };
  // R38：道具柱子：正面立面 → 可見側面（正面壓縮＋陰影）→ 頂面，全部用頂點投影
  const drawBoxProp = (p) => {
    const [cols, rows] = p.footprint, base = p.elevation, topH = base + p.height;
    if (cut !== null && cut < topH) return;
    const front = props[p.box + '_front'], top = props[p.box + '_top'];
    if (!front || !top) return;
    const x0 = p.cell[0] * CELL, y0 = p.cell[1] * CELL, w = cols * CELL, dep = rows * CELL, yb = y0 + dep;
    const q0 = PV(x0, yb, topH);
    drawPara(front, 0, 0, front.width, front.height, q0, vec(q0, PV(x0 + w, yb, topH)), vec(q0, PV(x0, yb, base)));
    if (faceVisible('right', x0 + w)) { const s0 = PV(x0 + w, y0, topH); pasteSide(front, 0, 0, CELL, front.height, rows, s0, dep, vec(s0, PV(x0 + w, y0, base)), 0.22, 'box:' + p.box); }
    if (faceVisible('left', x0)) { const s0 = PV(x0, y0, topH); pasteSide(front, 0, 0, CELL, front.height, rows, s0, dep, vec(s0, PV(x0, y0, base)), 0.22, 'box:' + p.box); }
    const t0 = PV(x0, y0, topH);
    drawPara(top, 0, 0, top.width, top.height, t0, [PV(x0 + w, y0, topH)[0] - t0[0], 0], [0, dep]);
  };
  const drawProp = (p) => {
    if (cut !== null && p.elevation > cut) return;
    if (p.box) { drawBoxProp(p); return; }
    const img = props[p.id]; if (!img) return;
    if (p.sprite_box) { const [x0, y0] = proj(p.cell[0], p.cell[1], p.elevation); ctx.drawImage(img, Math.round(x0 - p.sprite_box.pad), Math.round(y0 - p.sprite_box.front_px - p.sprite_box.pad - p.sprite_box.extra_top)); return; }   // R0 格盒道具
    const [c, r] = p.cell, [fw, fh] = p.footprint;
    const [bx, by] = PV((c + fw / 2) * CELL, (r + fh) * CELL, p.elevation);
    ctx.drawImage(img, Math.round(bx - img.width / 2), Math.round(by - img.height));
  };
  // 演員只有兩種不畫：比剖面高、或剖面正好切過身體。被屋頂／樓板蓋住是畫序的事
  const actorVisible = (a) => {
    if (cut === null) return true;
    if (a.cells.some(([, , h]) => h === cut)) return false;
    return a.cells[0][2] <= cut;
  };
  const drawActor = (a) => {
    if (!actorVisible(a)) return;
    drawActorBody(a);
  };
  const drawActorBody = (a) => {
    const [cc, cr, ch] = a.cells[0];
    const col = `rgb(${a.color.join(',')})`;
    const visibleCells = a.cells;
    for (const [c, r, h] of visibleCells) {
      const [x, y] = proj(c, r, h);
      ctx.fillStyle = `rgba(${a.color.join(',')},.35)`; ctx.fillRect(x + 3, y + 3, CELL - 6, CELL - 6);
      ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.strokeRect(x + 3, y + 3, CELL - 6, CELL - 6);
    }
    for (let i = 0; i < visibleCells.length; i += 1) for (let j = i + 1; j < visibleCells.length; j += 1) {
      const p = visibleCells[i], q = visibleCells[j];
      const dx = q[0] - p[0], dy = q[1] - p[1];
      if (Math.abs(dx) + Math.abs(dy) !== 1 || p[2] === q[2]) continue;
      const [ax, ay] = proj(p[0], p[1], p[2]), [bx, by] = proj(q[0], q[1], q[2]);
      let pts;
      if (dx) { const ea = dx > 0 ? ax + CELL : ax, eb = dx > 0 ? bx : bx + CELL; pts = [[ea, ay], [eb, by], [eb, by + CELL], [ea, ay + CELL]]; }
      else { const ea = dy > 0 ? ay + CELL : ay, eb = dy > 0 ? by : by + CELL; pts = [[ax, ea], [ax + CELL, ea], [bx + CELL, eb], [bx, eb]]; }
      ctx.beginPath(); pts.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y))); ctx.closePath();
      ctx.fillStyle = 'rgba(242,201,76,.55)'; ctx.fill(); ctx.strokeStyle = '#f2c94c'; ctx.stroke();
    }
    const n = a.cells.length;
    const offs = a.cells.map(([c, r]) => [c - cc, r - cr]);
    const avx = offs.reduce((s, o) => s + o[0], 0) / n, avy = offs.reduce((s, o) => s + o[1], 0) / n;
    const xs = offs.map((o) => o[0]), ys = offs.map((o) => o[1]);
    const fills = n === (Math.max(...xs) - Math.min(...xs) + 1) * (Math.max(...ys) - Math.min(...ys) + 1);
    const damping = fills ? 1 : 1 - 1 / n;
    const [sx, sy] = PV((cc + 0.5 + damping * avx) * CELL, (cr + 0.5 + damping * avy) * CELL, ch);
    const rad = n === 1 ? 11 : 15;
    ctx.beginPath(); ctx.arc(sx, sy, rad, 0, Math.PI * 2); ctx.fillStyle = col; ctx.fill(); ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.stroke();
    ctx.font = '11px "Noto Sans TC",sans-serif'; ctx.fillStyle = '#000'; ctx.fillText(a.label, sx - 6, sy + 4);
  };
  const drawOverlays = () => {
    if (showGrid) {
      ctx.strokeStyle = 'rgba(255,255,255,.28)'; ctx.lineWidth = 1 / zoom;
      ctx.beginPath();
      for (let c = 0; c <= COLS; c += 1) { ctx.moveTo(c * CELL, 0); ctx.lineTo(c * CELL, WORLD_H); }
      for (let r = 0; r <= ROWS; r += 1) { ctx.moveTo(0, r * CELL); ctx.lineTo(WORLD_W, r * CELL); }
      ctx.stroke();
      ctx.strokeStyle = '#fff'; ctx.lineWidth = 2 / zoom; ctx.strokeRect(0, 0, WORLD_W, WORLD_H);
      label('world origin (0,0)', 4, -6);
    }
    if (showLabels) {
      for (const s of S.surfaces) {
        const side = surfaceSide(s.cells);
        const isCut = cut !== null && cut >= 0 && s.elevation > cut;
        const disp = isCut ? cut : s.elevation;
        for (const [c, r] of s.cells) { const [x, y] = proj(c, r, disp); label(String(s.elevation), x + 11, y + 20); }
      }
    }
  };

  // ---- 主 render ----
  const render = () => {
    pending_frame = false;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = '#0b0a08'; ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(dpr * zoom, 0, 0, dpr * zoom, dpr * panX, dpr * panY);
    ctx.imageSmoothingEnabled = false;
    ctx.strokeStyle = 'rgba(160,160,180,.6)'; ctx.lineWidth = 2 / zoom; ctx.strokeRect(0, 0, WORLD_W, WORLD_H);
    // 統一 y-sort：row 由北到南；每 row 先畫戶外格（面→頂面），再畫腳印底邊落在這 row 的建築／道具／演員
    sideCacheFrame = new Map();
    const objects = [];
    const indoorBy = new Map();
    S.actors_fixture.forEach((a) => { if (a.indoor) { if (!indoorBy.has(a.indoor)) indoorBy.set(a.indoor, []); indoorBy.get(a.indoor).push(a); } });
    if (!(cut !== null && cut < 0)) buildings.forEach((b) => objects.push([b.oy + b.footprint.rows - 1, 0, () => drawBuilding(b, indoorBy.get(b.building_id) || [])]));
    S.props.forEach((p) => { if (p.on) return; objects.push([p.cell[1] + p.footprint[1] - 1, 1, () => {   // R38：子道具由父道具畫
      drawProp(p);
      S.props.filter((q) => q.on === p.id).sort((a, b) => (a.cell[1] + a.footprint[1]) - (b.cell[1] + b.footprint[1])).forEach(drawProp);
    }]); });
    S.actors_fixture.forEach((a) => {
      if (a.indoor) return;                                              // 室內演員由建築在正確層次畫
      objects.push([Math.max(...a.cells.map((c) => c[1])), 2, () => drawActor(a)]);
    });
    objects.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    let oi = 0;
    // R24：同一 row 內從離鏡頭中心最遠的格畫到最近的格（鏡頭右側由右往左、左側由左往右）
    const camCol = camWorldX() / CELL;
    const colOrder = [];
    for (let c = 0; c < COLS; c += 1) if (c + 0.5 <= camCol) colOrder.push(c);
    for (let c = COLS - 1; c >= 0; c -= 1) if (c + 0.5 > camCol) colOrder.push(c);
    for (let row = 0; row < ROWS; row += 1) {
      for (const c of colOrder) drawOutdoorCell(c, row);
      while (oi < objects.length && objects[oi][0] === row) { objects[oi][2](); oi += 1; }
    }
    if (showSurfaces) drawSurfaceLabels();
    drawOverlays();
    // 鏡頭中心十字
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.strokeStyle = '#c878ff'; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(cssW / 2 - 12, cssH / 2); ctx.lineTo(cssW / 2 + 12, cssH / 2); ctx.moveTo(cssW / 2, cssH / 2 - 12); ctx.lineTo(cssW / 2, cssH / 2 + 12); ctx.stroke();
    const cc = Math.floor(camWorldX() / CELL), cr = Math.floor(((cssH / 2 - panY) / zoom) / CELL);
    posText.textContent = `中心格：${cc}, ${cr}｜縮放 ${zoom}×`;
    stateText.textContent = `${cut === null ? '全部高度' : 'H' + cut + ' 剖面'}｜ΔY ${PJ.rise_ratio} 格｜ΔX ${PJ.side_shift_ratio} 格｜${mode === 'camera' ? '跟隨鏡頭中心' : '固定向右'}｜中鍵拖曳、滾輪縮放`;
  };
  const request = () => { if (!pending_frame) { pending_frame = true; requestAnimationFrame(render); } };

  // ---- 互動 ----
  canvas.addEventListener('mousedown', (e) => { if (e.button === 1) e.preventDefault(); });
  canvas.addEventListener('pointerdown', (e) => {
    if (e.button !== 1 && e.button !== 0) return;
    dragging = true; lastX = e.clientX; lastY = e.clientY; canvas.classList.add('drag'); canvas.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  canvas.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    panX += e.clientX - lastX; panY += e.clientY - lastY; lastX = e.clientX; lastY = e.clientY; request();
  });
  const endDrag = (e) => { dragging = false; canvas.classList.remove('drag'); if (e.pointerId !== undefined) try { canvas.releasePointerCapture(e.pointerId); } catch (_) { /* noop */ } };
  canvas.addEventListener('pointerup', endDrag); canvas.addEventListener('pointercancel', endDrag);
  canvas.addEventListener('contextmenu', (e) => e.preventDefault());
  canvas.addEventListener('auxclick', (e) => e.preventDefault());
  const ZOOMS = [0.5, 0.75, 1, 1.5, 2, 3, 4];
  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    const i = ZOOMS.indexOf(zoom), ni = Math.max(0, Math.min(ZOOMS.length - 1, i + (e.deltaY < 0 ? 1 : -1)));
    if (ni === i) return;
    const nz = ZOOMS[ni];
    panX = mx - (mx - panX) * nz / zoom; panY = my - (my - panY) * nz / zoom; zoom = nz; request();
  }, { passive: false });
  root.querySelectorAll('[data-layer]').forEach((btn) => btn.addEventListener('click', () => {
    root.querySelectorAll('[data-layer]').forEach((b) => b.classList.toggle('active', b === btn));
    const v = btn.getAttribute('data-layer'); cut = v === 'all' ? null : Number(v); request();
  }));
  root.querySelectorAll('[data-mode]').forEach((btn) => btn.addEventListener('click', () => {
    root.querySelectorAll('[data-mode]').forEach((b) => b.classList.toggle('active', b === btn));
    mode = btn.getAttribute('data-mode'); request();
  }));
  root.querySelectorAll('[data-toggle]').forEach((btn) => btn.addEventListener('click', () => {
    const t = btn.getAttribute('data-toggle');
    if (t === 'grid') showGrid = !showGrid; if (t === 'labels') showLabels = !showLabels; if (t === 'surfaces') showSurfaces = !showSurfaces;
    btn.classList.toggle('active'); request();
  }));
  root.querySelector('[data-reset]').addEventListener('click', resetPan);
  // 可程式化視角：驗證用。goto(col,row,zoom,cut)：把世界格 (col,row) 放到畫面中心
  window.PLM_VIEW = {
    goto: (col, row, z = 3, cutValue = null) => {
      zoom = z; cut = cutValue;
      root.querySelectorAll('[data-layer]').forEach((b) => b.classList.toggle('active', b.getAttribute('data-layer') === (cutValue === null ? 'all' : String(cutValue))));
      panX = cssW / 2 - (col + 0.5) * CELL * zoom; panY = cssH / 2 - (row + 0.5) * CELL * zoom; render();   // 同步 render：背景分頁 rAF 不會跑
    },
    state: () => ({ zoom, cut, panX, panY, cssW, cssH, camCol: camWorldX() / CELL }),
  };
  root.querySelector('[data-layer="all"]').classList.add('active');
  window.addEventListener('resize', resize);
  Promise.all(pending).then(() => { resize(); resetPan(); });
})();
