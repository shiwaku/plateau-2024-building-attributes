# PLATEAU 2024年度 建物利用現況調査 属性整備都市マップ

Project PLATEAU 2024年度の3D都市モデルにおける**建物利用現況調査の属性整備状況**を全国230都市について整理・可視化したものです。

## デモ

👉 **[マップを開く（plateau_building_survey_map.html）](./plateau_building_survey_map.html)**

![マップスクリーンショット](./docs/screenshot.png)

## 概要

国土交通省が公開している「[3D都市モデル（Project PLATEAU）属性情報公開リスト](https://www.mlit.go.jp/plateau/)」（2024年度版）をもとに、建物利用現況調査に対応する属性（延床面積・階数・構造種別など）の整備状況を都市単位で集計・地図化しました。

### 対象属性（29属性）

| 名前空間 | 属性 |
|---|---|
| `bldg::` | 用途、建築年、地上階数、地下階数 |
| `uro::` | 延床面積、建築面積、図形面積、敷地面積、構造種別、構造種別（独自）、耐火構造種別、建築物の高さ、空き家区分、調査年、建物利用現況（大/中/小/詳細分類）、階用途（1階・2階以上・地下）など |

### 主要属性の整備都市数（全230都市中）

| 属性 | 都市数 |
|---|---:|
| 調査年 | 220 |
| 用途（bldg） | 203 |
| 地上階数（bldg） | 191 |
| 地下階数（bldg） | 140 |
| 構造種別 | 116 |
| 耐火構造種別 | 115 |
| 延床面積 | 101 |
| 建築面積 | 89 |

## マップの使い方

### 属性フィルターモード
チェックした属性を**すべて保有する都市のみ**を表示します（AND条件）。  
例：「延床面積」「地上階数」「構造種別」にチェック → 3属性を揃えて整備している都市を確認。

### 保有属性数モード
29属性のうち何属性を保有しているかに応じた青グラデーションのコロプレスマップを表示します。

### クリック
都市ポリゴンをクリックすると、全29属性の保有状況をポップアップで確認できます。

## ファイル構成

```
.
├── plateau_building_survey_map.html        # MapLibreインタラクティブマップ（メイン成果物）
├── scripts/
│   └── generate.py                         # CSV・HTML生成スクリプト
├── data/
│   └── attributedata_2024_v4_r3.xlsx       # 元データ（PLATEAU属性情報公開リスト 2024年度版）
└── output/
    ├── uro_building_survey_cities.csv       # 建物利用現況調査29属性の属性別都市リスト
    ├── building_survey_attrs_cities.csv     # 延床面積・階数・構造種別の保有状況（全230都市）
    └── uro_building_utilization_cities.csv  # uro::建物利用現況グループ全38属性の都市リスト
```

## スクリプトの実行方法

```bash
pip install openpyxl geopandas pandas
python scripts/generate.py
```

N03行政区域データ（`N03-20250101_dissolved.parquet`）がローカルにある場合はポリゴンマップを、  
ない場合は国土地理院APIで座標を取得してポイントマップを生成します。

## データソース

- **PLATEAU属性情報公開リスト（2024年度）**: [国土交通省 Project PLATEAU](https://www.mlit.go.jp/plateau/)
- **行政区域データ（N03-2025）**: [国土数値情報](https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2024.html)（国土交通省）

## 技術スタック

- **地図ライブラリ**: [MapLibre GL JS](https://maplibre.org/) v4.7.1
- **ベースマップ**: [CARTO Positron](https://basemaps.cartocdn.com/)
- **データ処理**: Python（geopandas, openpyxl）
- **ジオコーディング**: 国土地理院 住所検索API

## ライセンス

- 元データ（PLATEAU属性情報公開リスト）：[国土交通省 利用規約](https://www.mlit.go.jp/plateau/site-policy/)に従います
- 国土数値情報：[国土数値情報利用規約](https://nlftp.mlit.go.jp/ksj/other/yakkan.html)に従います
