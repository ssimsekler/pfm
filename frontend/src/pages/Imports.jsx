// Import statements (MUI): upload → review parsed rows → commit (confirmed).
import { useEffect, useState } from "react";
import {
  Box, Card, CardHeader, CardContent, Button, Typography, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, Snackbar, Alert, CircularProgress, TextField,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CheckIcon from "@mui/icons-material/Check";
import { api } from "../api";
import ComboField from "../components/ComboField";
import ConfirmDialog from "../components/ConfirmDialog";

const ACCOUNT_FIELD = { type: "ref", refEntity: "accounts" };
const CCY_FIELD = { type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" };
const COUNTRY_FIELD = { type: "ref", refEntity: "countries", refValue: "iso2", refLabel: "name" };

export default function Imports() {
  const [imports, setImports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rows, setRows] = useState([]);
  const [accountId, setAccountId] = useState("");
  const [defaultCcy, setDefaultCcy] = useState("AED");
  const [country, setCountry] = useState("");
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const [confirmCommit, setConfirmCommit] = useState(false);

  const loadImports = async () => {
    const data = await api.get("/v1/imports", { limit: 50 }).catch(() => ({ items: [] }));
    setImports(data.items || []);
  };
  useEffect(() => { loadImports(); }, []);

  const onUpload = async (e) => {
    const file = e.target?.files?.[0];
    if (!file) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      const doc = await api.upload("/v1/imports", file, country ? { country } : {});
      setMsg(`Uploaded & parsed: ${doc.original_filename}`);
      await loadImports();
      await openImport(doc);
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); e.target.value = ""; }
  };

  const openImport = async (doc) => {
    setSelected(doc);
    const r = await api.get(`/v1/imports/${doc.uuid}/rows`).catch(() => []);
    setRows(r || []);
  };

  const doCommit = async () => {
    setConfirmCommit(false);
    if (!selected || !accountId) { setErr("Select an import and an account."); return; }
    setBusy(true); setErr(null); setMsg(null);
    try {
      const res = await api.post(`/v1/imports/${selected.uuid}/commit`, {
        account_id: accountId, default_currency: defaultCcy, skip_duplicates: true,
      });
      setMsg(`Committed: ${res.created} created, ${res.skipped} skipped.`);
      await openImport(selected);
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Import Statements</Typography>

      <Stack spacing={2}>
        <Card>
          <CardHeader title="1 · Upload a file" subheader="PDF, CSV or XLSX" />
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: "wrap" }}>
              <Box sx={{ minWidth: 220 }}>
                <ComboField field={COUNTRY_FIELD} value={country} onChange={setCountry}
                  label="Statement country (date/number format)" />
              </Box>
              <Button component="label" variant="contained" startIcon={<UploadFileIcon />} disabled={busy}>
                Choose file…
                <input type="file" accept=".csv,.xlsx,.xls,.pdf" hidden onChange={onUpload} />
              </Button>
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="2 · Recent imports" />
          <CardContent>
            <Table size="small">
              <TableHead><TableRow><TableCell>File</TableCell><TableCell>Summary</TableCell><TableCell /></TableRow></TableHead>
              <TableBody>
                {imports.map((d) => (
                  <TableRow key={d.uuid} hover>
                    <TableCell>{d.original_filename}</TableCell>
                    <TableCell>{d.parse_summary ? JSON.stringify(d.parse_summary) : ""}</TableCell>
                    <TableCell><Button size="small" onClick={() => openImport(d)}>Review</Button></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {selected ? (
          <Card>
            <CardHeader title={`3 · Review & commit — ${selected.original_filename}`} />
            <CardContent>
              {busy ? <CircularProgress size={20} sx={{ mb: 1 }} /> : null}
              <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: "wrap" }} alignItems="center">
                <Box sx={{ minWidth: 260 }}>
                  <ComboField field={ACCOUNT_FIELD} value={accountId} onChange={setAccountId} label="Account" required />
                </Box>
                <Box sx={{ minWidth: 160 }}>
                  <ComboField field={CCY_FIELD} value={defaultCcy} onChange={setDefaultCcy} label="Default currency" />
                </Box>
                <Button variant="contained" startIcon={<CheckIcon />} onClick={() => setConfirmCommit(true)}>Commit transactions</Button>
              </Stack>

              <Table size="small">
                <TableHead>
                  <TableRow><TableCell>Date</TableCell><TableCell>Amount</TableCell><TableCell>Currency</TableCell><TableCell>Partner</TableCell><TableCell>Status</TableCell><TableCell>Committed</TableCell></TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((r) => {
                    const mv = r.mapped_values || {};
                    return (
                      <TableRow key={r.uuid}>
                        <TableCell>{mv.date || ""}</TableCell>
                        <TableCell>{mv.amount ?? ""}</TableCell>
                        <TableCell>{mv.currency || ""}</TableCell>
                        <TableCell>{mv.partner_name || mv.partner_name_new || mv.partner || ""}</TableCell>
                        <TableCell>{r.mapping_status_cv_id ? "mapped" : ""}</TableCell>
                        <TableCell>{r.target_txn_id ? "✓" : ""}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ) : null}
      </Stack>

      <ConfirmDialog
        open={confirmCommit}
        title="Commit import?"
        message={`Create transactions from "${selected?.original_filename}" into the selected account? Duplicates are skipped.`}
        confirmText="Commit"
        onConfirm={doCommit}
        onCancel={() => setConfirmCommit(false)}
      />

      <Snackbar open={Boolean(msg)} autoHideDuration={5000} onClose={() => setMsg(null)}>
        <Alert severity="success" onClose={() => setMsg(null)}>{msg}</Alert>
      </Snackbar>
      <Snackbar open={Boolean(err)} autoHideDuration={7000} onClose={() => setErr(null)}>
        <Alert severity="error" onClose={() => setErr(null)}>{err}</Alert>
      </Snackbar>
    </Box>
  );
}