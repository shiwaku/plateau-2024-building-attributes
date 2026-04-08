"""
PLATEAU 2024年度 建物利用現況調査 属性整備都市マップ 生成スクリプト

使い方:
    python scripts/generate.py

出力:
    output/uro_building_survey_cities.csv        - 属性別の整備都市リスト
    output/building_survey_attrs_cities.csv      - 都市別の属性保有状況
    plateau_building_survey_map.html             - MapLibre インタラクティブマップ

依存ライブラリ:
    pip install openpyxl geopandas pandas
"""

import json
import subprocess
import openpyxl
import geopandas as gpd
import pandas as pd
from pathlib import Path

# --- パス設定 ---
ROOT   = Path(__file__).parent.parent
XLSX   = ROOT / "data" / "attributedata_2024_v4_r3.xlsx"
N03    = Path("/mnt/c/Users/yshiw/Documents/GIS/digital/abr/address_all.csv/N03-20250101_GML/N03-20250101_dissolved.parquet")
OUTPUT = ROOT / "output"
HTML   = ROOT / "index.html"

# --- 対象属性定義 ---
SURVEY_BLDG = [
    "bldg::用途", "bldg::建築年", "bldg::地上階数", "bldg::地下階数",
]
SURVEY_URO = [
    "uro::建物利用現況（大分類）", "uro::建物利用現況（大分類2）",
    "uro::建物利用現況（中分類）", "uro::建物利用現況（小分類）",
    "uro::建物利用現況（詳細分類）", "uro::建物利用現況（詳細分類2）",
    "uro::建物利用現況（詳細分類3）",
    "uro::1階用途", "uro::2階（以上）用途", "uro::3階（以上）用途",
    "uro::地下用途", "uro::地下1階用途", "uro::地下2階用途",
    "uro::構造種別", "uro::構造種別（独自）", "uro::耐火構造種別",
    "uro::延床面積", "uro::建築面積", "uro::図形面積", "uro::敷地面積",
    "uro::空き家区分", "uro::建築物の高さ", "uro::調査年",
    "uro::図面対象番号", "uro::備考",
]
ALL_ATTRS  = SURVEY_BLDG + SURVEY_URO
ATTR_SHORT = {a: a.replace("uro::", "").replace("bldg::", "") for a in ALL_ATTRS}

# V4建築物シート内の建築物地物型の行範囲
BLDG_START, BLDG_END = 14, 777


def load_excel():
    """Excelから都市情報・属性行インデックスを読み込む"""
    print("Excelを読み込み中...")
    wb = openpyxl.load_workbook(XLSX, read_only=True)
    ws = wb["V4建築物"]
    all_rows = list(ws.iter_rows(values_only=True))

    city_codes = [str(c).zfill(5) for c in all_rows[2][7:] if c is not None]
    regions    = [r for r, c in zip(all_rows[3][7:], all_rows[2][7:]) if c is not None]
    prefs      = [p for p, c in zip(all_rows[4][7:], all_rows[2][7:]) if c is not None]
    city_names = [n for n, c in zip(all_rows[5][7:], all_rows[2][7:]) if c is not None]

    # 属性行インデックスを収集
    attr_rows = {}
    in_uro_group = False
    for i in range(BLDG_START, BLDG_END):
        row = all_rows[i]
        if row[1] == "uro::建物利用現況":
            in_uro_group = True
            continue
        if in_uro_group and row[1] is not None:
            in_uro_group = False
        if in_uro_group and row[2] in SURVEY_URO:
            attr_rows[row[2]] = i
        if row[1] in SURVEY_BLDG:
            attr_rows[row[1]] = i

    return all_rows, city_codes, regions, prefs, city_names, attr_rows


