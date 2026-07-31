// List table using MUI DataGrid: built-in column filtering, sorting, pagination
// (satisfies #20). Server-side search + extraParams (structured filters) are
// merged into the request; client-side quick filter is also available.
import { useEffect, useState, useCallback, useMemo } from "react";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { Box, Alert } from "@mui/material";
import { api } from "../api";
import { formatMoney, formatDate, formatDateTime } from "../format";

function fmtCell(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return v;
}

// Bug 21: money/date columns render using the resolved display formats
// (profile → settings → defaults). Set `money`, `date` or `datetime` on a column.
function fmtMoney(v) {
  return formatMoney(v);
}

export default function DataTable({
  path,
  columns,
  extraParams = {},
  pageSize = 25,
  refreshKey,
  actions, // optional (row) => ReactNode
  getRowId,
}) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [model, setModel] = useState({ page: 0, pageSize });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: model.pageSize, offset: model.page * model.pageSize, ...extraParams };
      const data = await api.get(path, params);
      if (Array.isArray(data)) {
        setRows(data);
        setTotal(data.length);
      } else {
        setRows(data.items || []);
        setTotal(data.total || 0);
      }
    } catch (e) {
      setError(e.message);
      setRows([]);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, model.page, model.pageSize, JSON.stringify(extraParams), refreshKey]);

  useEffect(() => {
    load();
  }, [load]);

  const gridColumns = useMemo(() => {
    const base = columns.map((c) => ({
      field: c.key,
      headerName: c.label,
      flex: 1,
      minWidth: 120,
      sortable: true,
      align: c.money ? "right" : undefined,
      headerAlign: c.money ? "right" : undefined,
      valueGetter: c.render
        ? undefined
        : (value, row) => {
            const raw = row[c.key];
            if (c.money) return fmtMoney(raw);
            if (c.date) return formatDate(raw);
            if (c.datetime) return formatDateTime(raw);
            return fmtCell(raw);
          },
      renderCell: c.render ? (p) => c.render(p.row) : undefined,
    }));
    if (actions) {
      base.push({
        field: "__actions",
        headerName: "Actions",
        sortable: false,
        filterable: false,
        width: 120,
        renderCell: (p) => actions(p.row),
      });
    }
    return base;
  }, [columns, actions]);

  const rowId = getRowId || ((r) => r.uuid || r.code || r.mnemonic_id || JSON.stringify(r));

  return (
    <Box>
      {error ? <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert> : null}
      <DataGrid
        autoHeight
        rows={rows}
        columns={gridColumns}
        getRowId={rowId}
        loading={loading}
        rowCount={total}
        paginationMode="server"
        paginationModel={model}
        onPaginationModelChange={setModel}
        pageSizeOptions={[10, 25, 50, 100]}
        disableRowSelectionOnClick
        slots={{ toolbar: GridToolbar }}
        slotProps={{ toolbar: { showQuickFilter: true, printOptions: { disableToolbarButton: true } } }}
        sx={{ bgcolor: "background.paper" }}
      />
    </Box>
  );
}