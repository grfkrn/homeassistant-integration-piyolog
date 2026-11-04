/**
 * PiyoLog timeline card for Home Assistant.
 *
 * Shows one day of PiyoLog records (feed times and values as-is),
 * fetched from the integration via the `piyolog/get_records`
 * WebSocket command. Bundled with the piyolog integration; no build
 * step, plain ES module.
 */

const ICONS = {
  BreastFeeding: "🤱",
  Formula: "🍼",
  ExpressedBreastMilk: "🥛",
  Pumping: "🥛",
  Drink: "🥤",
  Solid: "🥣",
  Snack: "🍪",
  Meal: "🍚",
  Pee: "💦",
  Poop: "💩",
  Sleep: "😴",
  WakeUp: "🌅",
  Bath: "🛁",
  Medicine: "💊",
  Hospital: "🏥",
  Walking: "🚶",
  Vaccine: "💉",
  Temperature: "🌡️",
  Weight: "⚖️",
  Height: "📏",
  Head: "📏",
  Chest: "📏",
  Foot: "👣",
  Milestone: "⭐",
  Cough: "😷",
  Vomiting: "🤢",
  Rash: "🩹",
  Injury: "🩹",
  Memo: "📝",
  Other: "🔹",
};

const SUMMARY_LABELS = [
  ["breast_feeding_count", "🤱", (v) => `${v}回`],
  ["breast_feeding_ml", "母乳", (v) => `${Math.round(v)} ml`],
  ["breast_feeding_minutes", "授乳", (v) => formatMinutes(v)],
  ["formula_ml", "🍼", (v) => `${Math.round(v)} ml`],
  ["expressed_breast_milk_ml", "搾母乳", (v) => `${Math.round(v)} ml`],
  ["pumping_ml", "搾乳", (v) => `${Math.round(v)} ml`],
  ["drink_ml", "のみもの", (v) => `${Math.round(v)} ml`],
  ["sleep_minutes", "😴", (v) => formatMinutes(v)],
  ["pee_count", "💦", (v) => `${v}回`],
  ["poop_count", "💩", (v) => `${v}回`],
];

function formatMinutes(min) {
  const m = Math.round(min);
  const h = Math.floor(m / 60);
  const rest = m % 60;
  if (h === 0) return `${rest}分`;
  if (rest === 0) return `${h}時間`;
  return `${h}時間${rest}分`;
}

