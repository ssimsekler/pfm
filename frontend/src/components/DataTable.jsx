// Reusable Fiori list-report table with a filter bar, search, and pagination.
import { useEffect, useState, useCallback } from "react";
import {
  Label,
  Input,
  Button,
  Bar,
  Title,
  Text,
  BusyIndicator,
  FlexBox,
  FlexBoxJustifyContent,
  FlexBoxAlignItems,
  MessageStrip,
} from "@ui5/webcomponents-react";
import { api } from "../api";

/**
 * columns: [{ key, label, render?(row) }]
 * path: e.g. "/v1/partners" (list endpoint returning {items,total,limit,offset} or an array)
 * filters: optional React node rendered in the filter bar (controlled by parent)
 * extraParams: object merged into the request
 */
export default function DataTable({
  title,
  path,
  columns,
  filters,
  extraParams = {},
  pageSize = 25,
  onRowClick,
  toolbar,
  refreshKey,
}) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { limit: pageSize, offset, ...extraParams };
      if (search) params.search = search;
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
  }, [path, offset, pageSize, search, JSON.stringify(extraParams), refreshKey]);

  useEffect(() => {
    load();
  }, [load]);

  const page = Math.floor(offset / pageSize) + 1;
  const pages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div>
      <Bar
        startContent={<Title level="H4">{title}</Title>}
        endContent={toolbar}
        style={{ marginBottom: "0.5rem" }}
      />
      <FlexBox
        alignItems={FlexBoxAlignItems.End}
        style={{ gap: "0.75rem", padding: "0.5rem 0", flexWrap: "wrap" }}
      >
        <div>
          <Label>Search</Label>
          <Input
            value={search}
            placeholder="Search…"
            onInput={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                setOffset(0);
                load();
              }
            }}
          />
        </div>
        {filters}
        <Button design="Emphasized" onClick={() => { setOffset(0); load(); }}>
          Go
        </Button>
      </FlexBox>

      {error && (
        <MessageStrip design="Negative" hideCloseButton style={{ margin: "0.5rem 0" }}>
          {error}
        </MessageStrip>
      )}

      <BusyIndicator active={loading} style={{ width: "100%" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.875rem",
          }}
        >
          <thead>
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  style={{
                    textAlign: "left",
                    padding: "0.5rem 0.75rem",
                    borderBottom: "2px solid var(--sapList_BorderColor, #d9d9d9)",
                    whiteSpace: "nowrap",
                  }}
                >
                  <Label>{c.label}</Label>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  style={{ padding: "1rem 0.75rem", textAlign: "center" }}
                >
                  <Text>No data</Text>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.uuid || row.code || JSON.stringify(row)}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  style={{
                    cursor: onRowClick ? "pointer" : "default",
                    borderBottom: "1px solid var(--sapList_BorderColor, #ededed)",
                  }}
                >
                  {columns.map((c) => (
                    <td key={c.key} style={{ padding: "0.5rem 0.75rem" }}>
                      {c.render ? c.render(row) : <Text>{fmt(row[c.key])}</Text>}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </BusyIndicator>

      <FlexBox
        justifyContent={FlexBoxJustifyContent.SpaceBetween}
        alignItems={FlexBoxAlignItems.Center}
        style={{ padding: "0.5rem 0" }}
      >
        <Text>{total} item(s)</Text>
        <FlexBox alignItems={FlexBoxAlignItems.Center} style={{ gap: "0.5rem" }}>
          <Button
            icon="navigation-left-arrow"
            disabled={offset <= 0}
            onClick={() => setOffset(Math.max(0, offset - pageSize))}
          />
          <Text>
            Page {page} / {pages}
          </Text>
          <Button
            icon="navigation-right-arrow"
            disabled={page >= pages}
            onClick={() => setOffset(offset + pageSize)}
          />
        </FlexBox>
      </FlexBox>
    </div>
  );
}

function fmt(v) {
  if (v === null || v === undefined) return "";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  return String(v);
}