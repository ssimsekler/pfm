// Budget lines editor (#6): manage lines under a budget and show variance.
// Backend: GET/POST/DELETE /v1/budgets/{id}/lines, GET /v1/budgets/{id}/variance.
import { useCallback, useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, Button, Stack, Table, TableBody,
  TableCell, TableHead, TableRow, IconButton, TextField, Alert, Box, Typography, Divider, Tooltip,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import AssessmentIcon from "@mui/icons-material/Assessment";
import { api } from "../api";
import ComboField from "./ComboField";
import ConfirmDialog from "./ConfirmDialog";

const CATEGORY_FIELD = { type: "ref", refEntity: "expense-categories" };
const CFI_FIELD = { type: "ref", refEntity: "cash-flow-items" };
const DIRECTION_FIELD = { type: "codeValue", listKey: "flow_type" };

export default function BudgetLinesDialog({ budget, onClose }) {
  const [lines, setLines] = useState([]);
  const [draft, setDraft] = useState({ expense_category_id: "", cash_flow_item_id: "", direction_cv_id: "", expected_amount: "" });
  const [variance, setVariance] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [deleteId, setDeleteId] = useState(null);

  const load = useCallback(async () => {
    const rows = await api.get(`/v1/budgets/${budget.uuid}/lines`).catch(() => []);
    setLines(rows || []);
  }, [budget.uuid]);

  useEffect(() => { load(); }, [load]);

  const addLine = async () => {
    if (!draft.expected_amount) { setError("Enter an expected amount."); return; }
    setBusy(true); setError(null);
    try {
      await api.post(`/v1/budgets/${budget.uuid}/lines`, {
        expense_category_id: draft.expense_category_id || null,
        cash_flow_item_id: draft.cash_flow_item_id || null,
        direction_cv_id: draft.direction_cv_id || null,
        expected_amount: Number(draft.expected_amount),
      });
      setDraft({ expense_category_id: "", cash_flow_item_id: "", direction_cv_id: "", expected_amount: "" });
      load();
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  const doDelete = async () => {
    setBusy(true); setError(null);
    try {
      await api.del(`/v1/budgets/${budget.uuid}/lines/${deleteId}`);
      setDeleteId(null);
      load();
    } catch (e) { setDeleteId(null); setError(e.message); } finally { setBusy(false); }
  };

  const loadVariance = async () => {
    setError(null);
    const v = await api.get(`/v1/budgets/${budget.uuid}/variance`).catch((e) => { setError(e.message); return null; });
    setVariance(v);
  };

  return (
    <Dialog open onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Budget lines — {budget.name}</DialogTitle>
      <DialogContent dividers>
        {error ? <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert> : null}

        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Category</TableCell><TableCell>Cash Flow Item</TableCell>
              <TableCell>Direction</TableCell><TableCell align="right">Expected</TableCell><TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {lines.map((l) => (
              <TableRow key={l.uuid} hover>
                <TableCell>{l.expense_category_id || ""}</TableCell>
                <TableCell>{l.cash_flow_item_id || ""}</TableCell>
                <TableCell>{l.direction_cv_id || ""}</TableCell>
                <TableCell align="right">{l.expected_amount}</TableCell>
                <TableCell align="right">
                  <IconButton size="small" color="error" onClick={() => setDeleteId(l.uuid)}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
            {lines.length === 0 ? <TableRow><TableCell colSpan={5}><Typography color="text.secondary">No lines yet.</Typography></TableCell></TableRow> : null}
          </TableBody>
        </Table>

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2" sx={{ mb: 1 }}>Add a line</Typography>
        <Stack direction="row" spacing={1.5} alignItems="center" sx={{ flexWrap: "wrap" }}>
          <Box sx={{ minWidth: 180 }}><ComboField field={CATEGORY_FIELD} value={draft.expense_category_id} onChange={(v) => setDraft({ ...draft, expense_category_id: v })} label="Category" /></Box>
          <Box sx={{ minWidth: 180 }}><ComboField field={CFI_FIELD} value={draft.cash_flow_item_id} onChange={(v) => setDraft({ ...draft, cash_flow_item_id: v })} label="Cash Flow Item" /></Box>
          <Box sx={{ minWidth: 150 }}><ComboField field={DIRECTION_FIELD} value={draft.direction_cv_id} onChange={(v) => setDraft({ ...draft, direction_cv_id: v })} label="Direction" /></Box>
          <TextField label="Expected" type="number" size="small" value={draft.expected_amount} onChange={(e) => setDraft({ ...draft, expected_amount: e.target.value })} sx={{ width: 130 }} />
          <Button variant="contained" startIcon={<AddIcon />} onClick={addLine} disabled={busy}>Add</Button>
        </Stack>

        <Divider sx={{ my: 2 }} />
        <Stack direction="row" spacing={2} alignItems="center">
          <Button startIcon={<AssessmentIcon />} onClick={loadVariance}>Compute variance</Button>
          {variance ? (
            <Typography variant="body2">
              Expected {variance.total_expected} · Actual {variance.total_actual} · Variance {variance.total_variance} ({variance.reporting_currency})
            </Typography>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>

      <ConfirmDialog
        open={Boolean(deleteId)}
        title="Delete line?"
        message="Remove this budget line?"
        confirmText="Delete"
        confirmColor="error"
        busy={busy}
        onConfirm={doDelete}
        onCancel={() => setDeleteId(null)}
      />
    </Dialog>
  );
}