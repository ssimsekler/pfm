// Multi-line transaction split editor (MUI, ADR #33). Live "remaining" indicator;
// disabled when a Cash Flow Item is linked (Policy 1).
import {
  Box,
  Button,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Alert,
  Stack,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import ComboField from "./ComboField";

const CATEGORY_FIELD = { type: "ref", refEntity: "expense-categories" };
const BENEFICIARY_FIELD = { type: "ref", refEntity: "beneficiaries" };

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

export default function SplitEditor({ amount, rows, onChange, disabled }) {
  const total = rows.reduce((s, r) => s + toNum(r.amount), 0);
  const target = toNum(amount);
  const remaining = Number((target - total).toFixed(4));
  const balanced = Math.abs(remaining) < 0.00005;

  const update = (idx, patch) => onChange(rows.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  const addRow = () => onChange([...rows, { expense_category_id: "", beneficiary_id: "", amount: "" }]);
  const removeRow = (idx) => onChange(rows.filter((_, i) => i !== idx));

  return (
    <Box sx={{ mt: 2, pt: 1.5, borderTop: 1, borderColor: "divider" }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle2">Split lines</Typography>
        <Button size="small" startIcon={<AddIcon />} onClick={addRow} disabled={disabled}>Add line</Button>
      </Stack>

      {disabled ? (
        <Alert severity="info" sx={{ mb: 1 }}>
          Splitting is disabled when a Cash Flow Item is linked (Policy 1).
        </Alert>
      ) : null}

      {rows.length === 0 ? (
        <Typography variant="body2" color="text.secondary">No split lines.</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Category</TableCell>
              <TableCell>Beneficiary</TableCell>
              <TableCell sx={{ width: 140 }}>Amount</TableCell>
              <TableCell sx={{ width: 48 }} />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r, idx) => (
              <TableRow key={idx}>
                <TableCell>
                  <ComboField field={CATEGORY_FIELD} value={r.expense_category_id} onChange={(v) => update(idx, { expense_category_id: v })} disabled={disabled} />
                </TableCell>
                <TableCell>
                  <ComboField field={BENEFICIARY_FIELD} value={r.beneficiary_id} onChange={(v) => update(idx, { beneficiary_id: v })} disabled={disabled} />
                </TableCell>
                <TableCell>
                  <TextField type="number" size="small" fullWidth value={r.amount ?? ""} onChange={(e) => update(idx, { amount: e.target.value })} disabled={disabled} />
                </TableCell>
                <TableCell>
                  <IconButton size="small" onClick={() => removeRow(idx)} disabled={disabled}><DeleteIcon fontSize="small" /></IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {rows.length > 0 ? (
        <Stack direction="row" justifyContent="flex-end" spacing={3} sx={{ mt: 1 }}>
          <Typography variant="body2">Total: {total.toFixed(2)}</Typography>
          <Typography variant="body2" color={balanced ? "success.main" : "error.main"}>
            Remaining: {remaining.toFixed(2)}
          </Typography>
        </Stack>
      ) : null}

      {!balanced && rows.length > 0 ? (
        <Alert severity="warning" sx={{ mt: 1 }}>
          Split lines must sum exactly to the transaction amount ({target.toFixed(2)}) before saving.
        </Alert>
      ) : null}
    </Box>
  );
}