// Hierarchical entity page (Session 742, Bug 25): Expense Categories &
// Beneficiaries. Offers a Table / Tree toggle. Table view reuses EntityManager;
// Tree view uses EntityTree with the same Create/Edit/Delete flow.
import { useState } from "react";
import {
  Box, Stack, Typography, Button, ToggleButton, ToggleButtonGroup, Snackbar, Alert,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import TableRowsIcon from "@mui/icons-material/TableRows";
import AccountTreeIcon from "@mui/icons-material/AccountTree";
import EntityManager from "../components/EntityManager";
import EntityTree from "../components/EntityTree";
import EntityForm from "../components/EntityForm";
import ConfirmDialog from "../components/ConfirmDialog";
import { ENTITIES } from "../entities";
import { api } from "../api";

export default function HierarchyList({ entity }) {
  const cfg = ENTITIES[entity];
  const [view, setView] = useState("tree");
  const [refreshKey, setRefreshKey] = useState(0);
  const [formRecord, setFormRecord] = useState(undefined); // undefined=closed, null=create, obj=edit
  const [deleteRow, setDeleteRow] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!cfg) return <Typography>Unknown entity: {entity}</Typography>;

  const idField = cfg.idField || "uuid";
  const refresh = () => setRefreshKey((k) => k + 1);

  async function doDelete() {
    if (!deleteRow) return;
    setBusy(true); setError(null);
    try {
      await api.del(`${cfg.path}/${deleteRow[idField]}`);
      setDeleteRow(null);
      setSuccess("Record deleted.");
      refresh();
    } catch (e) {
      setError(e.message);
      setDeleteRow(null);
    } finally { setBusy(false); }
  }

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">{cfg.title}</Typography>
        <Stack direction="row" spacing={1} alignItems="center">
          <ToggleButtonGroup size="small" exclusive value={view}
            onChange={(e, v) => v && setView(v)}>
            <ToggleButton value="tree"><AccountTreeIcon fontSize="small" sx={{ mr: 0.5 }} />Tree</ToggleButton>
            <ToggleButton value="table"><TableRowsIcon fontSize="small" sx={{ mr: 0.5 }} />Table</ToggleButton>
          </ToggleButtonGroup>
          {view === "tree" ? (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setFormRecord(null)}>Create</Button>
          ) : null}
        </Stack>
      </Stack>

      {view === "table" ? (
        <EntityManager entity={entity} cfg={cfg} refreshSignal={refreshKey} />
      ) : (
        <EntityTree
          path={cfg.path}
          refreshKey={refreshKey}
          onEdit={(row) => setFormRecord(row)}
          onDelete={(row) => { setError(null); setDeleteRow(row); }}
        />
      )}

      {formRecord !== undefined ? (
        <EntityForm
          entity={entity}
          cfg={cfg}
          record={formRecord}
          onClose={() => setFormRecord(undefined)}
          onSaved={() => {
            const wasEdit = Boolean(formRecord);
            setFormRecord(undefined);
            setSuccess(wasEdit ? "Changes saved." : "Record created.");
            refresh();
          }}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(deleteRow)}
        title="Delete record?"
        message={deleteRow ? `Delete "${deleteRow.name || deleteRow[idField]}"? This is a soft delete and can be restored by an admin.` : ""}
        confirmText="Delete"
        confirmColor="error"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setDeleteRow(null)}
      />

      <Snackbar open={Boolean(error)} autoHideDuration={6000} onClose={() => setError(null)}>
        <Alert severity="error" onClose={() => setError(null)}>{error}</Alert>
      </Snackbar>
      <Snackbar open={Boolean(success)} autoHideDuration={4000} onClose={() => setSuccess(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
        <Alert severity="success" onClose={() => setSuccess(null)}>{success}</Alert>
      </Snackbar>
    </Box>
  );
}