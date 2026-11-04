/**
 * PiyoLog elapsed-time gauge card for Home Assistant.
 *
 * Shows how long it has been since the latest record of a group of
 * PiyoLog record types, as a semicircular gauge whose color changes
 * at user-configured thresholds:
 *
 * - mode "diaper":  latest of Pee / Poop
 * - mode "feeding": latest of ExpressedBreastMilk / BreastFeeding /
 *   Formula
 *
 * The card reads the integration's last-event timestamp sensors from
 * `hass.states`; it needs no extra backend API. Thresholds and the
 * gauge maximum are card config (YAML or the visual editor):
 *
 *   type: custom:piyolog-elapsed-card
 *   mode: diaper            # or feeding
 *   entity: sensor.piyolog_timeline   # anchor (optional)
 *   yellow_after_hours: 6   # green -> yellow
 *   red_after_hours: 12     # yellow -> red
 *   max_hours: 24           # gauge full scale
 *
 * Plain ES module, no build step (same style as piyolog-card.js).
 */

const MODE_DEFS = {
  diaper: {
    title: "うんち経過時間",
    yellow: 6,
    red: 12,
    max: 24,
    sources: [
      { key: "last_poop", label: "うんち" },
      { key: "last_pee", label: "おしっこ" },
    ],
  },
  feeding: {
    title: "ミルク経過時間",
    yellow: 3,
    red: 3.5,
    max: 4,
    sources: [
      { key: "last_expressed_breast_milk", label: "搾母乳" },
      { key: "last_breast_feeding", label: "母乳" },
      { key: "last_formula", label: "ミルク" },
    ],
  },
};

const MODE_ALIASES = {
  diaper: "diaper",
  pee: "diaper",
  poop: "diaper",
  "おむつ": "diaper",
  feeding: "feeding",
  milk: "feeding",
  "授乳": "feeding",
  "ミルク": "feeding",
};

const SOURCE_LABELS = Object.fromEntries(
  Object.values(MODE_DEFS).flatMap((def) =>
    def.sources.map((s) => [s.key, s.label]),
  ),
);

const COLORS = {
  green: "#66bb6a",
  yellow: "#fdd835",
  red: "#ef5350",
  none: "#9e9e9e",
};

