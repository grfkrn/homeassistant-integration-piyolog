# PiyoLog for Home Assistant

育児記録アプリ「ぴよログ」の公式 **データフィード** を Home Assistant に取り込むカスタム統合です。
フィードURLを設定するだけで、授乳・睡眠・排泄・身体計測などの記録がセンサーとして表示されます。読み取り専用です（ぴよログへの記録の書き込みはできません）。

A Home Assistant custom integration for the official **PiyoLog data feed** (read-only).
Set a feed URL and your baby's records — feeding, sleep, diapers, body measurements — appear as sensors.

## 必要なもの

- ぴよログアプリ（v9.4.0以降）で作成したデータフィードのURL
  - アプリの「設定 → データフィード」から作成します。対象のお子様・取得期間・有効期限を選んでください
  - フィードURL自体が認証情報です。パスワードと同じように扱ってください
- （推奨）プレミアムの28日フィードを2本目のURLとして追加すると、体重・身長など毎日は記録されない項目の最新値が安定します

## インストール

### HACS（カスタムリポジトリ）

1. HACS → ⋯ → カスタムリポジトリに `https://github.com/grfkrn/homeassistant-integration-piyolog` を「統合」として追加
2. 「PiyoLog」をインストールし、Home Assistant を再起動
3. 設定 → デバイスとサービス → 統合を追加 → 「PiyoLog」
4. ラベル（デバイス名）とフィードURLを入力

### 手動

`custom_components/piyolog` フォルダを Home Assistant の `config/custom_components/` にコピーして再起動し、上記3以降を行ってください。

## センサー

お子様1人につき1つのデバイスが作られ、entity_id は `sensor.piyolog_*` で統一されます。

| 種類 | 例 | 内容 |
| --- | --- | --- |
| 最終記録 | `sensor.piyolog_last_breast_feeding` | 種類ごとの最新記録の日時。属性に量・左右の授乳時間・当日の回数など |
| 身体計測 | `sensor.piyolog_weight` | 最新の測定値。属性に計測日時 |
| 当日集計 | `sensor.piyolog_today_formula_total` | 今日の合計・回数（JST等のローカル日付区切り） |
| 状態 | `binary_sensor.piyolog_sleeping` | いま寝ているか（Sleep/WakeUp のペアから判定） |
| タイムライン | `sensor.piyolog_timeline` | 属性 `records` に当日の記録一覧（新しい順） |
| フィード状態 | `sensor.piyolog_last_update` | フィードの生成時刻と記録件数 |

カスタム記録（Custom1〜10）は `sensor.piyolog_last_custom` に集約されます（フィードにはカスタム記録の設定名が含まれないため）。

## 設定

- 取得間隔：統合の「設定」からメインフィードの間隔を変更できます（既定5分、1〜60分）。28日フィードは公式のキャッシュ保持時間に合わせて最大15分に1回だけ取得します
- お子様が複数いる場合は、フィードごとに統合を追加してください

## 注意事項

- フィードから取れるのは最大で直近28日分です。それより前の記録の蓄積には Home Assistant の履歴・長期統計を使ってください
- フィードが期限切れ・失効すると404が返り続け、修復通知が表示されます。アプリで新しいフィードを作成して再設定してください
- この統合はぴよログ公式のデータフィード仕様（schema v1）に基づく非公式のサードパーティ製です。ぴよログおよび PiyoLog の名称・ロゴは、権利者である Sakabou Inc.（株式会社サカボウ）に帰属します

## ライセンス

MIT License. Copyright (c) 2026 grfkrn.
