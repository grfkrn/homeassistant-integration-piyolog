# 対応表リファレンス

README から分けた対応表の一覧です。導入や設定の説明は [README](../README.md) を参照してください。

## フィード項目（`type`）一覧

日本語ラベルはタイムラインやカードで使う表示名です。「主な対応先」にあるエンティティの詳細は、下記の「エンティティ対応表」を参照してください。

| `type` | 日本語ラベル／項目概要 | 主な値・専用項目 | 主な対応先 |
|---|---|---|---|
| `BreastFeeding` | 母乳（直接授乳） | `leftTime`、`rightTime`、`last`、任意の `value.value`（ml） | 最終記録、授乳回数・時間・母乳量、長期統計 |
| `Formula` | ミルク | `value.value`（ml） | 最終記録、今日のミルク量、長期統計 |
| `ExpressedBreastMilk` | 搾母乳 | `value.value`（ml） | 最終記録、今日の搾母乳量、長期統計 |
| `Pumping` | 搾乳 | `value.value`（ml） | 最終記録、今日の搾乳量、長期統計 |
| `Sleep` | 寝る | 開始時刻は `datetime` | 最終記録、睡眠中センサー、睡眠時間 |
| `WakeUp` | 起きる | 終了時刻は `datetime` | 最終記録、睡眠中センサー、睡眠時間、カードの睡眠時間 |
| `Pee` | おしっこ | 発生時刻は `datetime` | 最終記録、今日のおしっこ回数、長期統計 |
| `Poop` | うんち | `details.amount` / `hardness` / `color` | 最終記録、今日のうんち回数、長期統計 |
| `Temperature` | 体温 | `value.value`（°C） | 身体計測、履歴属性、長期統計 |
| `Height` | 身長 | `value.value`（cm） | 身体計測、履歴属性、長期統計 |
| `Weight` | 体重 | `value.value`（kg） | 身体計測、履歴属性、長期統計 |
| `Head` | 頭囲 | `value.value`（cm） | 身体計測、履歴属性、長期統計 |
| `Chest` | 胸囲 | `value.value`（cm） | 身体計測、履歴属性、長期統計 |
| `Foot` | 足サイズ | `value.left`、`value.right`（cm） | 足サイズセンサー |
| `Solid` | 離乳食 | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Snack` | おやつ | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Meal` | ごはん | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Drink` | のみもの | `value.value`（ml） | 最終記録、今日ののみもの量、長期統計 |
| `Cough` | せき | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Vomiting` | 吐く | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Rash` | 発疹 | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Injury` | けが | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Bath` | お風呂 | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Medicine` | くすり | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Hospital` | 病院 | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Walking` | さんぽ | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Vaccine` | 予防接種 | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Milestone` | できた | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Memo` | メモ | 本文は `memo` | 最終記録、タイムライン |
| `Other` | その他 | 時刻と `memo` が中心 | 最終記録、タイムライン |
| `Custom1` ～ `Custom10` | カスタム1～10 | フィードにはアプリ側の設定名が含まれません | <code>sensor.<wbr>piyolog_<wbr>last_<wbr>custom</code> に集約、タイムライン |

どの種類の記録にも `memo` が付く場合があります。また、最終記録センサーは、対象記録に数値の `value.value` がある場合は種類を問わず属性 `value` として取り出します。

## エンティティ対応表

### 表の読み方

- 「状態」は Home Assistant のエンティティの値そのものです
- 「属性」はエンティティの詳細画面やテンプレートから参照できる追加情報です
- 「最新」「最後」は取得できたフィード範囲内での最新を意味します。フィードから外れた過去の記録までは遡れません
- 「今日」はHome Assistant の既定タイムゾーンにおけるローカル日付の0時から24時までです
- 最終記録センサーと身体計測センサーは、対象記録がフィード範囲内に無い場合 `unknown` になります
- 当日集計センサーは対象記録が無い場合も原則として `0` を返します

### 最終記録センサー（25個）

状態はすべて、対応する `type` の最新記録の `datetime` です。対象が複数あるカスタム記録を除き、各センサーには共通属性 `count_today`（今日の同種記録数）が付きます。

共通属性は次のとおりです。

| 属性 | 元になるフィード値 | 内容 |
|---|---|---|
| `count_today` | 同じ `type` の当日記録数 | 値が省略された記録も含めて数えます |
| `value` | `value.value` | 最新記録に数値が入っている場合だけ付きます |
| `unit` | `value.unit` | フィード側の単位文字列をそのまま保持します |
| `memo` | `memo` | 最新記録にメモがある場合だけ付きます |

| entity_id | 表示名 | `type` | 種類固有の対応 |
|---|---|---|---|
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>breast_<wbr>feeding</code> | 最後の授乳 | `BreastFeeding` | `leftTime`（秒）→ `left_minutes`、`rightTime`（秒）→ `right_minutes`、`last` → `last_side`。量がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>formula</code> | 最後のミルク | `Formula` | 量がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>expressed_<wbr>breast_<wbr>milk</code> | 最後の搾母乳 | `ExpressedBreastMilk` | 量がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>pumping</code> | 最後の搾乳 | `Pumping` | 量がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>sleep</code> | 最後に寝た | `Sleep` | 睡眠開始時刻。固有の数値属性はありません |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>wake_<wbr>up</code> | 最後に起きた | `WakeUp` | 起床時刻。睡眠時間は状態には含めず、睡眠集計とカードで扱います |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>pee</code> | 最後のおしっこ | `Pee` | 発生時刻。固有の数値属性はありません |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>poop</code> | 最後のうんち | `Poop` | `details.amount` → `amount`、`details.hardness` → `hardness`、`details.color` → `color`（コード文字列のまま） |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>drink</code> | 最後ののみもの | `Drink` | 量がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>solid</code> | 最後の離乳食 | `Solid` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>snack</code> | 最後のおやつ | `Snack` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>meal</code> | 最後のごはん | `Meal` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>bath</code> | 最後のお風呂 | `Bath` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>medicine</code> | 最後のくすり | `Medicine` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>hospital</code> | 最後の病院 | `Hospital` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>walking</code> | 最後のさんぽ | `Walking` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>vaccine</code> | 最後の予防接種 | `Vaccine` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>milestone</code> | 最後の「できた」 | `Milestone` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>cough</code> | 最後のせき | `Cough` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>vomiting</code> | 最後に吐いた | `Vomiting` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>rash</code> | 最後の発疹 | `Rash` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>injury</code> | 最後のけが | `Injury` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>memo</code> | 最後のメモ | `Memo` | メモ本文は属性 `memo` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>other</code> | 最後のその他 | `Other` | 数値がある場合は `value` / `unit` |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>custom</code> | 最後のカスタム記録 | `Custom1` ～ `Custom10` | 10種類の中で最も新しい記録の日時。属性 `custom_type` に元の `type`、メモがある場合は `memo`。共通属性 `count_today` は付きません |

最終記録センサーの状態は「フィードに記録された時刻」です。Home Assistant がその変化を検出した時刻ではありません。複数件が1回の取得でまとめて入った場合、Home Assistant のログブック上の変更時刻は取得時刻側になりますが、センサーの状態値には各記録の `datetime` が入ります。

### 身体計測センサー（6個）

状態は対応する `type` の最新記録の `value.value` です。足サイズ以外には、計測日時 `measured_at` と、フィード範囲内の全計測点を持つ `history` 属性が付きます。

`history` は古い順の配列で、各要素は `{"time": ローカル時刻のISO文字列, "value": 数値}` です。保持上限は新しい順に200点です。Home Assistant のレコーダーには統合導入前の状態履歴が無いため、導入前の推移をグラフ化したい場合に使えます。

| entity_id | 表示名 | `type` | 状態の単位 | 属性・備考 |
|---|---|---|---|---|
| <code>sensor.<wbr>piyolog_<wbr>weight</code> | 体重 | `Weight` | kg | `measured_at`、`history`。長期統計にも投入します |
| <code>sensor.<wbr>piyolog_<wbr>height</code> | 身長 | `Height` | cm | `measured_at`、`history`。長期統計にも投入します |
| <code>sensor.<wbr>piyolog_<wbr>temperature</code> | 体温 | `Temperature` | °C | `measured_at`、`history`。長期統計にも投入します |
| <code>sensor.<wbr>piyolog_<wbr>head_<wbr>circumference</code> | 頭囲 | `Head` | cm | `measured_at`、`history`。長期統計にも投入します |
| <code>sensor.<wbr>piyolog_<wbr>chest_<wbr>circumference</code> | 胸囲 | `Chest` | cm | `measured_at`、`history`。長期統計にも投入します |
| <code>sensor.<wbr>piyolog_<wbr>foot_<wbr>size</code> | 足サイズ | `Foot` | cm | 状態は `value.left` を優先し、左が無い場合は `value.right`。属性 `measured_at` と、存在する側の `left` / `right`。`history` と長期統計の対象外です |

身体計測には別途「最後の体重」などの timestamp センサーは作りません。最新の計測日時は各センサーの `measured_at` 属性で確認します。

### 当日集計センサー（10個）

| entity_id | 表示名 | 元になるフィード値 | 算出方法 | 単位・属性 |
|---|---|---|---|---|
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>breast_<wbr>feeding_<wbr>count</code> | 今日の授乳回数 | 今日の `BreastFeeding` 件数 | 値の有無にかかわらず記録件数を数えます | 回 |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>breast_<wbr>feeding_<wbr>duration</code> | 今日の授乳時間 | `leftTime`、`rightTime` | 各記録の左右を秒で合計し、分へ換算して小数第1位まで表示 | 分 |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>breast_<wbr>feeding_<wbr>total</code> | 今日の母乳量 | <code>BreastFeeding.<wbr>value.<wbr>value</code> | 数値が入っている記録だけを合計します | ml。属性 `count_today` は全授乳回数、`measured_count` は量が記録された回数 |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>formula_<wbr>total</code> | 今日のミルク量 | `Formula.value.value` | 数値が入っている記録だけを合計します | ml。属性 `count_today` は量の有無を含むミルク記録数 |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>expressed_<wbr>breast_<wbr>milk_<wbr>total</code> | 今日の搾母乳量 | <code>ExpressedBreastMilk.<wbr>value.<wbr>value</code> | 数値が入っている記録だけを合計します | ml |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>pumping_<wbr>total</code> | 今日の搾乳量 | `Pumping.value.value` | 数値が入っている記録だけを合計します | ml |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>drink_<wbr>total</code> | 今日ののみもの量 | `Drink.value.value` | 数値が入っている記録だけを合計します | ml |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>pee_<wbr>count</code> | 今日のおしっこ回数 | 今日の `Pee` 件数 | 記録件数を数えます | 回 |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>poop_<wbr>count</code> | 今日のうんち回数 | 今日の `Poop` 件数 | 記録件数を数えます | 回 |
| <code>sensor.<wbr>piyolog_<wbr>today_<wbr>sleep_<wbr>total</code> | 今日の睡眠時間 | `Sleep` / `WakeUp` のペア | 睡眠区間と今日の重なりを合計し、分へ換算して小数第1位まで表示。進行中は現在時刻まで | 分 |

量センサーが `0 ml` の場合、「その種類の記録自体が無い」か「記録はあるが量が未入力」のどちらかです。母乳量は `measured_count`、ミルク量は `count_today` で区別できます。その他の量センサーでは、タイムラインや最終記録も合わせて確認してください。

### 状態・タイムライン・フィード状態（4個）

| entity_id | 表示名 | 状態 | 属性 |
|---|---|---|---|
| <code>binary_<wbr>sensor.<wbr>piyolog_<wbr>sleeping</code> | 睡眠中 | 最後に未終了の `Sleep` があれば ON、それ以外は OFF | `sleeping_since`: ONの場合は睡眠開始時刻、OFFの場合は `null` |
| <code>sensor.<wbr>piyolog_<wbr>timeline</code> | タイムライン | 全種類を通じた最新記録の `datetime` | `records`: 今日の記録を新しい順に最大50件。`records_today`: 属性に保持している件数。`generated_at`: フィード生成時刻 |
| <code>sensor.<wbr>piyolog_<wbr>recent_<wbr>events</code> | 直近の記録 | 全種類を通じた最新記録の `datetime` | `records`: 日付を問わず新しい順に最大100件。`count`: 属性に保持している件数。`total_records`: マージ後の全記録数。`generated_at`: フィード生成時刻 |
| <code>sensor.<wbr>piyolog_<wbr>last_<wbr>update</code> | フィード最終更新 | フィードの `generated_at`。2本構成では新しい方 | `record_count`: マージ後の全記録数 |

`sensor.piyolog_timeline` の `records` は当日の分だけですが、状態そのものは全期間の最新記録です。そのため、今日まだ記録が無くても、状態には前日以前の最新記録日時が入り、`records` は空になることがあります。

#### タイムライン項目の形式

`records` の各要素は次の形式です。

| キー | 内容 |
|---|---|
| `time` | `datetime` を Home Assistant の既定タイムゾーンへ変換したISO文字列 |
| `type` | フィードの `type` をそのまま保持 |
| `label` | `type` に対応する日本語ラベル。カスタム記録は「カスタム1」など |
| `summary` | フィード値から生成した短い要約。要約を作らない種類では空文字列 |
| `memo` | メモがある場合だけ含めます |

`summary` の生成規則は次のとおりです。

| 対象 | `summary` の形式 |
|---|---|
| `BreastFeeding` | 記録されている項目だけを並べます。例: `左5分 右4分 80ml`。左右は秒から分へ換算し四捨五入 |
| `Formula` / `ExpressedBreastMilk` / `Pumping` / `Drink` | `120ml`。量が無い場合は空文字列 |
| `Poop` | 量・かたさ・色を日本語化し、`・` で連結。例: `ふつう・やわらかめ・黄` |
| `Temperature` | `36.7℃` |
| `Weight` | `6.3kg` |
| `Height` / `Head` / `Chest` | `60cm` |
| `Foot` | 記録されている側だけを並べます。例: `左9cm 右9.2cm` |
| その他の種類 | 空文字列。時刻、`label`、`memo` で内容を表します |

## 長期統計の対応表

### 身体計測の統計

体重・身長・体温・頭囲・胸囲は、各センサー自身の統計として投入します。足サイズは対象外です。統計IDはセンサーのentity_idで、unique IDからエンティティレジストリで解決します。そのため、entity_idを変更した場合や、2人目以降で`_2`が付いたentity_idでも、正しい系列へ投入されます。下表の統計IDは1人目の既定のentity_idです。

| フィード `type` | 統計ID | 単位 | 投入方法 |
|---|---|---|---|
| `Weight` | <code>sensor.<wbr>piyolog_<wbr>weight</code> | kg | 過去日分を1時間ごとにまとめ、各時間の平均・最小・最大を投入 |
| `Height` | <code>sensor.<wbr>piyolog_<wbr>height</code> | cm | 同上 |
| `Temperature` | <code>sensor.<wbr>piyolog_<wbr>temperature</code> | °C | 同上 |
| `Head` | <code>sensor.<wbr>piyolog_<wbr>head_<wbr>circumference</code> | cm | 同上 |
| `Chest` | <code>sensor.<wbr>piyolog_<wbr>chest_<wbr>circumference</code> | cm | 同上 |

当日分は対象外です。当日分は Home Assistant のレコーダーが、稼働中のセンサー状態から通常どおり生成します。

### 日次合計の外部統計

日次合計は、外部統計 `piyolog:daily_*_{エントリID}` として投入します。末尾のエントリIDは、設定エントリIDを小文字化したもので、子どもごとに系列が分かれます。各日について、値が計算できた系列だけを作成し、値のない日を0で埋めることはありません。当日分も含み、フィード更新のたびにその時点までの値へ更新されます。

| 統計ID | 元になる記録・項目 | 内容 | 単位 |
|---|---|---|---|
| <code>piyolog:<wbr>daily_<wbr>breast_<wbr>feeding_<wbr>ml_<wbr>{エントリID}</code> | <code>BreastFeeding.<wbr>value.<wbr>value</code> | 量が記録された母乳の1日合計 | ml |
| <code>piyolog:<wbr>daily_<wbr>breast_<wbr>feeding_<wbr>count_<wbr>{エントリID}</code> | `BreastFeeding` | 1日の授乳回数 | なし（回数） |
| <code>piyolog:<wbr>daily_<wbr>breast_<wbr>feeding_<wbr>minutes_<wbr>{エントリID}</code> | `leftTime` + `rightTime` | 1日の授乳時間 | 分 |
| <code>piyolog:<wbr>daily_<wbr>formula_<wbr>ml_<wbr>{エントリID}</code> | `Formula.value.value` | 1日のミルク量 | ml |
| <code>piyolog:<wbr>daily_<wbr>expressed_<wbr>breast_<wbr>milk_<wbr>ml_<wbr>{エントリID}</code> | <code>ExpressedBreastMilk.<wbr>value.<wbr>value</code> | 1日の搾母乳量 | ml |
| <code>piyolog:<wbr>daily_<wbr>pumping_<wbr>ml_<wbr>{エントリID}</code> | `Pumping.value.value` | 1日の搾乳量 | ml |
| <code>piyolog:<wbr>daily_<wbr>drink_<wbr>ml_<wbr>{エントリID}</code> | `Drink.value.value` | 1日ののみもの量 | ml |
| <code>piyolog:<wbr>daily_<wbr>pee_<wbr>count_<wbr>{エントリID}</code> | `Pee` | 1日のおしっこ回数 | なし（回数） |
| <code>piyolog:<wbr>daily_<wbr>poop_<wbr>count_<wbr>{エントリID}</code> | `Poop` | 1日のうんち回数 | なし（回数） |
| <code>piyolog:<wbr>daily_<wbr>sleep_<wbr>minutes_<wbr>{エントリID}</code> | `Sleep` / `WakeUp` | 1日に属する睡眠時間。日をまたぐ場合は各日へ分割 | 分 |
