// Configuration page (MUI): code values + config entities (full CRUD).
// Holiday calendars get a row action to open the day/weekend editor (A.1).
import { useState } from "react";
import {
  Box, Typography, Stack, Tooltip, Card, CardHeader, CardContent, TextField, Button, Alert,
} from "@mui/material";
import EventIcon from "@mui/icons-material/Event";
import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import CodeValueManager from "../components/CodeValueManager";
import EntityManager from "../components/EntityManager";
import HolidayDaysDialog from "../components/HolidayDaysDialog";
import ComboField from "../components/ComboField";
import { ENTITIES } from "../entities";
import { api } from "../api";

const CONFIG_ENTITIES = [
  "llm-providers",
  "integration-endpoints",
  "categorization-rules",
  "currency-rates",
  "recurrence-profiles",
];

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
        subheader="Pull the latest rate(s) from the configured FX provider into a new validity period." />
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

export default function Configuration() {
  const [calendar, setCalendar] = useState(null);

  const holidayActions = [
    {
      icon: <EventIcon fontSize="small" />,
      tooltip: "Edit holidays & weekend",
      onClick: (row) => setCalendar(row),
    },
  ];

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Configuration</Typography>
      <Stack spacing={3}>
        <CodeValueManager />
        {CONFIG_ENTITIES.map((key) => (
          <div key={key}>
            <EntityManager entity={key} cfg={ENTITIES[key]} />
            {key === "currency-rates" ? <Box sx={{ mt: 2 }}><FxRefreshCard /></Box> : null}
          </div>
        ))}
        <EntityManager
          entity="holiday-calendars"
          cfg={ENTITIES["holiday-calendars"]}
          rowActions={holidayActions}
        />
      </Stack>

      {calendar ? (
        <HolidayDaysDialog calendar={calendar} onClose={() => setCalendar(null)} />
      ) : null}
    </Box>
  );
}
