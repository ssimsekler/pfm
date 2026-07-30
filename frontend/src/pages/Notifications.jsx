import { useCallback, useEffect, useState } from "react";
import {
  Title,
  Table,
  TableColumn,
  TableRow,
  TableCell,
  Label,
  Text,
  Button,
  Bar,
  Switch,
  BusyIndicator,
  MessageStrip,
} from "@ui5/webcomponents-react";
import { api } from "../api";

export default function Notifications() {
  const [rows, setRows] = useState([]);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get("/v1/notifications", {
        unread_only: unreadOnly ? "true" : "",
        limit: 200,
      });
      setRows(Array.isArray(data) ? data : data.items || []);
    } catch (e) {
      setError(e.message);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    load();
  }, [load]);

  const markRead = async (uuid) => {
    setError(null);
    setMsg(null);
    try {
      await api.post(`/v1/notifications/${uuid}/read`);
      setMsg("Marked as read.");
      load();
    } catch (e) {
      setError(e.message);
    }
  };

  const fmtDate = (v) => {
    if (!v) return "";
    try {
      return new Date(v).toLocaleString();
    } catch {
      return String(v);
    }
  };

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Notifications</Title>

      {msg ? (
        <MessageStrip design="Positive" hideCloseButton style={{ marginBottom: "0.5rem" }}>{msg}</MessageStrip>
      ) : null}
      {error ? (
        <MessageStrip design="Negative" hideCloseButton style={{ marginBottom: "0.5rem" }}>{error}</MessageStrip>
      ) : null}

      <Bar
        startContent={<Title level="H4">Notification center</Title>}
        endContent={
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <Label>Unread only</Label>
            <Switch checked={unreadOnly} onChange={(e) => setUnreadOnly(e.target.checked)} />
            <Button icon="refresh" onClick={load}>Refresh</Button>
          </div>
        }
        style={{ marginBottom: "0.5rem" }}
      />

      <BusyIndicator active={loading} style={{ width: "100%" }}>
        <Table
          columns={[
            <TableColumn key="s"><Label>Subject</Label></TableColumn>,
            <TableColumn key="b"><Label>Body</Label></TableColumn>,
            <TableColumn key="c"><Label>Created</Label></TableColumn>,
            <TableColumn key="a"><Label>Action</Label></TableColumn>,
          ]}
        >
          {rows.map((n) => (
            <TableRow key={n.uuid}>
              <TableCell><Text>{n.subject}</Text></TableCell>
              <TableCell><Text>{n.body}</Text></TableCell>
              <TableCell><Text>{fmtDate(n.created_at)}</Text></TableCell>
              <TableCell>
                <Button design="Transparent" icon="accept" onClick={() => markRead(n.uuid)}>
                  Mark read
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </Table>
      </BusyIndicator>

      <Text style={{ display: "block", marginTop: "0.5rem" }}>{rows.length} notification(s)</Text>
    </div>
  );
}