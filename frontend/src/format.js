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
    if (p) return p;
    const s = settings[settingKey];
    if (s) return s;
    return resolved[profKey];
  };

  resolved.date_format = pick("date_format", "format.date");
  resolved.time_format = pick("time_format", "format.time");
  resolved.number_format = pick("number_format", "format.number");
  RESOLVED = resolved;
  return RESOLVED;
}

export function getFormats() {
  return { ...RESOLVED };
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