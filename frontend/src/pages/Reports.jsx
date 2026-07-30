import { useEffect, useState } from "react";
import {
  Title,
  Card,
  CardHeader,
  Button,
  TextArea,
  Table,
  TableColumn,
  TableRow,
  TableCell,
  Label,
  Text,
  MessageStrip,
  FlexBox,
  FlexBoxWrap,
  BusyIndicator,
} from "@ui5/webcomponents-react";
import { BarChart } from "@ui5/webcomponents-react-charts";
import { api } from "../api";

export default function Reports() {
  const [catData, setCatData] = useState([]);
  const [cash, setCash] = useState(null);
  const [worth, setWorth] = useState(null);
  const [loading, setLoading] = useState(true);

  const [sql, setSql] = useState("SELECT mnemonic_id, name, currency FROM pfm.account LIMIT 20");
  const [sqlResult, setSqlResult] = useState(null);
  const [sqlError, setSqlError] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [vc, c, w] = await Promise.all([
          api.get("/v1/reports/volume-by-category").catch(() => ({ items: [] })),
          api.get("/v1/reports/cash-position").catch(() => null),
          api.get("/v1/reports/net-worth").catch(() => null),
        ]);
        setCatData((vc.items || []).map((i) => ({ category: i.category, amount: Number(i.amount) })));
        setCash(c);
        setWorth(w);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const runSql = async () => {
    setRunning(true);
    setSqlError(null);
    setSqlResult(null);
    try {
      const res = await api.post("/v1/reports/sql", { sql });
      setSqlResult(res);
    } catch (e) {
      setSqlError(e.message);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Reports</Title>
      <BusyIndicator active={loading} style={{ width: "100%" }}>
        <FlexBox wrap={FlexBoxWrap.Wrap} style={{ gap: "1rem" }}>
          <Card
            style={{ width: "520px" }}
            header={<CardHeader titleText="Volume by Category" subtitleText="Reporting currency (USD)" />}
          >
            <div style={{ padding: "1rem", height: "320px" }}>
              {catData.length > 0 ? (
                <BarChart
                  dataset={catData}
                  dimensions={[{ accessor: "category" }]}
                  measures={[{ accessor: "amount", label: "Amount" }]}
                />
              ) : (
                <Text>No data yet.</Text>
              )}
            </div>
          </Card>

          <Card
            style={{ width: "320px" }}
            header={<CardHeader titleText="Headline Figures" />}
          >
            <div style={{ padding: "1rem" }}>
              <FlexBox style={{ justifyContent: "space-between", padding: "0.35rem 0" }}>
                <Text>Cash total ({cash?.reporting_currency})</Text>
                <Text>{cash?.total_reporting ?? "—"}</Text>
              </FlexBox>
              <FlexBox style={{ justifyContent: "space-between", padding: "0.35rem 0" }}>
                <Text>Investments</Text>
                <Text>{worth?.investments ?? "—"}</Text>
              </FlexBox>
              <FlexBox style={{ justifyContent: "space-between", padding: "0.35rem 0" }}>
                <Text>Net worth</Text>
                <Text>{worth?.net_worth ?? "—"}</Text>
              </FlexBox>
            </div>
          </Card>
        </FlexBox>
      </BusyIndicator>

      <Card
        style={{ marginTop: "1.5rem" }}
        header={<CardHeader titleText="SQL Console" subtitleText="Read-only · single SELECT · limited rows" />}
      >
        <div style={{ padding: "1rem" }}>
          <Label>Query</Label>
          <TextArea
            value={sql}
            rows={4}
            style={{ width: "100%", fontFamily: "monospace" }}
            onInput={(e) => setSql(e.target.value)}
          />
          <div style={{ marginTop: "0.5rem" }}>
            <Button design="Emphasized" icon="play" onClick={runSql} disabled={running}>
              Run
            </Button>
          </div>
          {sqlError && (
            <MessageStrip design="Negative" hideCloseButton style={{ marginTop: "0.5rem" }}>
              {sqlError}
            </MessageStrip>
          )}
          {sqlResult && (
            <div style={{ marginTop: "0.75rem" }}>
              <Text>{sqlResult.row_count} row(s){sqlResult.truncated ? " (truncated)" : ""}</Text>
              <Table
                columns={(sqlResult.columns || []).map((c) => (
                  <TableColumn key={c}><Label>{c}</Label></TableColumn>
                ))}
              >
                {(sqlResult.rows || []).map((row, ri) => (
                  <TableRow key={ri}>
                    {row.map((v, ci) => (
                      <TableCell key={ci}><Text>{v === null ? "" : String(v)}</Text></TableCell>
                    ))}
                  </TableRow>
                ))}
              </Table>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}