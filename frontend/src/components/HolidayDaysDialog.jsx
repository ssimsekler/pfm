// Holiday calendar day editor (A.1): manage explicit holiday dates plus the
// recurring weekend config + week-start on the calendar itself.
// Backend: GET/POST/DELETE /v1/holiday-calendars/{id}/days and PATCH the calendar.
import { useCallback, useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, TextField, Alert, Box, Typography, Divider,
  ToggleButton, ToggleButtonGroup, MenuItem,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import { api } from "../api";
import ConfirmDialog from "./ConfirmDialog";

const WEEKDAYS = [
  { v: 0, label: "Mon" }, { v: 1, label: "Tue" }, { v: 2, label: "Wed" },
  { v: 3, label: "Thu" }, { v: 4, label: "Fri" }, { v: 5, label: "Sat" }, { v: 6, label: "Sun" },
];

export default function HolidayDaysDialog({ calendar, onClose }) {
  const [days, setDays] = useState([]);
  const [draft, setDraft] = useState({ holiday_date: "", label: "" });
  const [weekend, setWeekend] = useState(calendar.weekend_days || []);
  const [weekStart, setWeekStart] = useState(
    calendar.week_start === null || calendar.week_start === undefined ? "" : calendar.week_start
  );
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [deleteId, setDeleteId] = useState(null);

  const load = useCallback(async () => {
    const rows = await api.get(`/v1/holiday-calendars/${calendar.uuid}/days`).catch(() => []);
    setDays(rows || []);
  }, [calendar.uuid]);

  useEffect(() => { load(); }, [load]);

  const addDay = async () => {
    if (!draft.holiday_date) { setError("Pick a date."); return; }
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.post(`/v1/holiday-calendars/${calendar.uuid}/days`, {
        holiday_date: draft.holiday_date,
        label: draft.label || null,
      });
      setDraft({ holiday_date: "", label: "" });
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doDelete = async () => {
    setBusy(true); setError(null);
    try {
      await api.del(`/v1/holiday-calendars/${calendar.uuid}/days/${deleteId}`);
      setDeleteId(null);
      await load();
    } catch (e) { setDeleteId(null); setError(e.message); } finally { setBusy(false); }
  };

  const saveConfig = async () => {
    setBusy(true); setError(null); setMsg(null);
    try {
      await api.patch(`/v1/holiday-calendars/${calendar.uuid}`, {
        weekend_days: weekend,
        week_start: weekStart === "" ? null : Number(weekStart),
      });
      setMsg("Weekend/week-start saved.");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Holiday calendar — {calendar.name}</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        {msg ? <Alert severity="success" sx={{ mb: 2 }}>{msg}</Alert> : null}

        <Typography variant="subtitle2" sx={{ mb: 1 }}>Recurring weekend</Typography>
        <ToggleButtonGroup
          size="small"
          value={weekend}
          onChange={(_e, val) => setWeekend(val)}
          aria-label="weekend days"
        >
          {WEEKDAYS.map((d) => (
            <ToggleButton key={d.v} value={d.v}>{d.label}</ToggleButton>
          ))}
        </ToggleButtonGroup>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ mt: 2 }}>
          <TextField label="Week starts on" size="small" select value={weekStart}
            onChange={(e) => setWeekStart(e.target.value)} sx={{ width: 180 }}>
            <MenuItem value=""><em>Default</em></MenuItem>
            {WEEKDAYS.map((d) => <MenuItem key={d.v} value={d.v}>{d.label}</MenuItem>)}
          </TextField>
          <Button variant="outlined" startIcon={<SaveIcon />} onClick={saveConfig} disabled={busy}>
            Save weekend/week-start
          </Button>
        </Stack>

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Explicit holidays</Typography>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell><TableCell>Label</TableCell><TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {days.map((d) => (
              <TableRow key={d.uuid} hover>
                <TableCell>{d.holiday_date}</TableCell>
                <TableCell>{d.label || ""}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" color="error" onClick={() => setDeleteId(d.uuid)}>
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
            {days.length === 0 ? (
              <TableRow><TableCell colSpan={3}><Typography color="text.secondary">No holidays yet.</Typography></TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>

        <Divider sx={{ my: 2 }} />
        <Stack direction="row" spacing={1.5} alignItems="center">
          <TextField label="Date" type="date" size="small" value={draft.holiday_date}
            InputLabelProps={{ shrink: true }}
            onChange={(e) => setDraft({ ...draft, holiday_date: e.target.value })} />
          <TextField label="Label" size="small" value={draft.label}
            onChange={(e) => setDraft({ ...draft, label: e.target.value })} sx={{ minWidth: 220 }} />
          <Button variant="contained" startIcon={<AddIcon />} onClick={addDay} disabled={busy}>Add</Button>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>

      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Delete holiday?"
        message="Remove this holiday date?"
        confirmText="Delete"
        confirmColor="error"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setDeleteId(null)}
      />
    </Dialog>
  );
}