def build_city_records(all_rows, city_codes, regions, prefs, city_names, attr_rows):
    """都市ごとの属性保有状況を辞書リストで返す"""
    records = []
    for j, (code, region, pref, name) in enumerate(zip(city_codes, regions, prefs, city_names)):
        record = {"code": code, "region": region, "pref": pref, "name": name}
        for attr in ALL_ATTRS:
            short = ATTR_SHORT[attr]
            if attr in attr_rows:
                row = all_rows[attr_rows[attr]]
                record[short] = 1 if row[7 + j] is not None else 0
            else:
                record[short] = 0
        record["attr_count"] = sum(
            record[ATTR_SHORT[a]] for a in ALL_ATTRS
        )
        records.append(record)
    return records


def save_csvs(records, attr_rows, all_rows, city_codes, city_names):
    """CSV出力"""
    OUTPUT.mkdir(exist_ok=True)

    # 1. 属性別の整備都市リスト
    rows = []
    for attr in ALL_ATTRS:
        short = ATTR_SHORT[attr]
        if attr not in attr_rows:
            continue
        row = all_rows[attr_rows[attr]]
        cities = [
            f"{city_codes[j]}:{city_names[j]}"
            for j, v in enumerate(row[7:])
            if v is not None
        ]
        rows.append({"属性名": attr, "都市数": len(cities), "都市リスト": ";".join(cities)})
    pd.DataFrame(rows).to_csv(OUTPUT / "uro_building_survey_cities.csv", index=False, encoding="utf-8-sig")
    print(f"  -> output/uro_building_survey_cities.csv ({len(rows)} 属性)")

    # 2. 都市別の属性保有状況（延床面積・階数・構造種別）
    target_shorts = ["延床面積", "地上階数", "地下階数", "構造種別"]
    out_rows = []
    for rec in records:
        out_rows.append({
            "市区町村コード": rec["code"],
            "地方": rec["region"],
            "都道府県": rec["pref"],
            "市区町村名": rec["name"],
            **{k: "○" if rec[k] == 1 else "-" for k in target_shorts},
            "保有属性数": sum(1 for k in target_shorts if rec[k] == 1),
        })
    pd.DataFrame(out_rows).to_csv(OUTPUT / "building_survey_attrs_cities.csv", index=False, encoding="utf-8-sig")
    print(f"  -> output/building_survey_attrs_cities.csv ({len(out_rows)} 都市)")


def geocode_cities(records):
    """GSI住所検索APIで座標取得（N03データがない場合のフォールバック）"""
    print("座標を取得中（GSI API）...")
    coords = {}
    for i, rec in enumerate(records):
        query = f"{rec['pref']}{rec['name']}"
        result = subprocess.run(
            ["curl", "-s", "--max-time", "5",
             f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={query}"],
            capture_output=True, text=True,
        )
        try:
            data = json.loads(result.stdout)
            if data:
                coords[rec["code"]] = data[0]["geometry"]["coordinates"]
        except Exception:
            pass
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(records)} 完了...")
    # 離島等の補完
    fallback = {"13362": [139.519915, 34.086117], "13401": [139.789062, 33.112785]}
    coords.update({k: v for k, v in fallback.items() if k not in coords})
    print(f"  座標取得: {len(coords)}/{len(records)} 都市")
    return coords


def build_geojson(records, city_attr_map):
    """N03ポリゴン + 属性データで GeoJSON を構築"""
    if not N03.exists():
        print("N03データが見つかりません。GSI APIで座標を取得します...")
        coords = geocode_cities(records)
        features = []
        for rec in records:
            code = rec["code"]
            if code not in coords:
                continue
            lon, lat = coords[code]
            features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": rec,
            })
        return {"type": "FeatureCollection", "features": features}, "point"

    print("N03ポリゴンデータを読み込み中...")
    gdf_n03 = gpd.read_parquet(N03)
    gdf_n03["N03_007"] = gdf_n03["N03_007"].astype(str).str.zfill(5)

    plateau_codes = set(city_attr_map.keys())

    # 政令指定都市: 区ポリゴンを市単位に統合
    unmatched = plateau_codes - set(gdf_n03["N03_007"])
    extra = []
    for city_code in unmatched:
        prefix = city_code[:4]
        wards = gdf_n03[gdf_n03["N03_007"].str.startswith(prefix)]
        if len(wards) == 0:
            continue
        dissolved = wards.dissolve()[["geometry"]].reset_index(drop=True)
        dissolved["N03_007"] = city_code
        extra.append(dissolved)

    gdf_direct = gdf_n03[gdf_n03["N03_007"].isin(plateau_codes)].copy()
    if extra:
        gdf_all = pd.concat([gdf_direct, *extra], ignore_index=True)
    else:
        gdf_all = gdf_direct

    attr_df = pd.DataFrame(list(city_attr_map.values()))
    attr_df["N03_007"] = attr_df["code"]
    gdf_merged = gdf_all.merge(attr_df, on="N03_007", how="left")
    gdf_merged["geometry"] = gdf_merged["geometry"].simplify(0.001, preserve_topology=True)

    print(f"  ポリゴン数: {len(gdf_merged)}")
    return json.loads(gdf_merged.to_json()), "polygon"


