// Reusable confirmation dialog (MUI). Used for cancel-if-dirty, delete, and
// complex/destructive actions (ADR #32/#38).
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from "@mui/material";

export default function ConfirmDialog({
  open,
  title = "Please confirm",
  message = "Are you sure?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  confirmColor = "primary",
  busy = false,
  onConfirm,
  onCancel,
}) {
  return (
    <Dialog open={open} onClose={busy ? undefined : onCancel} maxWidth="xs" fullWidth>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText>{message}</DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} disabled={busy}>{cancelText}</Button>
        <Button onClick={onConfirm} variant="contained" color={confirmColor} disabled={busy}>
          {busy ? "Working…" : confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
}