import DataTable from "../components/DataTable";

// Generic list-report for simple entities driven by a config object.
const CONFIGS = {
  accounts: {
    title: "Accounts",
    path: "/v1/accounts",
    columns: [
      { key: "name", label: "Name" },
      { key: "currency", label: "Currency" },
      { key: "opening_balance", label: "Opening Balance" },
      { key: "mnemonic_id", label: "ID" },
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
      { key: "level", label: "Level" },
      { key: "mnemonic_id", label: "ID" },
    ],
  },
  "expense-categories": {
    title: "Expense Categories",
    path: "/v1/expense-categories",
    columns: [
      { key: "name", label: "Name" },
      { key: "level", label: "Level" },
      { key: "mnemonic_id", label: "ID" },
    ],
  },
  "cash-flow-items": {
    title: "Cash Flow Items",
    path: "/v1/cash-flow-items",
    columns: [
      { key: "name", label: "Name" },
      { key: "expected_amount", label: "Expected" },
      { key: "currency", label: "Currency" },
      { key: "mnemonic_id", label: "ID" },
    ],
  },
  investments: {
    title: "Investments",
    path: "/v1/investments",
    columns: [
      { key: "name", label: "Name" },
      { key: "symbol", label: "Symbol" },
      { key: "quantity", label: "Quantity" },
      { key: "current_value_cache", label: "Current Value" },
      { key: "currency", label: "Currency" },
    ],
  },
  budgets: {
    title: "Budgets",
    path: "/v1/budgets",
    columns: [
      { key: "name", label: "Name" },
      { key: "period_start", label: "Start" },
      { key: "period_end", label: "End" },
      { key: "base_currency", label: "Currency" },
      { key: "mnemonic_id", label: "ID" },
    ],
  },
  institutions: {
    title: "Institutions",
    path: "/v1/institutions",
    columns: [
      { key: "name", label: "Name" },
      { key: "swift_bic", label: "SWIFT/BIC" },
      { key: "website", label: "Website" },
      { key: "mnemonic_id", label: "ID" },
    ],
  },
  loans: {
    title: "Loans",
    path: "/v1/loans",
    columns: [
      { key: "name", label: "Name" },
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
      { key: "target_amount", label: "Target" },
      { key: "target_date", label: "Target Date" },
      { key: "currency", label: "Currency" },
    ],
  },
};

export default function EntityList({ entity }) {
  const cfg = CONFIGS[entity];
  if (!cfg) return <div>Unknown entity: {entity}</div>;
  return <DataTable title={cfg.title} path={cfg.path} columns={cfg.columns} />;
}