def generate_html(geojson, geom_type):
    """MapLibre インタラクティブHTMLを生成"""
    print("HTMLを生成中...")

    attr_shorts = [ATTR_SHORT[a] for a in ALL_ATTRS]
    bldg_shorts = [ATTR_SHORT[a] for a in SURVEY_BLDG]
    uro_shorts  = [ATTR_SHORT[a] for a in SURVEY_URO]

    labels = {
        "用途": "用途", "建築年": "建築年", "地上階数": "地上階数", "地下階数": "地下階数",
        "建物利用現況（大分類）": "利用現況(大)", "建物利用現況（大分類2）": "利用現況(大2)",
        "建物利用現況（中分類）": "利用現況(中)", "建物利用現況（小分類）": "利用現況(小)",
        "建物利用現況（詳細分類）": "利用現況(詳細)", "建物利用現況（詳細分類2）": "利用現況(詳細2)",
        "建物利用現況（詳細分類3）": "利用現況(詳細3)",
        "1階用途": "1階用途", "2階（以上）用途": "2階以上用途", "3階（以上）用途": "3階以上用途",
        "地下用途": "地下用途", "地下1階用途": "地下1階用途", "地下2階用途": "地下2階用途",
        "構造種別": "構造種別", "構造種別（独自）": "構造種別(独自)", "耐火構造種別": "耐火構造種別",
        "延床面積": "延床面積", "建築面積": "建築面積", "図形面積": "図形面積", "敷地面積": "敷地面積",
        "空き家区分": "空き家区分", "建築物の高さ": "建築物の高さ", "調査年": "調査年",
        "図面対象番号": "図面対象番号", "備考": "備考",
    }

    layer_type = "fill" if geom_type == "polygon" else "circle"
    geojson_str = json.dumps(geojson, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PLATEAU 2024年度 建物利用現況調査 属性整備都市マップ</title>
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Hiragino Sans','Meiryo',sans-serif;font-size:12px;}}
#map{{position:absolute;top:0;bottom:0;width:100%;}}
#panel{{
  position:absolute;top:10px;left:10px;
  background:rgba(255,255,255,0.96);padding:12px 14px;border-radius:8px;
  box-shadow:0 2px 10px rgba(0,0,0,0.25);width:270px;
  max-height:calc(100vh - 20px);overflow-y:auto;z-index:2;
  transition:transform 0.25s ease;
}}
#panel h2{{font-size:12px;font-weight:bold;margin-bottom:8px;color:#1a1a2e;line-height:1.4;}}
.panel-header{{display:flex;align-items:flex-start;justify-content:space-between;gap:6px;}}
#close-btn{{
  flex-shrink:0;display:none;
  background:none;border:none;cursor:pointer;
  font-size:18px;line-height:1;color:#666;padding:0 2px;
}}
#close-btn:hover{{color:#333;}}
.mode-btn{{display:flex;gap:4px;margin-bottom:10px;}}
.mode-btn button{{flex:1;padding:5px 4px;font-size:11px;border:1px solid #ccc;border-radius:4px;cursor:pointer;background:#fff;}}
.mode-btn button.active{{background:#2c6fad;color:#fff;border-color:#2c6fad;}}
.section-title{{font-size:11px;font-weight:bold;color:#555;margin:8px 0 4px;padding-bottom:2px;border-bottom:1px solid #eee;}}
.chk-row{{display:flex;align-items:center;gap:5px;padding:2px 0;cursor:pointer;}}
.chk-row input{{cursor:pointer;accent-color:#2c6fad;}}
.chk-row span{{font-size:11px;}}
#stats{{margin-top:8px;padding:6px 8px;background:#f0f6ff;border-radius:4px;font-size:11px;color:#333;font-weight:bold;}}
.legend-wrap{{margin-top:8px;}}
.lg-item{{display:flex;align-items:center;gap:6px;margin:3px 0;font-size:11px;}}
.lg-box{{width:14px;height:14px;border-radius:2px;flex-shrink:0;}}
.maplibregl-popup-content{{font-size:12px;padding:10px 12px;border-radius:6px;box-shadow:0 2px 8px rgba(0,0,0,0.2);max-width:340px;}}
.pop-title{{font-weight:bold;font-size:13px;margin-bottom:4px;}}
.pop-sub{{color:#666;font-size:11px;margin-bottom:8px;}}
.pop-grid{{display:grid;grid-template-columns:1fr 1fr;gap:2px 6px;}}
.pop-item{{display:flex;align-items:center;gap:4px;font-size:11px;padding:1px 0;}}
.dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;}}
.has{{color:#1a6bb5;}}.no{{color:#bbb;}}
#menu-btn{{
  display:none;
  position:absolute;top:10px;left:10px;z-index:3;
  background:#2c6fad;color:#fff;border:none;border-radius:8px;
  width:40px;height:40px;font-size:20px;cursor:pointer;
  box-shadow:0 2px 8px rgba(0,0,0,0.3);
  align-items:center;justify-content:center;
}}
@media(max-width:600px){{
  #panel{{
    top:0;left:0;right:0;bottom:0;
    width:100%;max-height:100%;
    border-radius:0;
    transform:translateX(-100%);
  }}
  #panel.open{{transform:translateX(0);}}
  #close-btn{{display:block;}}
  #menu-btn{{display:flex;}}
}}
</style>
</head>
<body>
<div id="map"></div>
<button id="menu-btn" onclick="openPanel()" aria-label="メニューを開く">☰</button>
<div id="panel">
  <div class="panel-header">
    <h2>🏙️ PLATEAU 2024年度<br>建物利用現況調査 属性整備都市</h2>
    <button id="close-btn" onclick="closePanel()" aria-label="閉じる">✕</button>
  </div>
  <div class="mode-btn">
    <button class="active" id="btn-filter" onclick="setMode('filter')">属性フィルター</button>
    <button id="btn-count" onclick="setMode('count')">保有属性数</button>
  </div>
  <div id="filter-panel">
    <div class="section-title">▼ bldg:: (CityGML標準属性)</div>
    <div id="bldg-chks"></div>
    <div class="section-title">▼ uro:: (建物利用現況)</div>
    <div id="uro-chks"></div>
    <div style="margin-top:6px;">
      <label class="chk-row">
        <input type="checkbox" id="chk-all" onchange="toggleAll(this)">
        <span><b>すべて選択/解除</b></span>
      </label>
    </div>
  </div>
  <div id="count-panel" style="display:none;">
    <div class="legend-wrap">
      <div class="section-title">凡例（保有属性数 / 29）</div>
      <div class="lg-item"><div class="lg-box" style="background:#08306b"></div>25〜29属性</div>
      <div class="lg-item"><div class="lg-box" style="background:#2171b5"></div>15〜24属性</div>
      <div class="lg-item"><div class="lg-box" style="background:#6baed6"></div>8〜14属性</div>
      <div class="lg-item"><div class="lg-box" style="background:#c6dbef"></div>3〜7属性</div>
      <div class="lg-item"><div class="lg-box" style="background:#f7fbff;border:1px solid #ccc"></div>1〜2属性</div>
      <div class="lg-item"><div class="lg-box" style="background:#e0e0e0;border:1px solid #ccc"></div>0属性</div>
    </div>
  </div>
  <div id="stats">表示中: <span id="stat-n">---</span> / 230 都市</div>
</div>
<script>
const GEOJSON = {geojson_str};
const BLDG_ATTRS = {json.dumps(bldg_shorts, ensure_ascii=False)};
const URO_ATTRS  = {json.dumps(uro_shorts, ensure_ascii=False)};
const ALL_ATTRS  = {json.dumps(attr_shorts, ensure_ascii=False)};
const LABELS = {json.dumps(labels, ensure_ascii=False)};
const GEOM_TYPE = "{geom_type}";

let mode = 'filter';

function openPanel()  {{ document.getElementById('panel').classList.add('open');    document.getElementById('menu-btn').style.display='none'; }}
function closePanel() {{ document.getElementById('panel').classList.remove('open'); document.getElementById('menu-btn').style.display='flex'; }}

function initCheckboxes() {{
  ['bldg','uro'].forEach(ns => {{
    const attrs = ns === 'bldg' ? BLDG_ATTRS : URO_ATTRS;
    const div = document.getElementById(ns+'-chks');
    attrs.forEach(a => {{
      div.innerHTML += `<label class="chk-row"><input type="checkbox" class="ac" value="${{a}}" onchange="applyFilter()"><span>${{LABELS[a]||a}}</span></label>`;
    }});
  }});
}}

function toggleAll(el) {{
  document.querySelectorAll('.ac').forEach(c => c.checked = el.checked);
  applyFilter();
}}

function getChecked() {{
  return [...document.querySelectorAll('.ac:checked')].map(c => c.value);
}}

function setMode(m) {{
  mode = m;
  document.getElementById('filter-panel').style.display = m==='filter' ? '' : 'none';
  document.getElementById('count-panel').style.display  = m==='count'  ? '' : 'none';
  document.getElementById('btn-filter').className = m==='filter' ? 'active' : '';
  document.getElementById('btn-count').className  = m==='count'  ? 'active' : '';
  if (m === 'count') applyCount(); else applyFilter();
}}

function applyFilter() {{
  const checked = getChecked();
  const filtered = {{
    type: 'FeatureCollection',
    features: GEOJSON.features.filter(f =>
      checked.length === 0 || checked.every(a => f.properties[a] === 1)
    )
  }};
  map.getSource('cities').setData(filtered);
  const color = checked.length ? '#27ae60' : '#2c6fad';
  if (GEOM_TYPE === 'polygon') {{
    map.setPaintProperty('cities-fill','fill-color', color);
    map.setPaintProperty('cities-fill','fill-opacity', 0.6);
  }} else {{
    map.setPaintProperty('cities-circle','circle-color', color);
  }}
  document.getElementById('stat-n').textContent = filtered.features.length;
}}

function applyCount() {{
  const fc = {{
    type: 'FeatureCollection',
    features: GEOJSON.features.map(f => ({{
      ...f,
      properties: {{...f.properties, attr_count: ALL_ATTRS.filter(a => f.properties[a] === 1).length}}
    }}))
  }};
  map.getSource('cities').setData(fc);
  const colorExpr = ['step',['get','attr_count'],'#e0e0e0',1,'#f7fbff',3,'#c6dbef',8,'#6baed6',15,'#2171b5',25,'#08306b'];
  if (GEOM_TYPE === 'polygon') {{
    map.setPaintProperty('cities-fill','fill-color', colorExpr);
    map.setPaintProperty('cities-fill','fill-opacity', 0.75);
  }} else {{
    map.setPaintProperty('cities-circle','circle-color', colorExpr);
  }}
  document.getElementById('stat-n').textContent = '230';
}}

const loading = document.createElement('div');
loading.id = 'loading';
loading.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(255,255,255,0.9);padding:16px 24px;border-radius:8px;font-size:14px;z-index:10;box-shadow:0 2px 8px rgba(0,0,0,0.2);';
loading.textContent = '地図を読み込み中...';
document.body.appendChild(loading);

const STYLES = [
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  'https://demotiles.maplibre.org/style.json',
];

const map = new maplibregl.Map({{
  container: 'map',
  style: STYLES[0],
  center: [137.0, 36.5],
  zoom: 4.8,
  hash: true,
}});
map.addControl(new maplibregl.NavigationControl(), 'bottom-right');

map.on('error', (e) => {{
  console.error('MapLibreエラー:', e);
  if (e.error && e.error.status === 404) {{
    loading.textContent = 'フォールバックスタイルに切り替え中...';
    map.setStyle(STYLES[1]);
  }}
}});

map.on('load', () => {{
  loading.remove();
  map.addSource('cities', {{type:'geojson', data: GEOJSON}});
  if (GEOM_TYPE === 'polygon') {{
    map.addLayer({{id:'cities-fill',type:'fill',source:'cities',paint:{{'fill-color':'#2c6fad','fill-opacity':0.6}}}});
    map.addLayer({{id:'cities-line',type:'line',source:'cities',paint:{{'line-color':'#fff','line-width':0.5}}}});
    map.on('click','cities-fill', showPopup);
    map.on('mouseenter','cities-fill',()=>map.getCanvas().style.cursor='pointer');
    map.on('mouseleave','cities-fill',()=>map.getCanvas().style.cursor='');
  }} else {{
    map.addLayer({{id:'cities-circle',type:'circle',source:'cities',paint:{{'circle-radius':7,'circle-color':'#2c6fad','circle-stroke-color':'#fff','circle-stroke-width':1.5,'circle-opacity':0.85}}}});
    map.on('click','cities-circle', showPopup);
    map.on('mouseenter','cities-circle',()=>map.getCanvas().style.cursor='pointer');
    map.on('mouseleave','cities-circle',()=>map.getCanvas().style.cursor='');
  }}
  initCheckboxes();
  applyFilter();
}});

function showPopup(e) {{
  const p = e.features[0].properties;
  const cnt = ALL_ATTRS.filter(a => p[a]===1).length;
  const rows = ALL_ATTRS.map(a => {{
    const has = p[a]===1;
    return `<div class="pop-item ${{has?'has':'no'}}"><div class="dot" style="background:${{has?'#2171b5':'#ddd'}}"></div>${{LABELS[a]||a}}</div>`;
  }}).join('');
  new maplibregl.Popup({{maxWidth:'360px'}})
    .setLngLat(e.lngLat)
    .setHTML(`
      <div class="pop-title">${{p.pref}} ${{p.name}}</div>
      <div class="pop-sub">コード: ${{p.code}} | ${{p.region}}</div>
      <div class="pop-sub">保有属性数: <b style="color:#1a6bb5">${{cnt}} / ${{ALL_ATTRS.length}}</b></div>
      <div class="pop-grid">${{rows}}</div>
    `).addTo(map);
}}
</script>
</body>
</html>"""

    HTML.write_text(html, encoding="utf-8")
    size_kb = HTML.stat().st_size // 1024
    print(f"  -> plateau_building_survey_map.html ({size_kb} KB)")


def main():
    all_rows, city_codes, regions, prefs, city_names, attr_rows = load_excel()
    records = build_city_records(all_rows, city_codes, regions, prefs, city_names, attr_rows)
    city_attr_map = {r["code"]: r for r in records}

    print("CSVを出力中...")
    save_csvs(records, attr_rows, all_rows, city_codes, city_names)

    geojson, geom_type = build_geojson(records, city_attr_map)
    generate_html(geojson, geom_type)

    print("\n完了！")
    print(f"  output/uro_building_survey_cities.csv")
    print(f"  output/building_survey_attrs_cities.csv")
    print(f"  plateau_building_survey_map.html")


if __name__ == "__main__":
    main()
