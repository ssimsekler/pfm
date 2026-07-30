import { useEffect, useState } from "react";
import {
  Title,
  Card,
  CardHeader,
  Select,
  Option,
  Table,
  TableColumn,
  TableRow,
  TableCell,
  Label,
  Text,
  FlexBox,
  FlexBoxWrap,
  BusyIndicator,
} from "@ui5/webcomponents-react";
import { api } from "../api";
import DataTable from "../components/DataTable";

export default function Configuration() {
  const [codeLists, setCodeLists] = useState([]);
  const [selectedList, setSelectedList] = useState("");
  const [values, setValues] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const cls = await api.get("/v1/code-lists").catch(() => []);
      setCodeLists(cls);
      if (cls.length) {
        setSelectedList(cls[0].list_key);
      }
      setLoading(false);
    })();
  }, []);

  useEffect(() => {
    if (!selectedList) return;
    api.get(`/v1/code-lists/${selectedList}/values`).then(setValues).catch(() => setValues([]));
  }, [selectedList]);

  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Configuration</Title>

      <FlexBox wrap={FlexBoxWrap.Wrap} style={{ gap: "1rem" }}>
        <Card style={{ width: "560px" }} header={<CardHeader titleText="Code Lists (value help)" />}>
          <div style={{ padding: "1rem" }}>
            <BusyIndicator active={loading} style={{ width: "100%" }}>
              <Label>List</Label>
              <Select onChange={(e) => setSelectedList(e.detail.selectedOption.dataset.key)}>
                {codeLists.map((cl) => (
                  <Option key={cl.list_key} data-key={cl.list_key} selected={cl.list_key === selectedList}>
                    {cl.list_key}
                  </Option>
                ))}
              </Select>
              <Table
                style={{ marginTop: "0.75rem" }}
                columns={[
                  <TableColumn key="c"><Label>Code</Label></TableColumn>,
                  <TableColumn key="l"><Label>Label</Label></TableColumn>,
                  <TableColumn key="d"><Label>Default</Label></TableColumn>,
                  <TableColumn key="a"><Label>Active</Label></TableColumn>,
                ]}
              >
                {values.map((v) => (
                  <TableRow key={v.uuid}>
                    <TableCell><Text>{v.code}</Text></TableCell>
                    <TableCell><Text>{v.label}</Text></TableCell>
                    <TableCell><Text>{v.is_default ? "✓" : ""}</Text></TableCell>
                    <TableCell><Text>{v.is_active ? "✓" : ""}</Text></TableCell>
                  </TableRow>
                ))}
              </Table>
            </BusyIndicator>
          </div>
        </Card>
      </FlexBox>

      <div style={{ marginTop: "1.5rem" }}>
        <DataTable
          title="LLM Providers"
          path="/v1/llm-providers"
          columns={[
            { key: "name", label: "Name" },
            { key: "model", label: "Model" },
            { key: "base_url", label: "Base URL" },
            { key: "enabled", label: "Enabled" },
          ]}
        />
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <DataTable
          title="Integration Endpoints"
          path="/v1/integration-endpoints"
          columns={[
            { key: "scenario_key", label: "Scenario" },
            { key: "provider_name", label: "Provider" },
            { key: "base_url", label: "Base URL" },
            { key: "enabled", label: "Enabled" },
          ]}
        />
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <DataTable
          title="Currency Rates"
          path="/v1/currency-rates"
          columns={[
            { key: "base_ccy", label: "Base" },
            { key: "quote_ccy", label: "Quote" },
            { key: "rate", label: "Rate" },
            { key: "begin_date", label: "From" },
            { key: "end_date", label: "To" },
          ]}
        />
      </div>

      <div style={{ marginTop: "1.5rem" }}>
        <DataTable
          title="Holiday Calendars"
          path="/v1/holiday-calendars"
          columns={[
            { key: "name", label: "Name" },
            { key: "mnemonic_id", label: "ID" },
            { key: "description", label: "Description" },
          ]}
        />
      </div>
    </div>
  );
}