function esc(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function normalizeMode(raw) {
  if (typeof raw !== "string") return "diaper";
  return MODE_ALIASES[raw.trim().toLowerCase()] || "diaper";
}

function finiteNumber(value, fallback) {
  const num = typeof value === "number" ? value : Number(value);
  return Number.isFinite(num) ? num : fallback;
}

/** Point on the gauge semicircle for fraction f (0 = left, 1 = right). */
function gaugePoint(cx, cy, r, f) {
  const theta = Math.PI * (1 - f);
  return [cx + r * Math.cos(theta), cy - r * Math.sin(theta)];
}

/** SVG arc path along the gauge semicircle from fraction a to b. */
function gaugeArc(cx, cy, r, a, b) {
  const span = b - a;
  if (span <= 0) return "";
  const [x1, y1] = gaugePoint(cx, cy, r, a);
  const [x2, y2] = gaugePoint(cx, cy, r, Math.min(b, a + 0.999));
  const large = span > 0.5 ? 1 : 0;
  return `M ${x1.toFixed(2)} ${y1.toFixed(2)} A ${r} ${r} 0 ${large} 1 ${x2.toFixed(2)} ${y2.toFixed(2)}`;
}

class PiyologElapsedCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._timer = null;
  }

  static getConfigElement() {
    return document.createElement("piyolog-elapsed-card-editor");
  }

  static getStubConfig(hass) {
    const ids = hass ? Object.keys(hass.states) : [];
    const exact = ids.find((id) => id === "sensor.piyolog_timeline");
    const any = ids.find((id) => id.includes("piyolog_timeline"));
    return { mode: "diaper", entity: exact || any || "sensor.piyolog_timeline" };
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    if (this._timer === null) {
      // Elapsed time advances even when no state changes.
      this._timer = setInterval(() => this._render(), 30000);
    }
  }

  disconnectedCallback() {
    if (this._timer !== null) {
      clearInterval(this._timer);
      this._timer = null;
    }
  }

  getCardSize() {
    return 4;
  }

  _mode() {
    return normalizeMode(this._config?.mode);
  }

  _thresholds() {
    const def = MODE_DEFS[this._mode()];
    const yellow = finiteNumber(this._config?.yellow_after_hours, def.yellow);
    const red = finiteNumber(this._config?.red_after_hours, def.red);
    const max = finiteNumber(this._config?.max_hours, def.max);
    if (yellow < 0 || red <= yellow || max <= red) return null;
    return { yellow, red, max };
  }

  /** Entity ids of the last-event sensors this gauge reads. */
  _sourceEntityIds() {
    const def = MODE_DEFS[this._mode()];
    if (Array.isArray(this._config?.entities)) {
      return this._config.entities.filter(
        (id) => typeof id === "string" && id.includes("."),
      );
    }
    const anchor =
      this._config?.entity ||
      this._config?.anchor_entity ||
      "sensor.piyolog_timeline";
    const match = String(anchor).match(/^(sensor\.piyolog_)(.*?)(_\d+)?$/);
    const suffix = match?.[3] || "";
    return def.sources.map((s) => `sensor.piyolog_${s.key}${suffix}`);
  }

  _labelFor(entityId) {
    const key = Object.keys(SOURCE_LABELS).find((k) => entityId.includes(k));
    return key ? SOURCE_LABELS[key] : "記録";
  }

  /** Latest valid timestamp among the source entities, or null. */
  _latest() {
    if (!this._hass) return null;
    let latest = null;
    for (const entityId of this._sourceEntityIds()) {
      const stateObj = this._hass.states[entityId];
      if (!stateObj) continue;
      const raw = stateObj.state;
      if (!raw || raw === "unknown" || raw === "unavailable") continue;
      const time = Date.parse(raw);
      if (!Number.isFinite(time)) continue;
      if (latest === null || time > latest.time) {
        latest = { entityId, time, label: this._labelFor(entityId) };
      }
    }
    return latest;
  }

  _formatTime(timeMs) {
    try {
      return new Intl.DateTimeFormat("ja-JP", {
        timeZone: this._hass?.config?.time_zone,
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }).format(new Date(timeMs));
    } catch {
      const d = new Date(timeMs);
      const pad = (n) => String(n).padStart(2, "0");
      return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
    }
  }

  _render() {
    if (!this.shadowRoot || !this._config) return;
    const mode = this._mode();
    const def = MODE_DEFS[mode];
    const title = this._config.title || this._config.name || def.title;
    const thresholds = this._thresholds();

    let body = "";
    if (!thresholds) {
      body = `<div class="message">しきい値の設定を確認してください。<br>黄色 ＜ 赤 ＜ 最大 の順にしてください。</div>`;
    } else if (!this._hass) {
      body = `<div class="message">読み込み中…</div>`;
    } else {
      const latest = this._latest();
      if (!latest) {
        body = `<div class="message">記録がありません</div>`;
      } else {
        const elapsedHours = Math.max(0, (Date.now() - latest.time) / 3600000);
        const colorName =
          elapsedHours >= thresholds.red
            ? "red"
            : elapsedHours >= thresholds.yellow
              ? "yellow"
              : "green";
        const color = COLORS[colorName];
        const frac = Math.min(elapsedHours / thresholds.max, 1);
        const yFrac = Math.min(thresholds.yellow / thresholds.max, 1);
        const rFrac = Math.min(thresholds.red / thresholds.max, 1);
        const cx = 110;
        const cy = 112;
        body = `
          <div class="gauge">
            <svg viewBox="0 0 220 124" role="img" aria-label="${esc(title)} ${elapsedHours.toFixed(2)} hour">
              <path d="${gaugeArc(cx, cy, 80, 0, 1)}" fill="none" stroke="var(--piyolog-track, rgba(127,127,127,0.25))" stroke-width="19" stroke-linecap="round"/>
              <path d="${gaugeArc(cx, cy, 96, 0, yFrac)}" fill="none" stroke="${COLORS.green}" stroke-width="4" stroke-linecap="round"/>
              <path d="${gaugeArc(cx, cy, 96, yFrac, rFrac)}" fill="none" stroke="${COLORS.yellow}" stroke-width="4" stroke-linecap="round"/>
              <path d="${gaugeArc(cx, cy, 96, rFrac, 1)}" fill="none" stroke="${COLORS.red}" stroke-width="4" stroke-linecap="round"/>
              <path d="${gaugeArc(cx, cy, 80, 0, Math.max(frac, 0.004))}" fill="none" stroke="${color}" stroke-width="19" stroke-linecap="round"/>
            </svg>
            <div class="value" style="color: ${color}">${elapsedHours.toFixed(2)} <span class="unit">hour</span></div>
          </div>
          <div class="detail">最後: ${esc(latest.label)} ${esc(this._formatTime(latest.time))}</div>`;
      }
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .title { padding: 14px 16px 0; font-size: 17px; font-weight: 600; color: var(--primary-text-color); }
        .gauge { position: relative; padding: 4px 10px 0; }
        .gauge svg { display: block; width: 100%; height: auto; }
        .value {
          position: absolute; left: 50%; bottom: 0; transform: translateX(-50%);
          font-size: 30px; font-weight: 600; font-variant-numeric: tabular-nums;
          white-space: nowrap; line-height: 1.1;
        }
        .value .unit { font-size: 19px; font-weight: 500; }
        .detail { text-align: center; color: var(--secondary-text-color); font-size: 12px; padding: 2px 8px 12px; }
        .message { padding: 30px 16px 36px; text-align: center; color: var(--secondary-text-color); line-height: 1.6; }
      </style>
      <ha-card>
        <div class="title">${esc(title)}</div>
        ${body}
      </ha-card>`;
  }
}

class PiyologElapsedCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
  }

  setConfig(config) {
    this._config = config || {};
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  _render() {
    if (!this.shadowRoot) return;
    const cfg = this._config || {};
    const mode = normalizeMode(cfg.mode);
    const def = MODE_DEFS[mode];
    const val = (key) => (cfg[key] === undefined || cfg[key] === null ? "" : cfg[key]);
    this.shadowRoot.innerHTML = `
      <style>
        .row { display: block; margin: 0 0 12px; }
        .row span { display: block; font-size: 13px; margin-bottom: 4px; color: var(--primary-text-color); }
        input, select {
          width: 100%; box-sizing: border-box; padding: 8px;
          background: var(--card-background-color, transparent);
          color: var(--primary-text-color);
          border: 1px solid var(--divider-color, #888); border-radius: 6px;
        }
      </style>
      <label class="row"><span>種類</span>
        <select data-field="mode">
          <option value="diaper" ${mode === "diaper" ? "selected" : ""}>うんち経過時間（うんち／おしっこ）</option>
          <option value="feeding" ${mode === "feeding" ? "selected" : ""}>ミルク経過時間（搾母乳／母乳／ミルク）</option>
        </select>
      </label>
      <label class="row"><span>タイトル（空欄で既定）</span>
        <input data-field="title" type="text" value="${esc(val("title"))}" placeholder="${esc(def.title)}">
      </label>
      <label class="row"><span>対象センサー（アンカー）</span>
        <input data-field="entity" type="text" value="${esc(val("entity"))}" placeholder="sensor.piyolog_timeline">
      </label>
      <label class="row"><span>黄色に切り替わる時間 [hour]（既定 ${def.yellow}）</span>
        <input data-field="yellow_after_hours" type="number" min="0" step="0.25" value="${esc(val("yellow_after_hours"))}" placeholder="${def.yellow}">
      </label>
      <label class="row"><span>赤に切り替わる時間 [hour]（既定 ${def.red}）</span>
        <input data-field="red_after_hours" type="number" min="0" step="0.25" value="${esc(val("red_after_hours"))}" placeholder="${def.red}">
      </label>
      <label class="row"><span>ゲージの最大時間 [hour]（既定 ${def.max}）</span>
        <input data-field="max_hours" type="number" min="0" step="0.5" value="${esc(val("max_hours"))}" placeholder="${def.max}">
      </label>`;
    this.shadowRoot.querySelectorAll("[data-field]").forEach((el) => {
      el.addEventListener("change", (ev) => this._changed(ev));
    });
  }

  _changed(ev) {
    const field = ev.target.dataset.field;
    const raw = ev.target.value;
    const next = { ...(this._config || {}) };
    if (
      field === "yellow_after_hours" ||
      field === "red_after_hours" ||
      field === "max_hours"
    ) {
      if (raw === "") delete next[field];
      else next[field] = Number(raw);
    } else if (field === "title" || field === "entity") {
      if (!raw.trim()) delete next[field];
      else next[field] = raw.trim();
    } else {
      next[field] = raw;
    }
    this._config = next;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: next },
        bubbles: true,
        composed: true,
      }),
    );
    if (field === "mode") this._render();
  }
}

if (!customElements.get("piyolog-elapsed-card")) {
  customElements.define("piyolog-elapsed-card", PiyologElapsedCard);
}
if (!customElements.get("piyolog-elapsed-card-editor")) {
  customElements.define("piyolog-elapsed-card-editor", PiyologElapsedCardEditor);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "piyolog-elapsed-card")) {
  window.customCards.push({
    type: "piyolog-elapsed-card",
    name: "PiyoLog Elapsed Gauge",
    description:
      "Elapsed time since the last diaper change or feeding, with configurable green/yellow/red thresholds.",
    preview: false,
  });
}
