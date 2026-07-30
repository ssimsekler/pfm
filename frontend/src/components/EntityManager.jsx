// Full CRUD manager (MUI): title + Create + filter bar + DataGrid (with row
// Edit/Delete) + EntityForm dialog. Delete is confirmed (ADR #38).
import { useState } from "react";
import { Box, Button, IconButton, Stack, Typography, Snackbar, Alert, Tooltip } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import DataTable from "./DataTable";
import EntityForm from "./EntityForm";
import ConfirmDialog from "./ConfirmDialog";
import FilterBar from "./FilterBar";
import { api } from "../api";

export default function EntityManager({ entity, cfg, extra }) {
  const idField = cfg.idField || "uuid";
  const readOnly = Boolean(cfg.readOnly);
  const [refreshKey, setRefreshKey] = useState(0);
  const [formRecord, setFormRecord] = useState(undefined); // undefined=closed, null=create, obj=edit
  const [deleteRow, setDeleteRow] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [filterParams, setFilterParams] = useState({});

  const refresh = () => setRefreshKey((k) => k + 1);

  const actions = readOnly
    ? undefined
    : (row) => (
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Edit"><IconButton size="small" onClick={() => setFormRecord(row)}><EditIcon fontSize="small" /></IconButton></Tooltip>
          <Tooltip title="Delete"><IconButton size="small" color="error" onClick={() => { setError(null); setDeleteRow(row); }}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
        </Stack>
      );

  async function doDelete() {
    if (!deleteRow) return;
    setBusy(true);
    setError(null);
    try {
      await api.del(`${cfg.path}/${deleteRow[idField]}`);
      setDeleteRow(null);
      refresh();
    } catch (e) {
      setError(e.message);
      setDeleteRow(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">{cfg.title}</Typography>
        <Stack direction="row" spacing={1}>
          {extra}
          {!readOnly ? (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setFormRecord(null)}>Create</Button>
          ) : null}
        </Stack>
      </Stack>

      {cfg.filterFields && cfg.filterFields.length > 0 ? (
        <FilterBar fields={cfg.filterFields} onApply={setFilterParams} />
      ) : null}

      <DataTable
        path={cfg.path}
        columns={cfg.columns}
        extraParams={filterParams}
        refreshKey={refreshKey}
        actions={actions}
        getRowId={(r) => r[idField]}
      />

      {formRecord !== undefined ? (
        <EntityForm
          entity={entity}
          cfg={cfg}
          record={formRecord}
          onClose={() => setFormRecord(undefined)}
          onSaved={() => { setFormRecord(undefined); refresh(); }}
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
    </Box>
  );
}