function esc(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

class PiyologCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._date = null; // YYYY-MM-DD, defaults to today (HA timezone)
    this._entries = null;
    this._summary = {};
    this._generatedAt = null;
    this._error = null;
    this._loading = false;
    this._lastAnchorState = null;
  }

  static getStubConfig(hass) {
    const ids = hass ? Object.keys(hass.states) : [];
    const exact = ids.find((id) => id === "sensor.piyolog_timeline");
    const any = ids.find((id) => id.includes("piyolog_timeline"));
    return { entity: exact || any || "" };
  }

  setConfig(config) {
    this._config = config || {};
    if (this._date === null) {
      this._date = this._today();
    }
    this._render();
    this._fetch();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._date === null) {
      this._date = this._today();
    }
    // Fetch on the anchor entity's first sighting as well as on later
    // changes (a feed refresh happened). setConfig usually runs before
    // hass exists, so the fetch it triggers is a no-op; skipping the
    // first sighting here left the card stuck on "loading" until the
    // user changed the date once.
    const state = this._config?.entity
      ? hass.states[this._config.entity]?.state
      : null;
    if (state != null && state !== this._lastAnchorState) {
      this._lastAnchorState = state;
      this._fetch();
    }
  }

  getCardSize() {
    return 6;
  }

  _today() {
    try {
      return new Intl.DateTimeFormat("en-CA", {
        timeZone: this._hass?.config?.time_zone,
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      }).format(new Date());
    } catch {
      const d = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    }
  }

  _shiftDate(days) {
    const [y, m, d] = this._date.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d + days));
    const pad = (n) => String(n).padStart(2, "0");
    return `${dt.getUTCFullYear()}-${pad(dt.getUTCMonth() + 1)}-${pad(
      dt.getUTCDate(),
    )}`;
  }

  _dateLabel() {
    const [y, m, d] = this._date.split("-").map(Number);
    const dt = new Date(Date.UTC(y, m - 1, d));
    try {
      return new Intl.DateTimeFormat("ja-JP", {
        timeZone: "UTC",
        month: "numeric",
        day: "numeric",
        weekday: "short",
      }).format(dt);
    } catch {
      return `${m}/${d}`;
    }
  }

  async _fetch() {
    if (!this._hass || !this._config?.entity || this._loading) return;
    this._loading = true;
    try {
      const result = await this._hass.callWS({
        type: "piyolog/get_records",
        entity_id: this._config.entity,
        date: this._date,
      });
      this._entries = result.entries || [];
      this._summary = result.summary || {};
      this._generatedAt = result.generated_at || null;
      this._error = null;
    } catch (err) {
      this._error = err?.message || String(err);
      this._entries = this._entries || [];
    } finally {
      this._loading = false;
      this._render();
    }
  }

  _navigate(days) {
    const next = this._shiftDate(days);
    if (next > this._today()) return;
    this._date = next;
    this._entries = null;
    this._render();
    this._fetch();
  }

  _render() {
    if (!this.shadowRoot) return;
    const root = this.shadowRoot;
    const isToday = this._date >= this._today();
    const title = this._config?.title;

    const summaryChips = SUMMARY_LABELS.filter(
      ([key]) => this._summary && key in this._summary,
    )
      .map(
        ([key, label, fmt]) =>
          `<span class="chip">${esc(label)} ${esc(fmt(this._summary[key]))}</span>`,
      )
      .join("");

    let body = "";
    if (!this._config?.entity) {
      body = `<div class="empty">表示するセンサー（sensor.piyolog_timeline）を設定してください</div>`;
    } else if (this._error) {
      body = `<div class="empty">読み込めませんでした（${esc(this._error)}）</div>`;
    } else if (this._entries === null) {
      body = `<div class="empty">読み込み中…</div>`;
    } else if (this._entries.length === 0) {
      body = `<div class="empty">この日の記録はありません</div>`;
    } else {
      body = this._entries
        .map((e) => {
          const time = (e.time || "").slice(11, 16);
          const icon = ICONS[e.type] || "🔹";
          const duration =
            e.type === "WakeUp" && e.duration_minutes
              ? `<span class="duration">💤 ${esc(formatMinutes(e.duration_minutes))}</span>`
              : "";
          const memo = e.memo
            ? `<div class="memo">${esc(e.memo)}</div>`
            : "";
          const summary = e.summary
            ? `<span class="detail">${esc(e.summary)}</span>`
            : "";
          return `<div class="row">
            <span class="icon">${icon}</span>
            <span class="time">${esc(time)}</span>
            <span class="main"><span class="label">${esc(e.label)}</span>${summary}${memo}</span>
            ${duration}
          </div>`;
        })
        .join("");
    }

    const updated = this._generatedAt
      ? `<div class="footer">フィード生成 ${esc(this._generatedAt.slice(5, 10))} ${esc(this._generatedAt.slice(11, 16))}時点</div>`
      : "";

    root.innerHTML = `
      <style>
        :host { display: block; }
        .nav { display: flex; align-items: center; gap: 4px; padding: 8px 8px 0; }
        .nav button {
          background: none; border: none; cursor: pointer; padding: 6px;
          color: var(--primary-text-color); font-size: 18px; line-height: 1;
        }
        .nav button:disabled { opacity: 0.3; cursor: default; }
        .nav .today-btn { font-size: 13px; border: 1px solid var(--divider-color, #444); border-radius: 999px; padding: 4px 10px; }
        .date-label { font-weight: 600; font-size: 15px; margin: 0 2px; }
        .date-input { margin-left: auto; background: none; border: 1px solid var(--divider-color, #444); border-radius: 8px; color: var(--primary-text-color); padding: 4px 6px; color-scheme: dark light; }
        .title { padding: 12px 16px 0; font-size: 16px; font-weight: 600; }
        .summary { display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 16px 2px; }
        .chip { background: var(--secondary-background-color, rgba(127,127,127,0.15)); border-radius: 999px; padding: 3px 10px; font-size: 12px; }
        .list { padding: 8px 16px 12px; }
        .row { display: flex; align-items: baseline; gap: 8px; padding: 5px 0; border-bottom: 1px solid var(--divider-color, rgba(127,127,127,0.2)); }
        .row:last-child { border-bottom: none; }
        .icon { font-size: 16px; width: 22px; text-align: center; flex: none; }
        .time { font-variant-numeric: tabular-nums; color: var(--secondary-text-color); font-size: 13px; width: 38px; flex: none; }
        .main { flex: 1; min-width: 0; }
        .label { font-weight: 600; margin-right: 6px; }
        .detail { color: var(--secondary-text-color); font-size: 13px; }
        .memo { color: var(--secondary-text-color); font-size: 12px; margin-top: 1px; }
        .duration { color: var(--secondary-text-color); font-size: 12px; flex: none; }
        .empty { padding: 18px 16px; color: var(--secondary-text-color); }
        .footer { padding: 0 16px 10px; color: var(--secondary-text-color); font-size: 11px; text-align: right; }
      </style>
      <ha-card>
        ${title ? `<div class="title">${esc(title)}</div>` : ""}
        <div class="nav">
          <button id="prev" title="前日">‹</button>
          <span class="date-label">${esc(this._dateLabel())}</span>
          <button id="next" title="翌日" ${isToday ? "disabled" : ""}>›</button>
          <button id="today" class="today-btn">今日</button>
          <input id="datepick" class="date-input" type="date" value="${esc(this._date)}" max="${esc(this._today())}">
        </div>
        ${summaryChips ? `<div class="summary">${summaryChips}</div>` : ""}
        <div class="list">${body}</div>
        ${updated}
      </ha-card>
    `;

    root.getElementById("prev")?.addEventListener("click", () => this._navigate(-1));
    root.getElementById("next")?.addEventListener("click", () => this._navigate(1));
    root.getElementById("today")?.addEventListener("click", () => {
      this._date = this._today();
      this._entries = null;
      this._render();
      this._fetch();
    });
    root.getElementById("datepick")?.addEventListener("change", (ev) => {
      if (ev.target.value) {
        this._date = ev.target.value;
        this._entries = null;
        this._render();
        this._fetch();
      }
    });
  }
}

if (!customElements.get("piyolog-card")) {
  customElements.define("piyolog-card", PiyologCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "piyolog-card")) {
  window.customCards.push({
    type: "piyolog-card",
    name: "PiyoLog Timeline",
    description: "One day of PiyoLog records (feed times and values as-is).",
    preview: false,
  });
}
