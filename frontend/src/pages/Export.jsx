import { useState } from "react";
import {
  Title,
  Card,
  CardHeader,
  Button,
  Input,
  Label,
  Text,
  MessageStrip,
  FlexBox,
  BusyIndicator,
} from "@ui5/webcomponents-react";
import { api } from "../api";
import { getToken } from "../auth";

const BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export default function Export() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [err, setErr] = useState(null);
  const [folder, setFolder] = useState("/data/exports");

  const downloadWorkbook = async () => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const headers = {};
      const token = getToken();
      if (token) headers["Authorization"] = "Bearer " + token;
      const resp = await fetch(BASE + "/v1/export/xlsx", { headers });
      if (!resp.ok) throw new Error(resp.status + ": " + (await resp.text()));
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "pfm_export.xlsx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setMsg("Workbook downloaded.");
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const exportToFolder = async () => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await api.post("/v1/export/to-folder", { folder });
      setMsg("Wrote " + res.count + " files to " + res.folder + ".");
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Export Data</Title>
      {msg ? <MessageStrip design="Positive" hideCloseButton style={{ marginBottom: "0.5rem" }}>{msg}</MessageStrip> : null}
      {err ? <MessageStrip design="Negative" hideCloseButton style={{ marginBottom: "0.5rem" }}>{err}</MessageStrip> : null}

      <BusyIndicator active={busy} style={{ width: "100%" }}>
        <Card header={<CardHeader titleText="Single workbook" subtitleText="One worksheet per entity (config, master, transactional)" />}>
          <div style={{ padding: "1rem" }}>
            <Text>Download all data as a single .xlsx file with one tab per entity.</Text>
            <div style={{ marginTop: "0.75rem" }}>
              <Button design="Emphasized" icon="excel-attachment" onClick={downloadWorkbook}>
                Download workbook
              </Button>
            </div>
          </div>
        </Card>

        <Card
          style={{ marginTop: "1rem" }}
          header={<CardHeader titleText="Separate files to a server folder" subtitleText="Writes one .xlsx per entity into a mounted folder" />}
        >
          <div style={{ padding: "1rem" }}>
            <FlexBox style={{ gap: "1rem", alignItems: "flex-end", flexWrap: "wrap" }}>
              <div>
                <Label>Server folder path</Label>
                <Input value={folder} onInput={(e) => setFolder(e.target.value)} style={{ width: "340px" }} />
              </div>
              <Button icon="folder" onClick={exportToFolder}>Write files</Button>
            </FlexBox>
            <Text style={{ display: "block", marginTop: "0.5rem", color: "var(--sapNeutralTextColor)" }}>
              The folder must be writable by the backend container (e.g. a mounted volume).
            </Text>
          </div>
        </Card>
      </BusyIndicator>
    </div>
  );
}