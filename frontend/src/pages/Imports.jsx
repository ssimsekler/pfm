// Import (MUI): two modes.
//  • Statement — messy real-world files (PDF/CSV/XLSX) read by the LLM, then
//    reviewed and committed. Needs the LLM master switch on + a provider.
//  • Bulk — clean structured CSV/XLSX with mnemonic-ID columns, resolved
//    deterministically (no LLM); errored rows are flagged before commit.
import { useEffect, useState } from "react";
import {
  Box, Card, CardHeader, CardContent, Button, Typography, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, Snackbar, Alert, CircularProgress, ToggleButton,
  ToggleButtonGroup, Chip, Tooltip,
} from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import CheckIcon from "@mui/icons-material/Check";
import DownloadIcon from "@mui/icons-material/Download";
import { api } from "../api";
import { getToken } from "../auth";
import ComboField from "../components/ComboField";
import ConfirmDialog from "../components/ConfirmDialog";

const ACCOUNT_FIELD = { type: "ref", refEntity: "accounts" };
const CCY_FIELD = { type: "ref", refEntity: "currencies", refValue: "code", refLabel: "code" };
const COUNTRY_FIELD = { type: "ref", refEntity: "countries", refValue: "iso2", refLabel: "name" };

export default function Imports() {
  const [mode, setMode] = useState("statement");
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
      const fields = { mode };
      if (mode === "statement" && country) fields.country = country;
      const doc = await api.upload("/v1/imports", file, fields);
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

  const downloadTemplate = async () => {
    // Blob download with the bearer token (the API client returns text for CSV).
    try {
      const BASE = import.meta.env.VITE_API_BASE_URL || "/api";
      const headers = {};
      const token = getToken();
      if (token) headers["Authorization"] = "Bearer " + token;
      const resp = await fetch(BASE + "/v1/imports/bulk/template", { headers });
      if (!resp.ok) throw new Error(`${resp.status}`);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pfm_bulk_import_template.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (ex) { setErr("Could not download template: " + ex.message); }
  };

  const doCommit = async () => {
    setConfirmCommit(false);
    if (!selected || !accountId) { setErr("Select an import and a default account."); return; }
    setBusy(true); setErr(null); setMsg(null);
    try {
      const res = await api.post(`/v1/imports/${selected.uuid}/commit`, {
        account_id: accountId, default_currency: defaultCcy, skip_duplicates: true,
      });
      setMsg(`Committed: ${res.created} created, ${res.skipped} skipped.`);
      await openImport(selected);
      await loadImports();
    } catch (ex) { setErr(ex.message); } finally { setBusy(false); }
  };

  const isBulk = mode === "bulk";
  const summary = selected?.parse_summary || {};

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Import Transactions</Typography>

      <Stack spacing={2}>
        <Card>
          <CardHeader
            title="1 · Choose a mode"
            subheader="Statement = messy bank files (LLM-read). Bulk = clean structured file you control."
          />
          <CardContent>
            <ToggleButtonGroup
              exclusive value={mode} color="primary"
              onChange={(_, v) => { if (v) { setMode(v); setSelected(null); setRows([]); } }}
            >
              <ToggleButton value="statement">Statement (LLM)</ToggleButton>
              <ToggleButton value="bulk">Bulk (structured)</ToggleButton>
            </ToggleButtonGroup>

            {isBulk ? (
              <Alert severity="info" sx={{ mt: 2 }}>
                Provide a CSV/XLSX whose columns are <b>mnemonic IDs</b> (account, partner,
                expense_category, beneficiary, goal) plus direct fields (txn_date, amount,
                currency, direction, name, description, note). Values are resolved exactly —
                no guessing.
                <Box sx={{ mt: 1 }}>
                  <Button size="small" startIcon={<DownloadIcon />} onClick={downloadTemplate}>
                    Download CSV template
                  </Button>
                </Box>
              </Alert>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>
                Statement import reads the file with the LLM (robust across bank layouts).
                It must be enabled in <b>Configuration ▸ LLM Providers</b> (master switch on
                + a configured provider). For clean structured data, use <b>Bulk</b> instead.
              </Alert>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="2 · Upload a file" subheader={isBulk ? "CSV or XLSX" : "PDF, CSV or XLSX"} />
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: "wrap" }}>
              {!isBulk ? (
                <Box sx={{ minWidth: 220 }}>
                  <ComboField field={COUNTRY_FIELD} value={country} onChange={setCountry}
                    label="Statement country (date/number format)" />
                </Box>
              ) : null}
              <Button component="label" variant="contained" startIcon={<UploadFileIcon />} disabled={busy}>
                Choose file…
                <input
                  type="file"
                  accept={isBulk ? ".csv,.xlsx,.xls" : ".csv,.xlsx,.xls,.pdf"}
                  hidden
                  onChange={onUpload}
                />
              </Button>
              {busy ? <CircularProgress size={20} /> : null}
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="3 · Recent imports" />
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
            <CardHeader
              title={`4 · Review & commit — ${selected.original_filename}`}
              subheader={
                summary.mode === "bulk"
                  ? `Bulk · ${summary.ok ?? 0} ok, ${summary.errored ?? 0} with errors`
                  : summary.mode === "statement"
                  ? `Statement · ${summary.rows ?? 0} rows`
                  : undefined
              }
            />
            <CardContent>
              {busy ? <CircularProgress size={20} sx={{ mb: 1 }} /> : null}
              <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: "wrap" }} alignItems="center">
                <Box sx={{ minWidth: 260 }}>
                  <ComboField field={ACCOUNT_FIELD} value={accountId} onChange={setAccountId}
                    label="Default account" required />
                </Box>
                <Box sx={{ minWidth: 160 }}>
                  <ComboField field={CCY_FIELD} value={defaultCcy} onChange={setDefaultCcy} label="Default currency" />
                </Box>
                <Button variant="contained" startIcon={<CheckIcon />} onClick={() => setConfirmCommit(true)}>
                  Commit transactions
                </Button>
              </Stack>

              {selected.parse_summary?.mode === "bulk" ? (
                <BulkRows rows={rows} />
              ) : (
                <StatementRows rows={rows} />
              )}
            </CardContent>
          </Card>
        ) : null}
      </Stack>

      <ConfirmDialog
        open={confirmCommit}
        title="Commit import?"
        message={
          selected?.parse_summary?.mode === "bulk"
            ? `Create transactions from "${selected?.original_filename}"? Rows with errors are skipped.`
            : `Create transactions from "${selected?.original_filename}" into the selected account? Duplicates are skipped.`
        }
        confirmText="Commit"
        onConfirm={doCommit}
        onCancel={() => setConfirmCommit(false)}
      />

      <Snackbar open={Boolean(msg)} autoHideDuration={5000} onClose={() => setMsg(null)}>
        <Alert severity="success" onClose={() => setMsg(null)}>{msg}</Alert>
      </Snackbar>
      <Snackbar open={Boolean(err)} autoHideDuration={8000} onClose={() => setErr(null)}>
        <Alert severity="error" onClose={() => setErr(null)}>{err}</Alert>
      </Snackbar>
    </Box>
  );
}

