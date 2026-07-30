import { Title } from "@ui5/webcomponents-react";
import DataTable from "../components/DataTable";

// Config-driven list reports. Each entity maps to a list endpoint + columns.
const ENTITIES = {
  accounts: {
    title: "Accounts",
    path: "/v1/accounts",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "currency", label: "Currency" },
      { key: "opening_balance", label: "Opening Balance" },
      { key: "is_active", label: "Active" },
    ],
  },
  partners: {
    title: "Partners",
    path: "/v1/partners",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "description", label: "Description" },
    ],
  },
  beneficiaries: {
    title: "Beneficiaries",
    path: "/v1/beneficiaries",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "level", label: "Level" },
    ],
  },
  "expense-categories": {
    title: "Expense Categories",
    path: "/v1/expense-categories",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "level", label: "Level" },
    ],
  },
  "cash-flow-items": {
    title: "Cash Flow Items",
    path: "/v1/cash-flow-items",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "expected_amount", label: "Expected Amount" },
      { key: "currency", label: "Currency" },
    ],
  },
  investments: {
    title: "Investments",
    path: "/v1/investment-holdings",
    columns: [
      { key: "name", label: "Name" },
      { key: "symbol", label: "Symbol" },
      { key: "quantity", label: "Quantity" },
      { key: "current_value_cache", label: "Current Value" },
      { key: "currency", label: "Currency" },
    ],
  },
  loans: {
    title: "Loans",
    path: "/v1/loans",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "principal", label: "Principal" },
      { key: "interest_rate", label: "Rate %" },
      { key: "term_months", label: "Term (mo)" },
      { key: "currency", label: "Currency" },
    ],
  },
  "installment-plans": {
    title: "Installment Plans",
    path: "/v1/installment-plans",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "total_amount", label: "Total" },
      { key: "installment_count", label: "Count" },
      { key: "currency", label: "Currency" },
    ],
  },
  goals: {
    title: "Goals",
    path: "/v1/goals",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "target_amount", label: "Target" },
      { key: "target_date", label: "Target Date" },
      { key: "currency", label: "Currency" },
    ],
  },
  budgets: {
    title: "Budgets",
    path: "/v1/budgets",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "period_start", label: "From" },
      { key: "period_end", label: "To" },
      { key: "base_currency", label: "Currency" },
    ],
  },
  institutions: {
    title: "Institutions",
    path: "/v1/institutions",
    columns: [
      { key: "name", label: "Name" },
      { key: "mnemonic_id", label: "ID" },
      { key: "swift_bic", label: "SWIFT/BIC" },
      { key: "website", label: "Website" },
    ],
  },
};

export default function EntityList({ entity }) {
  const cfg = ENTITIES[entity];
  if (!cfg) {
    return (
      <div>
        <Title level="H3">Unknown entity</Title>
        <p>No list configuration for &quot;{entity}&quot;.</p>
      </div>
    );
  }
  return (
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>{cfg.title}</Title>
      <DataTable title={cfg.title} path={cfg.path} columns={cfg.columns} />
    </div>
  );
}