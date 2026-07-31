// Credentials Store manager (Session 815, Item 19). Lists credentials, and
// creates/edits them with a **dynamic form** generated from the selected
// category's parameter schema:
//   - type "enum"      → combobox (fixed value set)
//   - type "password"  → masked password input (sensitive; shown as ******** on read)
//   - type "number"    → number input
//   - else             → text input
// Sensitive values are never returned in clear by the API; submitting the mask
// unchanged preserves the stored secret.
import { useCallback, useEffect, useState } from "react";
import {
  Box, Card, CardHeader, CardContent, Table, TableBody, TableCell, TableHead, TableRow,
  Button, IconButton, Tooltip, Alert, Stack, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, MenuItem, Typography, Chip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import { api } from "../api";

function DynamicField({ param, value, onChange }) {
  const label = param.label || param.key;
  if (param.type === "enum") {
    return (
      <TextField label={label} size="small" select value={value ?? ""} required={param.required}
        onChange={(e) => onChange(e.target.value)}>
        <MenuItem value=""><em>None</em></MenuItem>
        {(param.options || []).map((o) => <MenuItem key={o} value={o}>{o}</MenuItem>)}
      </TextField>
    );
  }
  const type = param.type === "password" ? "password" : param.type === "number" ? "number" : "text";
  return (
    <TextField label={label} size="small" type={type} value={value ?? ""} required={param.required}
      placeholder={param.placeholder || ""} onChange={(e) => onChange(e.target.value)} />
  );
}

function CredentialDialog({ categories, record, onClose, onSaved }) {
  const isEdit = Boolean(record);
  const [categoryId, setCategoryId] = useState(record?.category_id || (categories[0]?.uuid || ""));
  const [name, setName] = useState(record?.name || "");
  const [values, setValues] = useState(record?.values || {});
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const category = categories.find((c) => c.uuid === categoryId);
  const params = category?.params || [];

  const save = async () => {
    setBusy(true); setError(null);
    try {
      if (isEdit) {
        await api.patch(`/v1/credentials/${record.uuid}`, { name, values });
      } else {
        await api.post("/v1/credentials", { name, category_id: categoryId, values });
      }
      onSaved();
    } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Dialog open onClose={busy ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{isEdit ? "Edit credential" : "New credential"}</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        <Stack spacing={2} sx={{ mt: 0.5 }}>
          <TextField label="Name" size="small" value={name} onChange={(e) => setName(e.target.value)} required />
          <TextField label="Category" size="small" select value={categoryId}
            disabled={isEdit}
            onChange={(e) => { setCategoryId(e.target.value); setValues({}); }}>
            {categories.map((c) => <MenuItem key={c.uuid} value={c.uuid}>{c.name}</MenuItem>)}
          </TextField>
          {params.map((p) => (
            <DynamicField key={p.key} param={p} value={values[p.key]}
              onChange={(v) => setValues((s) => ({ ...s, [p.key]: v }))} />
          ))}
          {params.length === 0 ? (
            <Typography variant="caption" color="text.secondary">This category has no parameters.</Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>Cancel</Button>
        <Button variant="contained" onClick={save} disabled={busy || !name || !categoryId}>
          {busy ? "Saving…" : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default function CredentialsManager() {
  const [categories, setCategories] = useState([]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [dialog, setDialog] = useState(undefined); // undefined=closed, null=create, obj=edit
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [cats, creds] = await Promise.all([
        api.get("/v1/credential-categories").catch(() => []),
        api.get("/v1/credentials").catch(() => []),
      ]);
      setCategories(cats || []);
      setRows(creds || []);
    } catch (e) { setError(e.message); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const remove = async (row) => {
    setBusy(true); setError(null);
    try {
      await api.del(`/v1/credentials/${row.uuid}`);
      await load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  return (
    <Card>
      <CardHeader title="Credentials Store"
        subheader="Named credential value-sets by category (e.g. Email). Sensitive fields are masked; the dynamic form is driven by each category's parameter schema." />
      <CardContent>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
        <Box sx={{ mb: 2 }}>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialog(null)}
            disabled={categories.length === 0}>New credential</Button>
        </Box>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell><TableCell>Category</TableCell>
              <TableCell>ID</TableCell><TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((c) => (
              <TableRow key={c.uuid} hover>
                <TableCell>{c.name}</TableCell>
                <TableCell><Chip size="small" label={c.category_key || "—"} /></TableCell>
                <TableCell><code>{c.mnemonic_id}</code></TableCell>
                <TableCell align="right">
                  <Tooltip title="Edit"><span>
                    <IconButton size="small" onClick={() => setDialog(c)}><EditIcon fontSize="small" /></IconButton>
                  </span></Tooltip>
                  <Tooltip title="Delete"><span>
                    <IconButton size="small" color="error" disabled={busy} onClick={() => remove(c)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </span></Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 ? (
              <TableRow><TableCell colSpan={4}><Typography color="text.secondary">No credentials yet.</Typography></TableCell></TableRow>
            ) : null}
          </TableBody>
        </Table>
      </CardContent>

      {dialog !== undefined ? (
        <CredentialDialog
          categories={categories}
          record={dialog}
          onClose={() => setDialog(undefined)}
          onSaved={() => { setDialog(undefined); load(); }}
        />
      ) : null}
    </Card>
  );
}