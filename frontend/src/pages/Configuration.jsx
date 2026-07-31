// Configuration page (Session 815, Item 22): organized into MUI **tabs** so each
// configuration area has its own section, deep-linkable via the hash query
// (`#/configuration?tab=currency-rates`). Tabs: Code Lists, Currency Rates
// (+ FX refresh), Recurrence Profiles, Holiday Calendars, Integration Endpoints,
// LLM Providers, Categorization Rules, Credentials (Item 19).
import { useEffect, useMemo, useState } from "react";
import {
  Box, Typography, Stack, Tabs, Tab, Card, CardHeader, CardContent, TextField, Button, Alert,
} from "@mui/material";
import EventIcon from "@mui/icons-material/Event";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import { useLocation, useNavigate } from "react-router-dom";
import CodeValueManager from "../components/CodeValueManager";
import CredentialsManager from "../components/CredentialsManager";
import EntityManager from "../components/EntityManager";
import HolidayDaysDialog from "../components/HolidayDaysDialog";
import ComboField from "../components/ComboField";
import { ENTITIES } from "../entities";
import { api } from "../api";

const CCY_FIELD = { type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" };

// Bug 20: pull a rate from the configured FX source into a validity period.
function FxRefreshCard() {
  const [base, setBase] = useState("");
  const [quotes, setQuotes] = useState("");
  const [msg, setMsg] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    if (!base || !quotes.trim()) { setError("Pick a base currency and at least one quote."); return; }
    setBusy(true); setError(null); setMsg(null);
    const list = quotes.split(",").map((q) => q.trim().toUpperCase()).filter(Boolean);
    const done = [];
    try {
      for (const q of list) {
        // eslint-disable-next-line no-await-in-loop
        await api.post("/v1/fx/refresh", { base_ccy: base, quote_ccy: q });
        done.push(`${base}/${q}`);
      }
      setMsg(`Refreshed: ${done.join(", ")}.`);
    } catch (e) {
      setError(`${e.message}${done.length ? ` (done: ${done.join(", ")})` : ""}`);
    } finally { setBusy(false); }
  };

  return (
    <Card>
      <CardHeader title="Currency Rates — Refresh from source"
        subheader="Pull the latest rate(s) from the configured FX provider into a new validity period. Supports any base currency (e.g. AED)." />
      <CardContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexWrap: "wrap" }}>
          <Box sx={{ minWidth: 160 }}>
            <ComboField field={CCY_FIELD} value={base} onChange={setBase} label="Base currency" />
          </Box>
          <TextField label="Quote currencies (comma-separated)" size="small" value={quotes}
            onChange={(e) => setQuotes(e.target.value)} placeholder="USD, EUR, GBP" sx={{ minWidth: 260 }} />
          <Button variant="contained" startIcon={<CloudDownloadIcon />} onClick={refresh} disabled={busy}>
            {busy ? "Refreshing…" : "Refresh from source"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}

// Tab definitions. `key` maps to the ?tab= value for deep-linking.
const TABS = [
  { key: "code-lists", label: "Code Lists" },
  { key: "currency-rates", label: "Currency Rates" },
  { key: "recurrence-profiles", label: "Recurrence Profiles" },
  { key: "holiday-calendars", label: "Holiday Calendars" },
  { key: "integration-endpoints", label: "Integrations" },
  { key: "llm-providers", label: "LLM Providers" },
  { key: "categorization-rules", label: "Categorization Rules" },
  { key: "credentials", label: "Credentials" },
];

export default function Configuration() {
  const location = useLocation();
  const navigate = useNavigate();
  const [calendar, setCalendar] = useState(null);

  // Read the active tab from the hash query (?tab=…), default to the first.
  const initialTab = useMemo(() => {
    try {
      const q = new URLSearchParams(location.search || (location.hash.split("?")[1] || ""));
      const t = q.get("tab");
      return TABS.findIndex((x) => x.key === t);
    } catch { return -1; }
  }, [location.search, location.hash]);
  const [tab, setTab] = useState(initialTab >= 0 ? initialTab : 0);

  useEffect(() => { if (initialTab >= 0 && initialTab !== tab) setTab(initialTab); }, [initialTab]); // eslint-disable-line

  const onTab = (_e, v) => {
    setTab(v);
    navigate(`/configuration?tab=${TABS[v].key}`, { replace: true });
  };

  const holidayActions = [
    { icon: <EventIcon fontSize="small" />, tooltip: "Edit holidays & weekend", onClick: (row) => setCalendar(row) },
  ];

  const active = TABS[tab]?.key;

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Configuration</Typography>
      <Tabs value={tab} onChange={onTab} variant="scrollable" scrollButtons="auto" sx={{ mb: 2 }}>
        {TABS.map((t) => <Tab key={t.key} label={t.label} />)}
      </Tabs>

      {active === "code-lists" ? <CodeValueManager /> : null}

      {active === "currency-rates" ? (
        <Stack spacing={2}>
          <EntityManager entity="currency-rates" cfg={ENTITIES["currency-rates"]} />
          <FxRefreshCard />
        </Stack>
      ) : null}

      {active === "recurrence-profiles" ? (
        <EntityManager entity="recurrence-profiles" cfg={ENTITIES["recurrence-profiles"]} />
      ) : null}

      {active === "holiday-calendars" ? (
        <EntityManager entity="holiday-calendars" cfg={ENTITIES["holiday-calendars"]} rowActions={holidayActions} />
      ) : null}

      {active === "integration-endpoints" ? (
        <EntityManager entity="integration-endpoints" cfg={ENTITIES["integration-endpoints"]} />
      ) : null}

      {active === "llm-providers" ? (
        <EntityManager entity="llm-providers" cfg={ENTITIES["llm-providers"]} />
      ) : null}

      {active === "categorization-rules" ? (
        <EntityManager entity="categorization-rules" cfg={ENTITIES["categorization-rules"]} />
      ) : null}

      {active === "credentials" ? <CredentialsManager /> : null}

      {calendar ? (
        <HolidayDaysDialog calendar={calendar} onClose={() => setCalendar(null)} />
      ) : null}
    </Box>
  );
}