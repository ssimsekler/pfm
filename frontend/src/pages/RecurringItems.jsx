// Recurring cash-flow items (#19): list pending occurrences up to a horizon date
// (cash-flow items with a recurrence profile whose due dates have no transaction
// yet) and materialize any of them into a transaction.
// Backend: GET /v1/recurring/pending?until=  and  POST /v1/recurring/materialize
// (via MaterializeDialog). Recurrence profiles are managed under Configuration.
import { useCallback, useEffect, useState } from "react";
import {
  Box, Card, CardHeader, CardContent, Typography, Stack, Table, TableBody, TableCell,
  TableHead, TableRow, Button, Alert, Snackbar, Chip,
} from "@mui/material";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import dayjs from "dayjs";
import { api } from "../api";
import MaterializeDialog from "../components/MaterializeDialog";

export default function RecurringItems() {
  const [until, setUntil] = useState(dayjs().add(3, "month").format("YYYY-MM-DD"));
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [msg, setMsg] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const data = await api.get("/v1/recurring/pending", { until });
      setRows(data || []);
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  }, [until]);

  useEffect(() => { load(); }, [load]);

  // MaterializeDialog expects an `item` with uuid/name/expected_amount/currency.
  const openMaterialize = (r) => setSelected({
    uuid: r.cash_flow_item_id,
    name: r.cash_flow_item_name,
    expected_amount: r.expected_amount,
    currency: r.currency,
    _due: r.due_date,
  });

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Recurring</Typography>
      <Card>
        <CardHeader
          title="Pending occurrences"
          subheader="Recurring cash-flow items due up to the horizon with no transaction yet"
        />
        <CardContent>
          {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}
          <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2, flexWrap: "wrap" }}>
            <DatePicker label="Horizon (until)" value={until ? dayjs(until) : null}
              onChange={(d) => setUntil(d ? d.format("YYYY-MM-DD") : "")}
              slotProps={{ textField: { size: "small" } }} />
            <Button variant="outlined" onClick={load} disabled={loading}>Refresh</Button>
            <Chip label={`${rows.length} pending`} size="small" />
          </Stack>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Item</TableCell><TableCell>Due date</TableCell>
                <TableCell align="right">Expected</TableCell><TableCell>Currency</TableCell><TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((r, i) => (
                <TableRow key={`${r.cash_flow_item_id}-${r.due_date}-${i}`} hover>
                  <TableCell>{r.cash_flow_item_name}</TableCell>
                  <TableCell>{r.due_date}</TableCell>
                  <TableCell align="right">{r.expected_amount ?? ""}</TableCell>
                  <TableCell>{r.currency || ""}</TableCell>
                  <TableCell align="right">
                    <Button size="small" startIcon={<ReceiptLongIcon fontSize="small" />}
                      onClick={() => openMaterialize(r)}>Create transaction</Button>
                  </TableCell>
                </TableRow>
              ))}
              {rows.length === 0 && !loading ? (
                <TableRow><TableCell colSpan={5}>
                  <Typography color="text.secondary">
                    Nothing pending. Link a recurrence profile to a cash-flow item (Cash Flow Items →
                    Recurrence Profile) and set the horizon further out.
                  </Typography>
                </TableCell></TableRow>
              ) : null}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {selected ? (
        <MaterializeDialog
          item={selected}
          onClose={() => setSelected(null)}
          onDone={() => { setSelected(null); setMsg("Transaction created from recurring item."); load(); }}
        />
      ) : null}

      <Snackbar open={Boolean(msg)} autoHideDuration={5000} onClose={() => setMsg(null)}>
        <Alert severity="success" onClose={() => setMsg(null)}>{msg}</Alert>
      </Snackbar>
    </Box>
  );
}