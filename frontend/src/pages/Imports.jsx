import { useEffect, useState } from "react";
import {
  Title,
  Card,
  CardHeader,
  Button,
  FileUploader,
  Input,
  Label,
  Table,
  TableColumn,
  TableRow,
  TableCell,
  Text,
  MessageStrip,
  FlexBox,
  BusyIndicator,
} from "@ui5/webcomponents-react";
import { api } from "../api";

export default function Imports() {
  const [imports, setImports] = useState([]);
  const [selected, setSelected] = useState(null);
  const [rows, setRows] = useState([]);
  const [accountId, setAccountId] = useState("");
  const [defaultCcy, setDefaultCcy] = useState("AED");
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const loadImports = async () => {
    const data = await api.get("/v1/imports", { limit: 50 }).catch(() => ({ items: [] }));
    setImports(data.items || []);
  };

  useEffect(() => { loadImports(); }, []);

  const onUpload = async (event) => {
    const file = event.detail?.files?.[0] || event.target?.files?.[0];
    if (!file) return;
    setBusy(true); setErr(null); setMsg(null);
    try {
      const doc = await api.upload("/v1/imports", file);
      setMsg(`Uploaded & parsed: ${doc.original_filename}`);
      await loadImports();
      await openImport(doc);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const openImport = async (doc) => {
    setSelected(doc);
    const r = await api.get(`/v1/imports/${doc.uuid}/rows`).catch(() => []);
    setRows(r || []);
  };

  const commit = async () => {
    if (!selected || !accountId) { setErr("Select an import and enter an Account UUID."); return; }
    setBusy(true); setErr(null); setMsg(null);
    try {
      const res = await api.post(`/v1/imports/${selected.uuid}/commit`, {
        account_id: accountId,
        default_currency: defaultCcy,
        skip_duplicates: true,
      });
      setMsg(`Committed: ${res.created} created, ${res.skipped} skipped.`);
      await openImport(selected);
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Import Statements</Title>

      {msg && <MessageStrip design="Positive" hideCloseButton style={{ marginBottom: "0.5rem" }}>{msg}</MessageStrip>}
      {err && <MessageStrip design="Negative" hideCloseButton style={{ marginBottom: "0.5rem" }}>{err}</MessageStrip>}

      <Card header={<CardHeader titleText="1 · Upload a file" subtitleText="PDF, CSV or XLSX" />}>
        <div style={{ padding: "1rem" }}>
          <FileUploader accept=".csv,.xlsx,.xls,.pdf" hideInput onChange={onUpload}>
            <Button design="Emphasized" icon="upload">Choose file…</Button>
          </FileUploader>
        </div>
      </Card>

      <Card style={{ marginTop: "1rem" }} header={<CardHeader titleText="2 · Recent imports" />}>
        <Table
          columns={[
            <TableColumn key="f"><Label>File</Label></TableColumn>,
            <TableColumn key="s"><Label>Summary</Label></TableColumn>,
            <TableColumn key="a"><Label></Label></TableColumn>,
          ]}
        >
          {imports.map((d) => (
            <TableRow key={d.uuid}>
              <TableCell><Text>{d.original_filename}</Text></TableCell>
              <TableCell><Text>{d.parse_summary ? JSON.stringify(d.parse_summary) : ""}</Text></TableCell>
              <TableCell><Button onClick={() => openImport(d)}>Review</Button></TableCell>
            </TableRow>
          ))}
        </Table>
      </Card>

      {selected && (
        <Card style={{ marginTop: "1rem" }} header={<CardHeader titleText={`3 · Review & commit — ${selected.original_filename}`} />}>
          <BusyIndicator active={busy} style={{ width: "100%" }}>
            <div style={{ padding: "1rem" }}>
              <FlexBox style={{ gap: "1rem", alignItems: "flex-end", marginBottom: "0.75rem", flexWrap: "wrap" }}>
                <div>
                  <Label>Account UUID</Label>
                  <Input value={accountId} placeholder="account uuid" onInput={(e) => setAccountId(e.target.value)} style={{ width: "320px" }} />
                </div>
                <div>
                  <Label>Default currency</Label>
                  <Input value={defaultCcy} onInput={(e) => setDefaultCcy(e.target.value)} style={{ width: "120px" }} />
                </div>
                <Button design="Emphasized" icon="accept" onClick={commit}>Commit transactions</Button>
              </FlexBox>

              <Table
                columns={[
                  <TableColumn key="d"><Label>Date</Label></TableColumn>,
                  <TableColumn key="a"><Label>Amount</Label></TableColumn>,
                  <TableColumn key="c"><Label>Currency</Label></TableColumn>,
                  <TableColumn key="p"><Label>Partner</Label></TableColumn>,
                  <TableColumn key="s"><Label>Status</Label></TableColumn>,
                  <TableColumn key="t"><Label>Committed</Label></TableColumn>,
                ]}
              >
                {rows.map((r) => {
                  const mv = r.mapped_values || {};
                  return (
                    <TableRow key={r.uuid}>
                      <TableCell><Text>{mv.date || ""}</Text></TableCell>
                      <TableCell><Text>{mv.amount ?? ""}</Text></TableCell>
                      <TableCell><Text>{mv.currency || ""}</Text></TableCell>
                      <TableCell><Text>{mv.partner_name || mv.partner_name_new || mv.partner || ""}</Text></TableCell>
                      <TableCell><Text>{r.mapping_status_cv_id ? "mapped" : ""}</Text></TableCell>
                      <TableCell><Text>{r.target_txn_id ? "✓" : ""}</Text></TableCell>
                    </TableRow>
                  );
                })}
              </Table>
            </div>
          </BusyIndicator>
        </Card>
      )}
    </div>
  );
}