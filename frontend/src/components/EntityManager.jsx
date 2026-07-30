// Full CRUD manager for an entity (ADR #32): list + Create + row Edit/Delete.
//
// Uses DataTable for listing (adds an Actions column) and EntityForm for
// create/edit. Delete goes through a ConfirmDialog (confirm-on-write).
import { useState } from "react";
import { Button, Title } from "@ui5/webcomponents-react";
import DataTable from "./DataTable";
import EntityForm from "./EntityForm";
import ConfirmDialog from "./ConfirmDialog";
import { api } from "../api";

export default function EntityManager({ entity, cfg }) {
  const idField = cfg.idField || "uuid";
  const [refreshKey, setRefreshKey] = useState(0);
  const [formRecord, setFormRecord] = useState(undefined); // undefined=closed, null=create, obj=edit
  const [deleteRow, setDeleteRow] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const readOnly = Boolean(cfg.readOnly);
  const refresh = () => setRefreshKey((k) => k + 1);

  const columns = readOnly
    ? cfg.columns
    : [
        ...cfg.columns,
        {
          key: "__actions",
          label: "Actions",
          render: (row) => (
            <div style={{ display: "flex", gap: "0.25rem" }}>
              <Button
                icon="edit"
                design="Transparent"
                onClick={(e) => {
                  e.stopPropagation();
                  setFormRecord(row);
                }}
              />
              <Button
                icon="delete"
                design="Transparent"
                onClick={(e) => {
                  e.stopPropagation();
                  setError(null);
                  setDeleteRow(row);
                }}
              />
            </div>
          ),
        },
      ];

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

  const toolbar = readOnly ? null : (
    <Button design="Emphasized" icon="add" onClick={() => setFormRecord(null)}>
      Create
    </Button>
  );

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>{cfg.title}</Title>

      <DataTable
        title={cfg.title}
        path={cfg.path}
        columns={columns}
        toolbar={toolbar}
        refreshKey={refreshKey}
      />

      {formRecord !== undefined ? (
        <EntityForm
          entity={entity}
          cfg={cfg}
          record={formRecord}
          onClose={() => setFormRecord(undefined)}
          onSaved={() => {
            setFormRecord(undefined);
            refresh();
          }}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(deleteRow)}
        title="Delete record?"
        message={
          deleteRow
            ? `Delete "${deleteRow.name || deleteRow[idField]}"? This can be undone by an admin (soft delete).`
            : ""
        }
        confirmText="Delete"
        confirmDesign="Negative"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setDeleteRow(null)}
      />

      {error ? (
        <div style={{ color: "var(--sapNegativeTextColor)", marginTop: "0.5rem" }}>{error}</div>
      ) : null}
    </div>
  );
}