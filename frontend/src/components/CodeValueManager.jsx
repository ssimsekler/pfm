// Code-value administration (ADR #34): pick a code list, then create/edit/
// deactivate its values. System-locked lists are read-only (server enforces;
// UI hides write actions). Every write is confirmed.
import { useCallback, useEffect, useState } from "react";
import {
  Card,
  CardHeader,
  Select,
  Option,
  Label,
  Input,
  Switch,
  Button,
  Bar,
  Text,
  Title,
  BusyIndicator,
  MessageStrip,
  FlexBox,
  Dialog,
} from "@ui5/webcomponents-react";
import { api } from "../api";
import ConfirmDialog from "./ConfirmDialog";

function emptyForm() {
  return { code: "", label: "", sort_order: 100, is_default: false, is_active: true };
}

export default function CodeValueManager() {
  const [lists, setLists] = useState([]);
  const [selected, setSelected] = useState(null); // full code-list object
  const [values, setValues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const [form, setForm] = useState(null); // null=closed; {record?, ...fields}
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleteRow, setDeleteRow] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    (async () => {
      const cls = await api.get("/v1/code-lists").catch(() => []);
      setLists(cls);
      if (cls.length) setSelected(cls[0]);
      setLoading(false);
    })();
  }, []);

  const loadValues = useCallback(async (listKey) => {
    if (!listKey) return;
    const rows = await api
      .get(`/v1/code-lists/${listKey}/values`, { active_only: "" })
      .catch(() => []);
    setValues(rows);
  }, []);

  useEffect(() => {
    if (selected) loadValues(selected.list_key);
  }, [selected, loadValues]);

  const editable = selected && !(selected.is_system && !selected.allow_user_values);

  const openCreate = () => setForm({ ...emptyForm() });
  const openEdit = (row) =>
    setForm({
      record: row,
      code: row.code,
      label: row.label,
      sort_order: row.sort_order,
      is_default: row.is_default,
      is_active: row.is_active,
    });

  async function doSave() {
    setBusy(true);
    setError(null);
    setMsg(null);
    try {
      const key = selected.list_key;
      const payload = {
        code: form.code,
        label: form.label,
        sort_order: Number(form.sort_order) || 0,
        is_default: Boolean(form.is_default),
        is_active: Boolean(form.is_active),
      };
      if (form.record) {
        await api.patch(`/v1/code-lists/${key}/values/${form.record.uuid}`, payload);
      } else {
        await api.post(`/v1/code-lists/${key}/values`, payload);
      }
      setConfirmOpen(false);
      setForm(null);
      setMsg("Saved.");
      loadValues(key);
    } catch (e) {
      setConfirmOpen(false);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function doDelete() {
    if (!deleteRow) return;
    setBusy(true);
    setError(null);
    try {
      await api.del(`/v1/code-lists/${selected.list_key}/values/${deleteRow.uuid}`);
      setDeleteRow(null);
      setMsg("Deactivated.");
      loadValues(selected.list_key);
    } catch (e) {
      setDeleteRow(null);
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card header={<CardHeader titleText="Code Lists (value help)" />} style={{ width: "100%" }}>
      <div style={{ padding: "1rem" }}>
        <BusyIndicator active={loading} style={{ width: "100%" }}>
          {msg ? (
            <MessageStrip design="Positive" hideCloseButton style={{ marginBottom: "0.5rem" }}>{msg}</MessageStrip>
          ) : null}
          {error ? (
            <MessageStrip design="Negative" hideCloseButton style={{ marginBottom: "0.5rem" }}>{error}</MessageStrip>
          ) : null}

          <FlexBox style={{ gap: "0.75rem", alignItems: "flex-end", marginBottom: "0.75rem", flexWrap: "wrap" }}>
            <div>
              <Label>List</Label>
              <Select
                onChange={(e) => {
                  const key = e.detail.selectedOption.dataset.key;
                  setSelected(lists.find((l) => l.list_key === key) || null);
                }}
              >
                {lists.map((cl) => (
                  <Option key={cl.list_key} data-key={cl.list_key} selected={selected?.list_key === cl.list_key}>
                    {cl.list_key}
                  </Option>
                ))}
              </Select>
            </div>
            {editable ? (
              <Button design="Emphasized" icon="add" onClick={openCreate}>Create value</Button>
            ) : (
              <Text style={{ color: "var(--sapNeutralTextColor)" }}>System-managed (read-only)</Text>
            )}
          </FlexBox>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem" }}><Label>Code</Label></th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem" }}><Label>Label</Label></th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem" }}><Label>Order</Label></th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem" }}><Label>Default</Label></th>
                <th style={{ textAlign: "left", padding: "0.4rem 0.5rem" }}><Label>Active</Label></th>
                {editable ? <th style={{ width: "96px" }} /> : null}
              </tr>
            </thead>
            <tbody>
              {values.map((v) => (
                <tr key={v.uuid} style={{ borderBottom: "1px solid var(--sapList_BorderColor,#ededed)" }}>
                  <td style={{ padding: "0.4rem 0.5rem" }}><Text>{v.code}</Text></td>
                  <td style={{ padding: "0.4rem 0.5rem" }}><Text>{v.label}</Text></td>
                  <td style={{ padding: "0.4rem 0.5rem" }}><Text>{v.sort_order}</Text></td>
                  <td style={{ padding: "0.4rem 0.5rem" }}><Text>{v.is_default ? "✓" : ""}</Text></td>
                  <td style={{ padding: "0.4rem 0.5rem" }}><Text>{v.is_active ? "✓" : ""}</Text></td>
                  {editable ? (
                    <td style={{ padding: "0.4rem 0.5rem" }}>
                      <Button icon="edit" design="Transparent" onClick={() => openEdit(v)} />
                      <Button icon="delete" design="Transparent" onClick={() => { setError(null); setDeleteRow(v); }} />
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </BusyIndicator>
      </div>

      {form ? (
        <Dialog
          open
          headerText={`${form.record ? "Edit" : "Create"} code value`}
          onAfterClose={() => setForm(null)}
          footer={
            <Bar
              endContent={
                <>
                  <Button design="Transparent" onClick={() => setForm(null)}>Cancel</Button>
                  <Button design="Emphasized" onClick={() => setConfirmOpen(true)}>Save</Button>
                </>
              }
            />
          }
        >
          <div style={{ padding: "0.5rem 0.25rem", display: "grid", gap: "0.6rem", minWidth: "320px" }}>
            <div>
              <Label showColon required>Code</Label>
              <Input value={form.code} onInput={(e) => setForm({ ...form, code: e.target.value })} style={{ width: "100%" }} />
            </div>
            <div>
              <Label showColon required>Label</Label>
              <Input value={form.label} onInput={(e) => setForm({ ...form, label: e.target.value })} style={{ width: "100%" }} />
            </div>
            <div>
              <Label showColon>Sort order</Label>
              <Input type="Number" value={String(form.sort_order)} onInput={(e) => setForm({ ...form, sort_order: e.target.value })} style={{ width: "100%" }} />
            </div>
            <FlexBox style={{ gap: "1.5rem" }}>
              <div><Label>Default</Label>{" "}<Switch checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} /></div>
              <div><Label>Active</Label>{" "}<Switch checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /></div>
            </FlexBox>
          </div>
        </Dialog>
      ) : null}

      <ConfirmDialog
        open={confirmOpen}
        title="Save code value?"
        message="Do you want to save this code value?"
        confirmText="Save"
        busy={busy}
        onConfirm={doSave}
        onCancel={() => setConfirmOpen(false)}
      />

      <ConfirmDialog
        open={Boolean(deleteRow)}
        title="Deactivate value?"
        message={deleteRow ? `Deactivate "${deleteRow.label}"? Existing references are preserved.` : ""}
        confirmText="Deactivate"
        confirmDesign="Negative"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setDeleteRow(null)}
      />
    </Card>
  );
}