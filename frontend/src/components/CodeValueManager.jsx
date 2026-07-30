// Code-value administration (MUI, ADR #34): pick a code list, then create/edit/
// deactivate its values. System-locked lists are read-only. Writes are confirmed.
import { useCallback, useEffect, useState } from "react";
import {
  Card, CardHeader, CardContent, MenuItem, TextField, Button, Stack, Typography,
  Table, TableBody, TableCell, TableHead, TableRow, IconButton, Dialog, DialogTitle,
  DialogContent, DialogActions, FormControlLabel, Switch, Alert, Box,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { api } from "../api";
import ConfirmDialog from "./ConfirmDialog";

function emptyForm() {
  return { code: "", label: "", sort_order: 100, is_default: false, is_active: true };
}

export default function CodeValueManager() {
  const [lists, setLists] = useState([]);
  const [selected, setSelected] = useState(null);
  const [values, setValues] = useState([]);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [form, setForm] = useState(null);
  const [confirmSave, setConfirmSave] = useState(false);
  const [deleteRow, setDeleteRow] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const cls = await api.get("/v1/code-lists").catch(() => []);
      setLists(cls);
      if (cls.length) setSelected(cls[0]);
    })();
  }, []);

  const loadValues = useCallback(async (listKey) => {
    if (!listKey) return;
    const rows = await api.get(`/v1/code-lists/${listKey}/values`, { active_only: "" }).catch(() => []);
    setValues(rows);
  }, []);

  useEffect(() => {
    if (selected) loadValues(selected.list_key);
  }, [selected, loadValues]);

  const editable = selected && !(selected.is_system && !selected.allow_user_values);

  async function doSave() {
    setBusy(true); setError(null); setMsg(null);
    try {
      const key = selected.list_key;
      const payload = {
        code: form.code, label: form.label, sort_order: Number(form.sort_order) || 0,
        is_default: Boolean(form.is_default), is_active: Boolean(form.is_active),
      };
      if (form.record) await api.patch(`/v1/code-lists/${key}/values/${form.record.uuid}`, payload);
      else await api.post(`/v1/code-lists/${key}/values`, payload);
      setConfirmSave(false); setForm(null); setMsg("Saved.");
      loadValues(key);
    } catch (e) { setConfirmSave(false); setError(e.message); } finally { setBusy(false); }
  }

  async function doDelete() {
    if (!deleteRow) return;
    setBusy(true); setError(null);
    try {
      await api.del(`/v1/code-lists/${selected.list_key}/values/${deleteRow.uuid}`);
      setDeleteRow(null); setMsg("Deactivated."); loadValues(selected.list_key);
    } catch (e) { setDeleteRow(null); setError(e.message); } finally { setBusy(false); }
  }

  return (
    <Card>
      <CardHeader title="Code Lists (value help)" />
      <CardContent>
        {msg ? <Alert severity="success" sx={{ mb: 1 }} onClose={() => setMsg(null)}>{msg}</Alert> : null}
        {error ? <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>{error}</Alert> : null}

        <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
          <TextField
            select size="small" label="List" sx={{ minWidth: 240 }}
            value={selected?.list_key || ""}
            onChange={(e) => setSelected(lists.find((l) => l.list_key === e.target.value) || null)}
          >
            {lists.map((cl) => <MenuItem key={cl.list_key} value={cl.list_key}>{cl.list_key}</MenuItem>)}
          </TextField>
          {editable ? (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setForm({ ...emptyForm() })}>Create value</Button>
          ) : (
            <Typography variant="body2" color="text.secondary">System-managed (read-only)</Typography>
          )}
        </Stack>

        <Box sx={{ maxHeight: 360, overflow: "auto", border: 1, borderColor: "divider", borderRadius: 1 }}>
          <Table size="small" stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell>Code</TableCell><TableCell>Label</TableCell><TableCell>Order</TableCell>
                <TableCell>Default</TableCell><TableCell>Active</TableCell>{editable ? <TableCell /> : null}
              </TableRow>
            </TableHead>
            <TableBody>
              {values.map((v) => (
                <TableRow key={v.uuid} hover>
                  <TableCell>{v.code}</TableCell>
                  <TableCell>{v.label}</TableCell>
                  <TableCell>{v.sort_order}</TableCell>
                  <TableCell>{v.is_default ? "✓" : ""}</TableCell>
                  <TableCell>{v.is_active ? "✓" : ""}</TableCell>
                  {editable ? (
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => setForm({ record: v, code: v.code, label: v.label, sort_order: v.sort_order, is_default: v.is_default, is_active: v.is_active })}><EditIcon fontSize="small" /></IconButton>
                      <IconButton size="small" color="error" onClick={() => { setError(null); setDeleteRow(v); }}><DeleteIcon fontSize="small" /></IconButton>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      </CardContent>

      {form ? (
        <Dialog open onClose={() => setForm(null)} maxWidth="xs" fullWidth>
          <DialogTitle>{form.record ? "Edit" : "Create"} code value</DialogTitle>
          <DialogContent dividers>
            <Stack spacing={2} sx={{ mt: 0.5 }}>
              <TextField label="Code" required size="small" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
              <TextField label="Label" required size="small" value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })} />
              <TextField label="Sort order" type="number" size="small" value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: e.target.value })} />
              <Stack direction="row" spacing={3}>
                <FormControlLabel control={<Switch checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />} label="Default" />
                <FormControlLabel control={<Switch checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />} label="Active" />
              </Stack>
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setForm(null)}>Cancel</Button>
            <Button variant="contained" onClick={() => setConfirmSave(true)}>Save</Button>
          </DialogActions>
        </Dialog>
      ) : null}

      <ConfirmDialog open={confirmSave} title="Save code value?" message="Save this code value?" confirmText="Save" busy={busy} onConfirm={doSave} onCancel={() => setConfirmSave(false)} />
      <ConfirmDialog open={Boolean(deleteRow)} title="Deactivate value?" message={deleteRow ? `Deactivate "${deleteRow.label}"? Existing references are preserved.` : ""} confirmText="Deactivate" confirmColor="error" busy={busy} onConfirm={doDelete} onCancel={() => setDeleteRow(null)} />
    </Card>
  );
}