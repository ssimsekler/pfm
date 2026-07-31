// Settings page (Phase 11 Batch 3, A.7): App Settings (app_config incl. LLM master
// switch), Entity Prefixes (id_sequence pad width), and My Profile (name/email +
// date/number/time display formats). Backed by /v1/app-config, /v1/id-sequences,
// and /v1/profile in backend admin.py.
import { useCallback, useEffect, useState } from "react";
import {
  Box, Typography, Stack, Card, CardContent, CardHeader, Table, TableBody, TableCell,
  TableHead, TableRow, TextField, Button, Alert, Switch, FormControlLabel, MenuItem,
  Divider, IconButton, Tooltip,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import AddIcon from "@mui/icons-material/Add";
import { Tabs, Tab } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { initFormats } from "../format";

// Internal/secret app_config keys never shown in the App Settings editor
// (Batch 10): the local-admin hashed credential and reset tokens are secrets,
// and rendering their JSON object value showed "[object Object]".
const HIDDEN_SETTING_KEYS = new Set(["auth.local_admin"]);
const isHiddenKey = (k) => HIDDEN_SETTING_KEYS.has(k) || String(k).startsWith("auth.reset.");

// ---------------------------------------------------------------------------
// App Settings (key/value) — with a friendly LLM master switch on top.
// ---------------------------------------------------------------------------
// Session 742, Bug 6: standardized on the seeded key `llm.master_enabled`
// (the old `llm.enabled` is migrated away by the seeder).
const LLM_MASTER_KEY = "llm.master_enabled";

function coerce(valueType, raw) {
  if (valueType === "boolean") return raw === true || raw === "true";
  if (valueType === "number") return raw === "" || raw === null ? null : Number(raw);
  return raw;
}

function AppSettings() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [drafts, setDrafts] = useState({}); // key -> value
  const [newKey, setNewKey] = useState({ key: "", value: "", value_type: "string", description: "" });

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.get("/v1/app-config");
      setRows(data || []);
      const d = {};
      (data || []).forEach((r) => { d[r.key] = r.value; });
      setDrafts(d);
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const llmRow = rows.find((r) => r.key === LLM_MASTER_KEY);
  const llmEnabled = llmRow ? (drafts[LLM_MASTER_KEY] === true || drafts[LLM_MASTER_KEY] === "true") : false;

  const saveKey = async (key, value, value_type, description) => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.put(`/v1/app-config/${encodeURIComponent(key)}`, {
        value: coerce(value_type, value),
        value_type,
        description,
      });
      setMsg(`Saved “${key}”.`);
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const toggleLlm = async (checked) => {
    setDrafts((d) => ({ ...d, [LLM_MASTER_KEY]: checked }));
    await saveKey(LLM_MASTER_KEY, checked, "boolean", "Master switch for LLM features");
  };

  const addKey = async () => {
    if (!newKey.key) { setError("Enter a key."); return; }
    await saveKey(newKey.key, newKey.value, newKey.value_type, newKey.description);
    setNewKey({ key: "", value: "", value_type: "string", description: "" });
  };

  return (
    <Card>
      <CardHeader title="App Settings" subheader="Global configuration (app_config). Includes the LLM master switch." />
      <CardContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}

        {/* Item 16: the duplicate top "LLM features" switch was removed — the
            `llm.master_enabled` row below (same input method as other settings)
            is the single control. */}
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Key</TableCell><TableCell>Type</TableCell>
              <TableCell>Value</TableCell><TableCell>Description</TableCell><TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.filter((r) => !isHiddenKey(r.key)).map((r) => (
              <TableRow key={r.key} hover>
                <TableCell><code>{r.key}</code></TableCell>
                <TableCell>{r.value_type}</TableCell>
                <TableCell>
                  {r.value_type === "boolean" ? (
                    <Switch
                      size="small"
                      checked={drafts[r.key] === true || drafts[r.key] === "true"}
                      onChange={(e) => setDrafts((d) => ({ ...d, [r.key]: e.target.checked }))}
                    />
                  ) : r.value_type === "json" || (drafts[r.key] !== null && typeof drafts[r.key] === "object") ? (
                    // Safe render for object/JSON values (never "[object Object]").
                    <Typography variant="caption" component="pre"
                      sx={{ m: 0, whiteSpace: "pre-wrap", fontFamily: "monospace" }}>
                      {(() => { try { return JSON.stringify(drafts[r.key]); } catch { return String(drafts[r.key]); } })()}
                    </Typography>
                  ) : (
                    <TextField
                      size="small"
                      value={drafts[r.key] ?? ""}
                      type={r.value_type === "number" ? "number" : "text"}
                      onChange={(e) => setDrafts((d) => ({ ...d, [r.key]: e.target.value }))}
                    />
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="caption" color="text.secondary">{r.description || ""}</Typography>
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="Save">
                    <span>
                      <IconButton size="small" disabled={busy}
                        onClick={() => saveKey(r.key, drafts[r.key], r.value_type, r.description)}>
                        <SaveIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={5}><Typography color="text.secondary">No settings yet.</Typography></TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Add / override a setting</Typography>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexWrap: "wrap" }}>
          <TextField label="Key" size="small" value={newKey.key}
            onChange={(e) => setNewKey({ ...newKey, key: e.target.value })} sx={{ width: 220 }} />
          <TextField label="Type" size="small" select value={newKey.value_type}
            onChange={(e) => setNewKey({ ...newKey, value_type: e.target.value })} sx={{ width: 130 }}>
            {["string", "number", "boolean", "json"].map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
          </TextField>
          <TextField label="Value" size="small" value={newKey.value}
            onChange={(e) => setNewKey({ ...newKey, value: e.target.value })} sx={{ width: 180 }} />
          <TextField label="Description" size="small" value={newKey.description}
            onChange={(e) => setNewKey({ ...newKey, description: e.target.value })} sx={{ minWidth: 220, flexGrow: 1 }} />
          <Button variant="contained" startIcon={<AddIcon />} onClick={addKey} disabled={busy}>Save</Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Email settings (Session 815, Item 20): SMTP now lives in the Credentials Store.
// This card only toggles `email.enabled` and picks the Email credential
// (`email.credentials_ref`); a "Send test email" action verifies it.
// ---------------------------------------------------------------------------
function EmailSettings() {
  const [enabled, setEnabled] = useState(false);
  const [ref, setRef] = useState("");
  const [creds, setCreds] = useState([]);
  const [testTo, setTestTo] = useState("");
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.get("/v1/app-config");
      const by = {};
      (data || []).forEach((r) => { by[r.key] = r.value; });
      setEnabled(by["email.enabled"] === true || by["email.enabled"] === "true");
      setRef(by["email.credentials_ref"] || "");
      // Only email-category credentials are eligible.
      const all = await api.get("/v1/credentials").catch(() => []);
      setCreds((all || []).filter((c) => c.category_key === "email"));
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const put = (key, value, value_type, description) =>
    api.put(`/v1/app-config/${encodeURIComponent(key)}`, { value, value_type, description });

  const saveAll = async () => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await put("email.enabled", enabled, "boolean", "Enable outgoing email");
      await put("email.credentials_ref", ref, "string", "Credentials Store entry (Email category) for SMTP settings");
      setMsg("Email settings saved.");
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const sendTest = async () => {
    setBusy(true); setError(null); setMsg(null);
    try {
      const r = await api.post("/v1/notifications/test-email", { to: testTo || null });
      setMsg(`Test email sent to ${r.to} via ${r.host} (${r.security}).`);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Card>
      <CardHeader title="Email" subheader="Enable outgoing email and pick an Email credential from the Credentials Store (Configuration → Credentials). SMTP host/port/security/username/password now live there — sensitive values are masked." />
      <CardContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}
        <FormControlLabel
          control={<Switch checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />}
          label={`Email ${enabled ? "enabled" : "disabled"}`}
        />
        <Stack spacing={2} sx={{ maxWidth: 520, mt: 1 }}>
          <TextField label="Email credential" size="small" select value={ref}
            onChange={(e) => setRef(e.target.value)}
            helperText={creds.length === 0 ? "No Email credentials yet — add one under Configuration → Credentials." : "From the Credentials Store (Email category)"}>
            <MenuItem value=""><em>None</em></MenuItem>
            {creds.map((c) => <MenuItem key={c.mnemonic_id} value={c.mnemonic_id}>{c.name} ({c.mnemonic_id})</MenuItem>)}
          </TextField>
          <Box>
            <Button variant="contained" startIcon={<SaveIcon />} onClick={saveAll} disabled={busy}>Save email settings</Button>
          </Box>
          <Divider />
          <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexWrap: "wrap" }}>
            <TextField label="Send test to (optional)" size="small" value={testTo}
              onChange={(e) => setTestTo(e.target.value)} sx={{ minWidth: 240 }}
              helperText="Blank = use the credential's default recipient" />
            <Button variant="outlined" onClick={sendTest} disabled={busy}>Send test email</Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Entity Prefixes (id_sequence) — edit pad width per entity type.
// ---------------------------------------------------------------------------
function EntityPrefixes() {
  const [rows, setRows] = useState([]);
  const [drafts, setDrafts] = useState({});
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await api.get("/v1/id-sequences");
      setRows(data || []);
      const d = {};
      (data || []).forEach((r) => { d[r.prefix] = r.pad_width; });
      setDrafts(d);
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (prefix) => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.patch(`/v1/id-sequences/${encodeURIComponent(prefix)}`, {
        pad_width: Number(drafts[prefix]),
      });
      setMsg(`Saved prefix “${prefix}”.`);
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const sample = (r) => `${r.prefix}${String((r.current_seq || 0) + 1).padStart(Number(drafts[r.prefix] || r.pad_width), "0")}`;

  return (
    <Card>
      <CardHeader title="Entity Prefixes" subheader="Mnemonic ID prefixes and zero-pad width per entity type (id_sequence)." />
      <CardContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Entity Type</TableCell><TableCell>Prefix</TableCell>
              <TableCell>Current Seq</TableCell><TableCell>Pad Width</TableCell>
              <TableCell>Next ID</TableCell><TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.prefix} hover>
                <TableCell>{r.entity_type}</TableCell>
                <TableCell><code>{r.prefix}</code></TableCell>
                <TableCell>{r.current_seq}</TableCell>
                <TableCell>
                  <TextField size="small" type="number" value={drafts[r.prefix] ?? r.pad_width}
                    inputProps={{ min: 1, max: 18 }} sx={{ width: 90 }}
                    onChange={(e) => setDrafts((d) => ({ ...d, [r.prefix]: e.target.value }))} />
                </TableCell>
                <TableCell><code>{sample(r)}</code></TableCell>
                <TableCell align="right">
                  <Tooltip title="Save">
                    <span>
                      <IconButton size="small" disabled={busy} onClick={() => save(r.prefix)}>
                        <SaveIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={6}><Typography color="text.secondary">No prefixes yet.</Typography></TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// My Profile — name/email + display-format preferences.
// ---------------------------------------------------------------------------
const DATE_FORMATS = ["yyyy-MM-dd", "dd/MM/yyyy", "MM/dd/yyyy", "dd MMM yyyy"];
const TIME_FORMATS = ["HH:mm", "hh:mm a", "HH:mm:ss"];
const NUMBER_FORMATS = ["1,234.56", "1.234,56", "1 234.56", "1234.56"];

function MyProfile() {
  const [form, setForm] = useState({
    name: "", email: "", base_currency: "",
    date_format: "", number_format: "", time_format: "",
    time_locale: "", amount_decimals: "",
  });
  const [username, setUsername] = useState("");
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const p = await api.get("/v1/profile");
      setUsername(p.username || "");
      setForm({
        name: p.name || "", email: p.email || "", base_currency: p.base_currency || "",
        date_format: p.date_format || "", number_format: p.number_format || "",
        time_format: p.time_format || "",
        time_locale: p.time_locale || "",
        amount_decimals: p.amount_decimals ?? "",
      });
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.put("/v1/profile", form);
      // Batch 10: re-resolve display formats so lists/inputs reflect the new
      // date/number/time + high-precision decimals immediately (no full reload).
      try { await initFormats(); } catch { /* ignore */ }
      setMsg("Profile saved. Reloading to apply display formats…");
      await load();
      // A hard reload guarantees every already-mounted DataGrid re-renders with
      // the new formats (they cache formatted cell values).
      setTimeout(() => window.location.reload(), 600);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  return (
    <Card>
      <CardHeader title="My Profile" subheader="Your identity and display-format preferences." />
      <CardContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}
        {username ? (
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 2 }}>
            Signed in as <code>{username}</code>
          </Typography>
        ) : null}
        <Stack spacing={2} sx={{ maxWidth: 520 }}>
          <TextField label="Name" size="small" value={form.name} onChange={set("name")} />
          <TextField label="Email" size="small" type="email" value={form.email} onChange={set("email")} />
          <TextField label="Base currency (ISO 4217)" size="small" value={form.base_currency}
            onChange={set("base_currency")} inputProps={{ maxLength: 3, style: { textTransform: "uppercase" } }} />
          <TextField label="Date format" size="small" select value={form.date_format} onChange={set("date_format")}>
            <MenuItem value=""><em>Default</em></MenuItem>
            {DATE_FORMATS.map((f) => <MenuItem key={f} value={f}>{f}</MenuItem>)}
          </TextField>
          <TextField label="Time format" size="small" select value={form.time_format} onChange={set("time_format")}>
            <MenuItem value=""><em>Default</em></MenuItem>
            {TIME_FORMATS.map((f) => <MenuItem key={f} value={f}>{f}</MenuItem>)}
          </TextField>
          <TextField label="Number format" size="small" select value={form.number_format} onChange={set("number_format")}>
            <MenuItem value=""><em>Default</em></MenuItem>
            {NUMBER_FORMATS.map((f) => <MenuItem key={f} value={f}>{f}</MenuItem>)}
          </TextField>
          {/* Item 8: time locale (blank → browser default). */}
          <TextField label="Time locale" size="small" value={form.time_locale} onChange={set("time_locale")}
            placeholder="e.g. en-GB" helperText="Blank → use the browser locale" />
          {/* Item 5: decimals for high-precision amounts (FX rates, investment qty/unit price). */}
          <TextField label="Decimals for high-precision amounts" size="small" type="number"
            value={form.amount_decimals} onChange={set("amount_decimals")}
            inputProps={{ min: 0, max: 12 }}
            helperText="Applies to exchange rates and investment quantities/unit prices only" />
          <Box>
            <Button variant="contained" startIcon={<SaveIcon />} onClick={save} disabled={busy}>Save profile</Button>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Page: stacks all three sections. `section` can pin one ("profile").
// ---------------------------------------------------------------------------
// Tabbed layout (Batch 10) — like the Configuration page; deep-linkable via ?tab=.
const SETTINGS_TABS = [
  { key: "app", label: "App Settings", render: () => <AppSettings /> },
  { key: "email", label: "Email", render: () => <EmailSettings /> },
  { key: "prefixes", label: "Entity Prefixes", render: () => <EntityPrefixes /> },
  { key: "profile", label: "My Profile", render: () => <MyProfile /> },
];

export default function Settings({ section }) {
  const location = useLocation();
  const navigate = useNavigate();

  // Pin to My Profile when routed via the avatar menu (#/profile).
  if (section === "profile") {
    return (
      <Box>
        <Typography variant="h5" sx={{ mb: 2 }}>My Profile</Typography>
        <MyProfile />
      </Box>
    );
  }

  // Resolve the active tab from ?tab=… (HashRouter puts the query after the hash).
  const params = new URLSearchParams(location.search || "");
  const tabParam = params.get("tab");
  const activeIdx = Math.max(0, SETTINGS_TABS.findIndex((t) => t.key === tabParam));

  const onTab = (_e, idx) => {
    const key = SETTINGS_TABS[idx].key;
    navigate(`/settings?tab=${key}`);
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Settings</Typography>
      <Tabs value={activeIdx} onChange={onTab} variant="scrollable" scrollButtons="auto"
        sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}>
        {SETTINGS_TABS.map((t) => <Tab key={t.key} label={t.label} />)}
      </Tabs>
      {SETTINGS_TABS[activeIdx].render()}
    </Box>
  );
}
