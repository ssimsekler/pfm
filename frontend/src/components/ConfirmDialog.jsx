// Reusable confirmation dialog (ADR #32: every UI state change is confirmed).
import { Dialog, Bar, Button, Text } from "@ui5/webcomponents-react";

export default function ConfirmDialog({
  open,
  title = "Please confirm",
  message = "Are you sure?",
  confirmText = "Confirm",
  cancelText = "Cancel",
  confirmDesign = "Emphasized",
  busy = false,
  onConfirm,
  onCancel,
}) {
  return (
    <Dialog
      open={open}
      headerText={title}
      onAfterClose={onCancel}
      footer={
        <Bar
          endContent={
            <>
              <Button design="Transparent" onClick={onCancel} disabled={busy}>
                {cancelText}
              </Button>
              <Button design={confirmDesign} onClick={onConfirm} disabled={busy}>
                {busy ? "Working…" : confirmText}
              </Button>
            </>
          }
        />
      }
    >
      <div style={{ padding: "0.5rem 0.25rem", maxWidth: "420px" }}>
        <Text>{message}</Text>
      </div>
    </Dialog>
  );
}