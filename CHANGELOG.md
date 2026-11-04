# Changelog

## 1.2.0 (2026-11-04)

- `sensor.piyolog_today_breast_feeding_total`（今日の母乳量）を追加：母乳レコードに記録された ml の当日合計。属性に `measured_count`（ml記録のある回数）と `count_today`（授乳回数）。ml未記録の回は合計に含めない

## 1.1.1 (2026-11-04)

- うんち系センサー（`piyolog_last_poop` / `piyolog_today_poop_count`）のアイコンが表示されない問題を修正：存在しない `mdi:emoticon-poo` を正しい `mdi:emoticon-poop` に変更

## 1.1.0 (2026-11-04)

- `sensor.piyolog_recent_events`（直近の記録）を追加：日付を問わずフィード範囲内の直近100件を新しい順に属性 `records` へ保持。状態は最新記録の日時、属性に `count`（保持件数）と `total_records`（フィード内総件数）を持つ

## 1.0.0 (2026-11-04)

- 初回リリース
- ぴよログ公式データフィード（schema v1）の読み取りに対応
- フィード2本構成（短期フィード＋28日フィード）に対応
- 最終記録センサー、身体計測センサー、当日集計センサー、睡眠中バイナリセンサー、タイムラインセンサーを提供
- フィード失効（404継続）時の修復通知、診断（diagnostics）対応
