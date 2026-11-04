"""Constants for the PiyoLog integration."""

from __future__ import annotations

DOMAIN = "piyolog"

CONF_FEED_URL = "feed_url"
CONF_FEED_URL_LONG = "feed_url_long"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_NAME = "PiyoLog"
DEFAULT_SCAN_INTERVAL_MINUTES = 5
LONG_FEED_MIN_INTERVAL_MINUTES = 15

FEED_HOST = "feed.piyolog.com"
FEED_PERIODS = ("24h", "3d", "7d", "28d")
SUPPORTED_SCHEMA_VERSION = 1

# Record types defined by the data feed specification (schema v1).
TYPE_BREAST_FEEDING = "BreastFeeding"
TYPE_FORMULA = "Formula"
TYPE_EXPRESSED_BREAST_MILK = "ExpressedBreastMilk"
TYPE_PUMPING = "Pumping"
TYPE_SLEEP = "Sleep"
TYPE_WAKE_UP = "WakeUp"
TYPE_PEE = "Pee"
TYPE_POOP = "Poop"
TYPE_TEMPERATURE = "Temperature"
TYPE_HEIGHT = "Height"
TYPE_WEIGHT = "Weight"
TYPE_HEAD = "Head"
TYPE_CHEST = "Chest"
TYPE_FOOT = "Foot"
TYPE_SOLID = "Solid"
TYPE_SNACK = "Snack"
TYPE_MEAL = "Meal"
TYPE_DRINK = "Drink"
TYPE_COUGH = "Cough"
TYPE_VOMITING = "Vomiting"
TYPE_RASH = "Rash"
TYPE_INJURY = "Injury"
TYPE_BATH = "Bath"
TYPE_MEDICINE = "Medicine"
TYPE_HOSPITAL = "Hospital"
TYPE_WALKING = "Walking"
TYPE_VACCINE = "Vaccine"
TYPE_MILESTONE = "Milestone"
TYPE_MEMO = "Memo"
TYPE_OTHER = "Other"

CUSTOM_TYPE_PREFIX = "Custom"

# Japanese labels for record types (used in timeline entries).
TYPE_LABELS_JA = {
    TYPE_BREAST_FEEDING: "母乳",
    TYPE_FORMULA: "ミルク",
    TYPE_EXPRESSED_BREAST_MILK: "搾母乳",
    TYPE_PUMPING: "搾乳",
    TYPE_SLEEP: "寝る",
    TYPE_WAKE_UP: "起きる",
    TYPE_PEE: "おしっこ",
    TYPE_POOP: "うんち",
    TYPE_TEMPERATURE: "体温",
    TYPE_HEIGHT: "身長",
    TYPE_WEIGHT: "体重",
    TYPE_HEAD: "頭囲",
    TYPE_CHEST: "胸囲",
    TYPE_FOOT: "足サイズ",
    TYPE_SOLID: "離乳食",
    TYPE_SNACK: "おやつ",
    TYPE_MEAL: "ごはん",
    TYPE_DRINK: "のみもの",
    TYPE_COUGH: "せき",
    TYPE_VOMITING: "吐く",
    TYPE_RASH: "発疹",
    TYPE_INJURY: "けが",
    TYPE_BATH: "お風呂",
    TYPE_MEDICINE: "くすり",
    TYPE_HOSPITAL: "病院",
    TYPE_WALKING: "さんぽ",
    TYPE_VACCINE: "予防接種",
    TYPE_MILESTONE: "できた",
    TYPE_MEMO: "メモ",
    TYPE_OTHER: "その他",
}

POOP_AMOUNT_JA = {
    "minimum": "ちょっと",
    "small": "少なめ",
    "normal": "ふつう",
    "large": "多め",
}
POOP_HARDNESS_JA = {
    "diarrhea": "下痢",
    "soft": "やわらかめ",
    "normal": "ふつう",
    "hard": "かため",
}
POOP_COLOR_JA = {
    "white": "白",
    "yellow": "黄",
    "orange": "橙",
    "brown": "茶",
    "green": "緑",
    "red": "赤",
    "black": "黒",
}
