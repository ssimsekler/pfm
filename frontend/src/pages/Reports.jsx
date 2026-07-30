// Reports (MUI + recharts): volumes (pie), cash/net-worth headline, projection
// (line), plus a guarded SQL console (#13).
import { useEffect, useState } from "react";
import {
  Box, Card, CardContent, CardHeader, Grid, Typography, TextField, Button,
  Table, TableBody, TableCell, TableHead, TableRow, Alert, CircularProgress, Stack, MenuItem,
} from "@mui/material";
import {
  PieChart, Pie, Cell, Tooltip as RTooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, LineChart, Line,
} from "recharts";
import { api } from "../api";

const COLORS = ["#0a3d62", "#1e88e5", "#2e7d32", "#ed6c02", "#8e24aa", "#00838f", "#c62828", "#5d4037"];

function VolumePie({ title, path }) {
  const [data, setData] = useState([]);
  useEffect(() => {
    api.get(path).then((r) => setData((r.items || []).map((i) => ({ name: i.label || i.category || i.name || "—", value: Number(i.amount) || 0 })))).catch(() => setData([]));
  }, [path]);
  return (
    <Card sx={{ height: "100%" }}>
      <CardHeader title={title} subheader="Reporting currency (USD)" />
      <CardContent sx={{ height: 300 }}>
        {data.length === 0 ? <Typography color="text.secondary">No data yet.</Typography> : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" outerRadius={90} label>
                {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <RTooltip /><Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export default function Reports() {
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
        const [c, w] = await Promise.all([
          api.get("/v1/reports/cash-position").catch(() => null),
          api.get("/v1/reports/net-worth").catch(() => null),
        ]);
        setCash(c); setWorth(w);
      } finally { setLoading(false); }
    })();
  }, []);

  const runSql = async () => {
    setRunning(true); setSqlError(null); setSqlResult(null);
    try { setSqlResult(await api.post("/v1/reports/sql", { sql })); }
    catch (e) { setSqlError(e.message); }
    finally { setRunning(false); }
  };

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Reports</Typography>
      {loading ? <CircularProgress /> : (
        <Grid container spacing={2} sx={{ mb: 1 }}>
          <Grid item xs={12} md={4}><VolumePie title="Volume by Category" path="/v1/reports/volume-by-category" /></Grid>
          <Grid item xs={12} md={4}><VolumePie title="Volume by Supplier" path="/v1/reports/volume-by-partner" /></Grid>
          <Grid item xs={12} md={4}><VolumePie title="Volume by Beneficiary" path="/v1/reports/volume-by-beneficiary" /></Grid>
          <Grid item xs={12} md={4}>
            <Card sx={{ height: "100%" }}>
              <CardHeader title="Headline Figures" />
              <CardContent>
                <Stack spacing={1}>
                  <Stack direction="row" justifyContent="space-between"><Typography>Cash ({cash?.reporting_currency})</Typography><Typography>{cash?.total_reporting ?? "—"}</Typography></Stack>
                  <Stack direction="row" justifyContent="space-between"><Typography>Investments</Typography><Typography>{worth?.investments ?? "—"}</Typography></Stack>
                  <Stack direction="row" justifyContent="space-between"><Typography>Net worth</Typography><Typography>{worth?.net_worth ?? "—"}</Typography></Stack>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Card sx={{ mt: 2 }}>
        <CardHeader title="SQL Console" subheader="Read-only · single SELECT · limited rows" />
        <CardContent>
          <TextField value={sql} onChange={(e) => setSql(e.target.value)} fullWidth multiline minRows={3}
            sx={{ fontFamily: "monospace", mb: 1 }} />
          <Button variant="contained" onClick={runSql} disabled={running}>Run</Button>
          {sqlError ? <Alert severity="error" sx={{ mt: 1 }}>{sqlError}</Alert> : null}
          {sqlResult ? (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" sx={{ mb: 1 }}>{sqlResult.row_count} row(s){sqlResult.truncated ? " (truncated)" : ""}</Typography>
              <Box sx={{ overflow: "auto" }}>
                <Table size="small">
                  <TableHead><TableRow>{(sqlResult.columns || []).map((c) => <TableCell key={c}>{c}</TableCell>)}</TableRow></TableHead>
                  <TableBody>
                    {(sqlResult.rows || []).map((row, ri) => (
                      <TableRow key={ri}>{row.map((v, ci) => <TableCell key={ci}>{v === null ? "" : String(v)}</TableCell>)}</TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </Box>
          ) : null}
        </CardContent>
      </Card>
    </Box>
  );
}