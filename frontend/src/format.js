// Display-format utility (Session 742, Bug 21).
//
// Resolution order for each format:
//   1. the logged-in user's profile preference (/v1/profile)
//   2. the application default from app settings (/v1/app-config key `format.*`)
//   3. a hard-coded last-resort default:
//        date   -> yyyy-MM-dd
//        time   -> HH:mm
//        number -> 1,234.56  (grouping ",", decimal ".")
//
// The resolved formats are loaded once (cached) via `initFormats()` which the
// app calls at startup after auth. All components import the pure `formatDate`,
// `formatTime`, `formatDateTime`, `formatNumber` and `formatMoney` helpers.
import dayjs from "dayjs";
import { api } from "./api";

// Hard last-resort defaults.
const DEFAULTS = {
  date_format: "yyyy-MM-dd",
  time_format: "HH:mm",
  number_format: "1,234.56",
  // Item 8: no time locale set → the browser locale is used at runtime.
  time_locale: null,
  // Item 5: decimals for high-precision amounts (FX rates, investment
  // quantities, investment unit prices). Everything else uses 2 dp.
  amount_decimals: 6,
};

// Module-level resolved formats (mutated by initFormats).
let RESOLVED = { ...DEFAULTS };

// Map our tokenized date/time formats to dayjs format tokens.
// We support the tokens exposed in the profile/settings pickers.
function toDayjsFormat(fmt) {
  if (!fmt) return null;
  return fmt
    // year
    .replace(/yyyy/g, "YYYY")
    .replace(/yy/g, "YY")
    // month (MM/MMM already dayjs-compatible; keep uppercase M for month)
    // day: our token uses lowercase dd for day-of-month → dayjs DD
    .replace(/dd/g, "DD")
    .replace(/\bd\b/g, "D");
  // Time tokens HH, hh, mm, ss, a are already dayjs-compatible.
}

// Parse a number-format sample like "1,234.56" / "1.234,56" / "1 234.56" /
// "1234.56" into { group, decimal } separators.
function parseNumberFormat(sample) {
  const s = (sample || "").trim();
  // Defaults
  let group = ",";
  let decimal = ".";
  if (s === "1.234,56") { group = "."; decimal = ","; }
  else if (s === "1 234.56") { group = " "; decimal = "."; }
  else if (s === "1234.56") { group = ""; decimal = "."; }
  else if (s === "1,234.56") { group = ","; decimal = "."; }
  else {
    // Best-effort: detect from the sample. The last separator is the decimal.
    const lastComma = s.lastIndexOf(",");
    const lastDot = s.lastIndexOf(".");
    if (lastComma === -1 && lastDot === -1) { group = ""; decimal = "."; }
    else if (lastComma > lastDot) { decimal = ","; group = lastDot === -1 ? "" : "."; }
    else { decimal = "."; group = lastComma === -1 ? "" : ","; }
  }
  return { group, decimal };
}

// Initialize the resolved formats. Call once after auth. Safe to call again.
export async function initFormats() {
  const resolved = { ...DEFAULTS };
  let profile = null;
  let settings = {};
  try { profile = await api.get("/v1/profile"); } catch { /* ignore */ }
  try {
    const rows = await api.get("/v1/app-config");
    (rows || []).forEach((r) => { settings[r.key] = r.value; });
  } catch { /* ignore */ }

  const pick = (profKey, settingKey) => {
    const p = profile && profile[profKey];
    if (p !== undefined && p !== null && p !== "") return p;
    const s = settings[settingKey];
    if (s !== undefined && s !== null && s !== "") return s;
    return resolved[profKey];
  };

  resolved.date_format = pick("date_format", "format.date");
  resolved.time_format = pick("time_format", "format.time");
  resolved.number_format = pick("number_format", "format.number");
  // Item 8: time locale — profile → app-setting → null (browser default).
  resolved.time_locale = pick("time_locale", "format.time_locale") || null;
  // Item 5: high-precision decimals — profile → app-setting → default 6.
  const ad = pick("amount_decimals", "format.amount_decimals");
  const adNum = Number(ad);
  resolved.amount_decimals = Number.isFinite(adNum) && adNum >= 0 ? adNum : DEFAULTS.amount_decimals;
  RESOLVED = resolved;
  return RESOLVED;
}

