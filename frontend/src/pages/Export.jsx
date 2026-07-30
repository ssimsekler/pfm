// Export & Import Data (MUI): single-workbook download, per-entity folder export,
// and destructive round-trip import (confirmed, ADR #38).
import { useState } from "react";
import {
  Box, Card, CardHeader, CardContent, Button, TextField, Typography, Stack,
  Alert, Snackbar,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import FolderIcon from "@mui/icons-material/Folder";
import UploadIcon from "@mui/icons-material/Upload";
import { api } from "../api";
import { getToken } from "../auth";
import ConfirmDialog from "../components/ConfirmDialog";

const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export default function Export() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [folder, setFolder] = useState("/data/exports");
  const [importFile, setImportFile] = useState(null);
  const [confirmImport, setConfirmImport] = useState(false);

  const downloadWorkbook = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try {
      const headers = {};
      const token = getToken();
      if (token) headers["Authorization"] = "Bearer " + token;
      const resp = await fetch(BASE + "/v1/export/xlsx", { headers });
      if (!resp.ok) throw new Error(resp.status + ": " + (await resp.text()));
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "pfm_export.xlsx";
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      setMsg("Workbook downloaded.");
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  const exportToFolder = async () => {
    setBusy(true); setErr(null); setMsg(null);
    try {
      const res = await api.post("/v1/export/to-folder", { folder });
      setMsg(`Wrote ${res.count} files to ${res.folder}.`);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  const importWorkbook = async () => {
    setConfirmImport(false);
    if (!importFile) { setErr("Choose an .xlsx file first."); return; }
    setBusy(true); setErr(null); setMsg(null);
    try {
      const headers = {};
      const token = getToken();
      if (token) headers["Authorization"] = "Bearer " + token;
      const form = new FormData();
      form.append("file", importFile);
      const resp = await fetch(BASE + "/v1/import/xlsx", { method: "POST", headers, body: form });
      if (!resp.ok) throw new Error(resp.status + ": " + (await resp.text()));
      const res = await resp.json();
      setMsg(`Import complete. ${res.total} rows written.`);
      setImportFile(null);
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Export &amp; Import Data</Typography>
      <Stack spacing={2}>
        <Card>
          <CardHeader title="Single workbook" subheader="One worksheet per entity (config, master, transactional)" />
          <CardContent>
            <Typography sx={{ mb: 1.5 }}>Download all data as a single .xlsx file with one tab per entity.</Typography>
            <Button variant="contained" startIcon={<DownloadIcon />} onClick={downloadWorkbook} disabled={busy}>Download workbook</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Separate files to a server folder" subheader="Writes one .xlsx per entity into a mounted folder" />
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: "wrap" }}>
              <TextField label="Server folder path" size="small" value={folder} onChange={(e) => setFolder(e.target.value)} sx={{ width: 340 }} />
              <Button startIcon={<FolderIcon />} onClick={exportToFolder} disabled={busy}>Write files</Button>
            </Stack>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              The folder must be writable by the backend container (e.g. a mounted volume).
            </Typography>
          </CardContent>
        </Card>

        <Card>
          <CardHeader title="Import workbook" subheader="Wipe & reload all entities from an export file" />
          <CardContent>
            <Alert severity="warning" sx={{ mb: 2 }}>
              Destructive: importing deletes all existing data first, then writes the file content.
              Use only on a clean instance or to fully replace content.
            </Alert>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ flexWrap: "wrap" }}>
              <Button component="label" variant="outlined">
                {importFile ? importFile.name : "Choose .xlsx…"}
                <input type="file" accept=".xlsx" hidden onChange={(e) => setImportFile(e.target.files?.[0] || null)} />
              </Button>
              <Button color="error" variant="contained" startIcon={<UploadIcon />} disabled={!importFile || busy} onClick={() => setConfirmImport(true)}>
                Import &amp; replace
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>

      <ConfirmDialog
        open={confirmImport}
        title="Replace ALL data?"
        message="This deletes all existing data and reloads it from the file. This cannot be undone. Continue?"
        confirmText="Replace all data"
        confirmColor="error"
        busy={busy}
        onConfirm={importWorkbook}
        onCancel={() => setConfirmImport(false)}
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