// Statement rows: LLM-extracted + mapped. Show the mapping suggestions.
function StatementRows({ rows }) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Date</TableCell><TableCell>Amount</TableCell><TableCell>Currency</TableCell>
          <TableCell>Partner</TableCell><TableCell>Suggested category</TableCell>
          <TableCell>Account hint</TableCell><TableCell>Committed</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((r) => {
          const mv = r.mapped_values || {};
          const suggested = mv.category_name || mv.suggested_category_name || mv.category || "";
          const acct = mv.account_hint || mv.account || mv.iban || mv.account_number || "";
          const partner = mv.partner_name || mv.partner_name_new || mv.partner || "";
          return (
            <TableRow key={r.uuid}>
              <TableCell>{mv.date || mv.txn_date || ""}</TableCell>
              <TableCell>{mv.amount ?? ""}</TableCell>
              <TableCell>{mv.currency || ""}</TableCell>
              <TableCell>{partner}</TableCell>
              <TableCell>{suggested || <Chip size="small" label="unsure" color="warning" variant="outlined" />}</TableCell>
              <TableCell>{acct}</TableCell>
              <TableCell>{r.target_txn_id ? "✓" : ""}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}

// Bulk rows: deterministically resolved. Flag rows with errors so the user can
// fix the file before committing (errored rows are skipped on commit).
function BulkRows({ rows }) {
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Status</TableCell><TableCell>Date</TableCell><TableCell>Amount</TableCell>
          <TableCell>Currency</TableCell><TableCell>Account</TableCell><TableCell>Partner</TableCell>
          <TableCell>Category</TableCell><TableCell>Errors</TableCell><TableCell>Committed</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {rows.map((r) => {
          const mv = r.mapped_values || {};
          const disp = mv._display || {};
          const errors = mv._errors || [];
          const ok = errors.length === 0;
          return (
            <TableRow key={r.uuid} sx={ok ? undefined : { bgcolor: "error.50" }}>
              <TableCell>
                {ok
                  ? <Chip size="small" label="OK" color="success" variant="outlined" />
                  : <Chip size="small" label="Error" color="error" />}
              </TableCell>
              <TableCell>{mv.txn_date || ""}</TableCell>
              <TableCell>{mv.amount ?? ""}</TableCell>
              <TableCell>{mv.currency || ""}</TableCell>
              <TableCell>{disp.account || ""}</TableCell>
              <TableCell>{disp.partner || ""}</TableCell>
              <TableCell>{disp.expense_category || ""}</TableCell>
              <TableCell>
                {errors.length ? (
                  <Tooltip title={errors.join("; ")}>
                    <span style={{ color: "#c62828" }}>{errors.join("; ")}</span>
                  </Tooltip>
                ) : ""}
              </TableCell>
              <TableCell>{r.target_txn_id ? "✓" : ""}</TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
