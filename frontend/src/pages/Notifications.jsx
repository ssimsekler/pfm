// Notifications (MUI): list + unread-only toggle + mark-read.
import { useCallback, useEffect, useState } from "react";
import {
  Box, Typography, Stack, FormControlLabel, Switch, Button, IconButton, Tooltip,
  Table, TableBody, TableCell, TableHead, TableRow, CircularProgress, Snackbar, Alert,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import DoneIcon from "@mui/icons-material/Done";
import { api } from "../api";

export default function Notifications() {
  const [rows, setRows] = useState([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.get("/v1/notifications", { unread_only: unreadOnly ? "true" : "", limit: 200 });
      setRows(Array.isArray(data) ? data : data.items || []);
    } catch (e) { setError(e.message); setRows([]); } finally { setLoading(false); }
  }, [unreadOnly]);

  useEffect(() => { load(); }, [load]);

  const markRead = async (uuid) => {
    setError(null); setMsg(null);
    try { await api.post(`/v1/notifications/${uuid}/read`); setMsg("Marked as read."); load(); }
    catch (e) { setError(e.message); }
  };

  const fmtDate = (v) => { if (!v) return ""; try { return new Date(v).toLocaleString(); } catch { return String(v); } };

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">Notifications</Typography>
        <Stack direction="row" spacing={2} alignItems="center">
          <FormControlLabel control={<Switch checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />} label="Unread only" />
          <Button startIcon={<RefreshIcon />} onClick={load}>Refresh</Button>
        </Stack>
      </Stack>

      {loading ? <CircularProgress /> : (
        <Table size="small">
          <TableHead>
            <TableRow><TableCell>Subject</TableCell><TableCell>Body</TableCell><TableCell>Created</TableCell><TableCell align="right">Action</TableCell></TableRow>
          </TableHead>
          <TableBody>
            {rows.map((n) => (
              <TableRow key={n.uuid} hover>
                <TableCell>{n.subject}</TableCell>
                <TableCell>{n.body}</TableCell>
                <TableCell>{fmtDate(n.created_at)}</TableCell>
                <TableCell align="right">
                  <Tooltip title="Mark read"><IconButton size="small" onClick={() => markRead(n.uuid)}><DoneIcon fontSize="small" /></IconButton></Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 ? <TableRow><TableCell colSpan={4}><Typography color="text.secondary">No notifications.</Typography></TableCell></TableRow> : null}
          </TableBody>
        </Table>
      )}

      <Typography variant="body2" sx={{ mt: 1 }}>{rows.length} notification(s)</Typography>

      <Snackbar open={Boolean(msg)} autoHideDuration={4000} onClose={() => setMsg(null)}>
        <Alert severity="success" onClose={() => setMsg(null)}>{msg}</Alert>
      </Snackbar>
      <Snackbar open={Boolean(error)} autoHideDuration={6000} onClose={() => setError(null)}>
        <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>
      </Snackbar>
    </Box>
  );
}