export function getFormats() {
  return { ...RESOLVED };
}

// The resolved date format as a dayjs token string (for <DatePicker format=…>).
export function getDayjsDateFormat() {
  return toDayjsFormat(RESOLVED.date_format) || "YYYY-MM-DD";
}

// The resolved time locale, or the browser locale when none is set (Item 8).
export function getTimeLocale() {
  if (RESOLVED.time_locale) return RESOLVED.time_locale;
  try {
    return (navigator.languages && navigator.languages[0]) || navigator.language || "en";
  } catch {
    return "en";
  }
}

// --- Public formatters ------------------------------------------------------

export function formatDate(value) {
  if (value === null || value === undefined || value === "") return "";
  const d = dayjs(value);
  if (!d.isValid()) return String(value);
  return d.format(toDayjsFormat(RESOLVED.date_format) || "YYYY-MM-DD");
}

export function formatTime(value) {
  if (value === null || value === undefined || value === "") return "";
  const d = dayjs(value);
  if (!d.isValid()) return String(value);
  return d.format(toDayjsFormat(RESOLVED.time_format) || "HH:mm");
}

export function formatDateTime(value) {
  if (value === null || value === undefined || value === "") return "";
  const d = dayjs(value);
  if (!d.isValid()) return String(value);
  const df = toDayjsFormat(RESOLVED.date_format) || "YYYY-MM-DD";
  const tf = toDayjsFormat(RESOLVED.time_format) || "HH:mm";
  return d.format(`${df} ${tf}`);
}

// Format a number with the resolved grouping/decimal separators.
// `decimals` (default null) — when null, keep the number's natural precision
// (up to 6 places, trailing zeros trimmed). For money use decimals=2.
export function formatNumber(value, decimals = null) {
  if (value === null || value === undefined || value === "") return "";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  const { group, decimal } = parseNumberFormat(RESOLVED.number_format);

  let fixed;
  if (decimals === null) {
    // Natural precision, trimmed.
    fixed = String(Math.round(num * 1e6) / 1e6);
    if (fixed.includes(".")) fixed = fixed.replace(/0+$/, "").replace(/\.$/, "");
  } else {
    fixed = num.toFixed(decimals);
  }

  const negative = fixed.startsWith("-");
  if (negative) fixed = fixed.slice(1);
  const [intPart, fracPart] = fixed.split(".");
  const grouped = group
    ? intPart.replace(/\B(?=(\d{3})+(?!\d))/g, group)
    : intPart;
  const out = fracPart !== undefined ? grouped + decimal + fracPart : grouped;
  return (negative ? "-" : "") + out;
}

// Money: always 2 decimals, optionally prefixed with a currency code.
export function formatMoney(value, currency) {
  if (value === null || value === undefined || value === "") return "";
  const s = formatNumber(value, 2);
  return currency ? `${s} ${currency}` : s;
}

// High-precision amounts (Item 5): FX rates, investment quantities and
// investment unit prices only. Uses the resolved `amount_decimals` (profile →
// app-setting → default 6) with the standard grouping/decimal separators, and
// trims trailing zeros so short values stay readable. All *other* numbers must
// use formatNumber/formatMoney (2 dp).
export function formatHighPrecision(value) {
  if (value === null || value === undefined || value === "") return "";
  const num = Number(value);
  if (Number.isNaN(num)) return String(value);
  const decimals = RESOLVED.amount_decimals ?? DEFAULTS.amount_decimals;
  let out = formatNumber(num, decimals);
  // Trim trailing zeros in the fractional part (keep at least the integer).
  const { decimal } = parseNumberFormat(RESOLVED.number_format);
  if (out.includes(decimal)) {
    out = out.replace(new RegExp(`\\${decimal}?0+$`), "");
  }
  return out;
}
