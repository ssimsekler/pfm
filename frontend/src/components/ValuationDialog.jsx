// Investment valuation history dialog (#18): view/add valuations, refresh from a
// price source, and see the trend. Backend:
//   GET  /v1/investments/{id}/valuations
//   POST /v1/investments/{id}/valuations         { as_of_date, value }
//   POST /v1/investments/{id}/refresh-valuation
import { useCallback, useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, TextField, Alert, Typography, Box,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import RefreshIcon from "@mui/icons-material/Refresh";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RTooltip, ResponsiveContainer,
} from "recharts";
import { api } from "../api";

export default function ValuationDialog({ record, onClose }) {
  const [rows, setRows] = useState([]);
  const [draft, setDraft] = useState({ as_of_date: "", value: "" });
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const r = await api.get(`/v1/investments/${record.uuid}/valuations`).catch(() => []);
    setRows(r || []);
  }, [record.uuid]);

  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!draft.as_of_date || draft.value === "") { setError("Enter a date and value."); return; }
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post(`/v1/investments/${record.uuid}/valuations`, {
        as_of_date: draft.as_of_date,
        value: Number(draft.value),
      });
      setDraft({ as_of_date: "", value: "" });
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const refresh = async () => {
    setBusy(true); setError(null); setMsg(null);
    try {
      const res = await api.post(`/v1/investments/${record.uuid}/refresh-valuation`, {});
      setMsg(`Refreshed: ${res.value} as of ${res.as_of}.`);
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  // Chart oldest→newest; API returns newest first.
  const chart = [...rows]
    .map((r) => ({ date: r.as_of_date, value: Number(r.value) || 0 }))
    .sort((a, b) => (a.date < b.date ? -1 : 1));

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Valuation history — {record.name} ({record.symbol})</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}

        {chart.length > 0 ? (
          <Box sx={{ height: 260, mb: 2 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chart}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" /><YAxis /><RTooltip />
                <Line type="monotone" dataKey="value" stroke="#1e88e5" />
              </LineChart>
            </ResponsiveContainer>
          </Box>
        ) : <Typography color="text.secondary" sx={{ mb: 2 }}>No valuations yet.</Typography>}

        <Table size="small">
          <TableHead>
            <TableRow><TableCell>As of</TableCell><TableCell align="right">Value</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.uuid} hover>
                <TableCell>{r.as_of_date}</TableCell>
                <TableCell align="right">{r.value}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>

        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 2, flexWrap: "wrap" }}>
          <TextField label="As of" type="date" size="small" value={draft.as_of_date}
            InputLabelProps={{ shrink: true }}
            onChange={(e) => setDraft({ ...draft, as_of_date: e.target.value })} />
          <TextField label="Value" type="number" size="small" value={draft.value}
            onChange={(e) => setDraft({ ...draft, value: e.target.value })} sx={{ width: 140 }} />
          <Button variant="contained" startIcon={<AddIcon />} onClick={add} disabled={busy}>Add</Button>
          <Button startIcon={<RefreshIcon />} onClick={refresh} disabled={busy}>Refresh from source</Button>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}