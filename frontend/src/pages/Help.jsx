// In-app Help / Wiki (Session 742).
//  - Bug 15: section chips expand the target Accordion AND scroll to it (no more
//    dead hash-anchor links behind the hash router).
//  - Bug 16: expanded categorization-rules guidance with condition/action keys.
//  - Added SMTP/Yahoo (8), loan/installment link (10/11), goals (19), formats (21),
//    import intelligence (17), multi-account CSV (18), cash projection (23).
import { useRef, useState } from "react";
import {
  Box, Typography, Accordion, AccordionSummary, AccordionDetails, Divider, Chip, Stack, Alert,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

const SECTIONS = [
  {
    id: "getting-started",
    title: "Getting started",
    body: (
      <>
        <Typography paragraph>
          PFM tracks accounts, transactions, budgets, loans, investments and more. Typical order:
        </Typography>
        <Typography component="ol" sx={{ pl: 3 }}>
          <li>Create <b>Institutions</b> and <b>Accounts</b>.</li>
          <li>Add <b>Partners</b>, <b>Beneficiaries</b> and <b>Categories</b>.</li>
          <li>Record <b>Transactions</b>, or <b>Import</b> a statement and review it.</li>
          <li>Set up <b>Budgets</b>, <b>Recurring</b> items, <b>Loans</b> and <b>Investments</b>.</li>
          <li>Review <b>Reports</b> and the <b>Overview</b>.</li>
        </Typography>
        <Typography paragraph sx={{ mt: 1 }}>
          The left menu is <b>collapsible</b> — use the menu button in the top bar to shrink it to
          icons with tooltips. Beneficiaries and Categories can be viewed as a <b>tree</b> or table.
        </Typography>
      </>
    ),
  },
  {
    id: "categorization-rules",
    title: "Categorization rules (detailed)",
    body: (
      <>
        <Typography paragraph>
          Rules automatically set a <b>category</b>, <b>partner</b> and/or <b>beneficiary</b> on
          transactions during <b>import</b>. Manage them under
          <b> Configuration → Categorization Rules</b> — each has a <b>priority</b>, a
          <b> conditions</b> JSON, an <b>actions</b> JSON and an <b>enabled</b> flag.
        </Typography>
        <Typography variant="subtitle2" sx={{ mt: 1 }}>How matching works</Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li>Lower <b>priority</b> runs first; the <b>first matching rule wins</b>.</li>
          <li>All keys inside one rule's conditions must match (AND).</li>
          <li>Text matches are case-insensitive substring matches.</li>
        </Typography>
        <Typography variant="subtitle2" sx={{ mt: 1 }}>Condition keys</Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li><code>description_contains</code>, <code>partner</code></li>
          <li><code>amount_lt</code>, <code>amount_gt</code>, <code>amount_eq</code></li>
          <li><code>direction</code> (debit/credit), <code>currency</code></li>
        </Typography>
        <Typography variant="subtitle2" sx={{ mt: 1 }}>Action keys</Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li><code>set_category</code>, <code>set_partner</code>, <code>set_beneficiary</code></li>
        </Typography>
        <Typography variant="subtitle2" sx={{ mt: 1 }}>Examples</Typography>
        <Box sx={{ pl: 1 }}>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{`{"partner":"Netflix","amount_lt":100} -> {"set_category":"Entertainment"}
{"description_contains":"SALARY","direction":"credit"} -> {"set_category":"Salary","set_beneficiary":"Self"}
{"description_contains":"ADNOC"} -> {"set_category":"Fuel","set_partner":"ADNOC"}`}</pre>
        </Box>
        <Alert severity="info" sx={{ mt: 2 }}>
          Rules produce <b>suggestions</b> on the import validation screen — you confirm before
          anything is written. Accepted mappings are <b>learned</b> and pre-filled next time.
        </Alert>
      </>
    ),
  },
  {
    id: "import-intelligence",
    title: "Import intelligence & partner mapping (17)",
    body: (
      <>
        <Typography paragraph>On import, each row is mapped in this order:</Typography>
        <Typography component="ol" sx={{ pl: 3 }}>
          <li><b>Categorization rules</b> — deterministic and auditable.</li>
          <li><b>Mapping memory</b> — most-frequently accepted source-text → partner/category.</li>
          <li><b>LLM assist</b> — only if the <b>LLM master switch</b> is on (Settings); suggestion only.</li>
        </Typography>
        <Typography paragraph>
          <b>Partners/suppliers</b> come from the counterparty text via rules and memory; confirming
          a row records the mapping so it improves over time.
        </Typography>
      </>
    ),
  },
  {
    id: "generic-csv",
    title: "Generic multi-account CSV import (18)",
    body: (
      <>
        <Typography paragraph>
          A generic CSV can carry transactions for <b>different accounts</b>, deduced per row from
          <code> account</code>, <code>iban</code> or <code>account_number</code>. Unresolved rows
          fall back to the default account chosen at commit time. Pick the statement's
          <b> country</b> so dates/numbers parse correctly.
        </Typography>
      </>
    ),
  },
  {
    id: "policy-1",
    title: "Cash-flow items & Policy 1 (14)",
    body: (
      <>
        <Typography paragraph>
          A <b>Cash Flow Item</b> is an obligation fulfilled by one or more transactions. Use the
          per-row <b>Create transaction</b> action to materialize one.
        </Typography>
        <Typography paragraph>
          <b>Policy 1:</b> a transaction linked to an item inherits its category (and
          <b> beneficiary</b>, if set) and cannot be split. The beneficiary is pre-filled but stays
          editable. You get a success confirmation on save.
        </Typography>
      </>
    ),
  },
  {
    id: "installments-loans",
    title: "Loans, installments & the transaction link (10, 11)",
    body: (
      <>
        <Typography paragraph>
          Creating a <b>Loan</b> or <b>Investment</b> auto-creates a typed <b>backing account</b>.
          Open <b>Schedule &amp; payments</b> to generate/import a schedule and record payments.
          Recording a payment <b>creates a transaction</b> and stores its id on the schedule row
          (<code>linked_txn_id</code>) — that is the installment↔transaction link.
        </Typography>
        <Typography paragraph>
          CSV columns: installments <code>seq, due_date, amount</code>; loans
          <code> period, due_date, principal_portion, interest_portion, balance</code>.
        </Typography>
      </>
    ),
  },
  {
    id: "goals",
    title: "Goals & transactions (19)",
    body: (
      <>
        <Typography paragraph>Goals link to transactions and report progress:</Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li><b>Save to target</b> — tag transactions with the goal; progress = tagged sum vs. target.</li>
          <li><b>Cap expense</b> — category + period + limit; e.g. keep fuel under 1000/month.</li>
        </Typography>
        <Typography paragraph>Progress: <code>GET /v1/goals/&#123;id&#125;/progress</code>.</Typography>
      </>
    ),
  },
  {
    id: "recurring",
    title: "Recurring items",
    body: (
      <Typography paragraph>
        Link a <b>Recurrence Profile</b> (Configuration) to a cash-flow item. The <b>Recurring</b>
        page lists upcoming occurrences without a transaction — create them with one click.
        Profiles support frequencies, a business-day rule and a holiday calendar.
      </Typography>
    ),
  },
  {
    id: "transfers",
    title: "Transfers",
    body: (
      <Typography paragraph>
        Use <b>New Transfer</b> on Transactions to move money between two accounts (creates two
        linked legs). For cross-currency transfers, enter the received amount/currency on the other
        leg; the FX rate is derived.
      </Typography>
    ),
  },
  {
    id: "budgets-projection",
    title: "Budgets, variance & cash projection (23)",
    body: (
      <>
        <Typography paragraph>
          A <b>budget line</b> is defined by <b>either</b> a Cash Flow Item <b>or</b> a
          Category + Direction (not both — the item already carries its own category/direction).
        </Typography>
        <Typography paragraph>
          <b>Reports → Cash Projection</b> takes a <b>Budget</b> and a number of <b>months</b> and
          charts month-end <b>cash</b>, <b>investments</b>, <b>loans</b> and <b>net</b> position for
          the period (<code>GET /v1/reports/cash-projection?budget_id=&amp;months=</code>).
          <b> Budget vs. Actual</b> and <b>Monthly Trend</b> charts are also available.
        </Typography>
      </>
    ),
  },
  {
    id: "reporting-currency",
    title: "Reporting currency & FX (20)",
    body: (
      <Typography paragraph>
        Transactions keep their own currency; reports roll up in a configurable reporting currency
        (default USD) using FX rates with validity periods. Maintain rates under
        <b> Configuration → Currency Rates</b>, and use <b>Refresh from source</b> to fetch rates
        from the configured endpoint. Keep an open-ended period so a rate always exists.
      </Typography>
    ),
  },
  {
    id: "valuation",
    title: "Investment valuation history (26)",
    body: (
      <Typography paragraph>
        Open <b>Valuation history</b> on an investment to see the trend, add a manual value, or
        <b> Refresh from source</b> for a chosen <b>As of</b> date. If a value exists for that date
        it is overwritten; otherwise a new point is inserted. Manual-only assets return a clear
        message instead of a fetch error.
      </Typography>
    ),
  },
  {
    id: "smtp",
    title: "Email / SMTP (incl. Yahoo) (8)",
    body: (
      <>
        <Typography paragraph>
          Configure outgoing email under <b>Settings → Email (SMTP)</b>. Set the discrete
          <code> smtp.*</code> keys: host, port, username, password, from, default recipient, and
          security (<code>none</code> / <code>starttls</code> / <code>ssl</code>). Turn on
          <code> smtp.enabled</code> and use <b>Send test email</b> to verify.
        </Typography>
        <Typography variant="subtitle2" sx={{ mt: 1 }}>Yahoo example</Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li>Host <code>smtp.mail.yahoo.com</code></li>
          <li>Port <code>465</code> with security <code>ssl</code> (or <code>587</code> + <code>starttls</code>)</li>
          <li>Username: your Yahoo address; Password: a Yahoo <b>app password</b> (not your login password)</li>
        </Typography>
        <Typography paragraph sx={{ mt: 1 }}>
          Any provider works with the same fields. Reminders and notifications use these settings.
        </Typography>
      </>
    ),
  },
  {
    id: "settings",
    title: "Settings, LLM switch & profile (6, 7, 21)",
    body: (
      <>
        <Typography paragraph>
          <b>Settings</b> holds App Settings, Email (SMTP), Entity Prefixes (mnemonic ID pad widths)
          and your profile. There is a single LLM switch, <code>llm.master_enabled</code> — the
          master kill-switch that gates all LLM features (import assist, etc.); the old duplicate
          <code> llm.enabled</code> key was removed.
        </Typography>
        <Typography paragraph>
          <b>Display formats (Bug 21):</b> dates, times and numbers use your <b>profile</b>
          preference first; otherwise the application default from settings
          (<code>format.date</code>, <code>format.time</code>, <code>format.number</code>);
          otherwise the built-in defaults <code>yyyy-MM-dd</code>, <code>HH:mm</code> and
          <code> 1,234.56</code>. Money always shows 2 decimals.
        </Typography>
      </>
    ),
  },
  {
    id: "llm",
    title: "LLM providers & failover (New-2)",
    body: (
      <Typography paragraph>
        Configure providers under <b>Configuration → LLM Providers</b>. Each has a <b>priority</b>
        (lower is tried first) and an <b>enabled</b> flag. Gated by the master switch, the gateway
        tries providers in priority order and <b>fails over</b> to the next enabled one if a call
        fails or a provider is disabled.
      </Typography>
    ),
  },
];

export default function Help() {
  const refs = useRef({});
  const [expanded, setExpanded] = useState("getting-started");

  // Bug 15: expand the target section and smooth-scroll to it (no navigation).
  const jump = (id) => {
    setExpanded(id);
    // Wait a tick so the Accordion is expanded before scrolling.
    setTimeout(() => {
      const el = refs.current[id];
      if (el && el.scrollIntoView) el.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 60);
  };

  return (
    <Box>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
        <HelpOutlineIcon color="primary" />
        <Typography variant="h5">Help &amp; Wiki</Typography>
      </Stack>
      <Typography color="text.secondary" paragraph>
        Quick guidance on the main concepts and flows. Jump to a section:
      </Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mb: 2, gap: 1 }}>
        {SECTIONS.map((s) => (
          <Chip key={s.id} label={s.title} onClick={() => jump(s.id)} clickable size="small" />
        ))}
      </Stack>
      <Divider sx={{ mb: 2 }} />
      {SECTIONS.map((s) => (
        <Accordion
          key={s.id}
          expanded={expanded === s.id}
          onChange={(e, isExp) => setExpanded(isExp ? s.id : false)}
          ref={(el) => { refs.current[s.id] = el; }}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">{s.title}</Typography>
          </AccordionSummary>
          <AccordionDetails>{s.body}</AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}
