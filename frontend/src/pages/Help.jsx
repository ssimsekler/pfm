// In-app Help / Wiki (A.2): concise guidance on the app's key concepts and flows,
// including categorization rules. Static content (no backend) rendered as
// collapsible sections so it's easy to scan.
import {
  Box, Typography, Accordion, AccordionSummary, AccordionDetails, Link, Divider, Chip, Stack,
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
          PFM tracks accounts, transactions, budgets, loans, investments and more.
          A typical setup order:
        </Typography>
        <Typography component="ol" sx={{ pl: 3 }}>
          <li>Create <b>Institutions</b> and <b>Accounts</b> (Money).</li>
          <li>Add <b>Partners</b>, <b>Beneficiaries</b> and <b>Categories</b> (Master Data).</li>
          <li>Record <b>Transactions</b>, or <b>Import</b> a statement and review it.</li>
          <li>Set up <b>Budgets</b>, <b>Recurring</b> items, <b>Loans</b> and <b>Investments</b>.</li>
          <li>Review <b>Reports</b> and the <b>Overview</b>.</li>
        </Typography>
      </>
    ),
  },
  {
    id: "categorization-rules",
    title: "Categorization rules",
    body: (
      <>
        <Typography paragraph>
          Rules automatically set a category / partner / beneficiary on transactions
          (e.g. during import). Manage them under <b>Configuration → Categorization Rules</b>.
        </Typography>
        <Typography paragraph>Each rule has:</Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li><b>Priority</b> — lower numbers run first; the first match wins.</li>
          <li><b>Conditions</b> (JSON) — e.g. <code>{`{"partner":"Netflix","amount_lt":100}`}</code>.</li>
          <li><b>Actions</b> (JSON) — e.g. <code>{`{"set_category":"Entertainment"}`}</code>.</li>
          <li><b>Enabled</b> — toggle without deleting.</li>
        </Typography>
        <Typography paragraph sx={{ mt: 1 }}>
          Rules are suggestions applied on the import validation screen — you always
          confirm before anything is written.
        </Typography>
      </>
    ),
  },
  {
    id: "policy-1",
    title: "Cash-flow items & Policy 1",
    body: (
      <>
        <Typography paragraph>
          A <b>Cash Flow Item</b> is an income/expense obligation (e.g. “Rent”) that can be
          fulfilled by one or more transactions. Use the per-row <b>Create transaction</b>
          action to materialize one.
        </Typography>
        <Typography paragraph>
          <b>Policy 1:</b> a transaction linked to a cash-flow item inherits that item’s
          category and <b>cannot be split</b>. Standalone transactions keep a free category
          and support multi-line splits.
        </Typography>
      </>
    ),
  },
  {
    id: "recurring",
    title: "Recurring items",
    body: (
      <>
        <Typography paragraph>
          Link a <b>Recurrence Profile</b> (Configuration) to a cash-flow item to schedule it.
          The <b>Recurring</b> page lists upcoming occurrences up to a horizon date that don’t
          yet have a transaction — create them with one click.
        </Typography>
        <Typography paragraph>
          Profiles support frequencies, a business-day rule, and a holiday calendar (with
          recurring weekends and explicit holidays) so “last working day” style rules work.
        </Typography>
      </>
    ),
  },
  {
    id: "transfers",
    title: "Transfers",
    body: (
      <Typography paragraph>
        Use <b>New Transfer</b> on the Transactions page to move money between two accounts.
        This creates two linked transactions (out + in). For cross-currency transfers, enter
        the received amount and currency on the other leg; the FX rate is derived.
      </Typography>
    ),
  },
  {
    id: "imports",
    title: "Importing statements",
    body: (
      <>
        <Typography paragraph>
          Upload a PDF/CSV/XLSX under <b>Imports</b>. Pick the statement’s <b>country</b> so
          dates and numbers are parsed correctly (day-first vs month-first, comma vs dot decimals).
        </Typography>
        <Typography paragraph>
          Rows land on a validation screen. Review them, then <b>Commit</b> into an account —
          duplicates are skipped and each transaction notes its source file.
        </Typography>
      </>
    ),
  },
  {
    id: "reporting-currency",
    title: "Reporting currency & FX",
    body: (
      <Typography paragraph>
        Transactions keep their own currency. Reports roll up in a configurable reporting
        currency (default <b>USD</b>) using FX rates with validity periods. Maintain rates under
        <b> Configuration → Currency Rates</b>; keep an open-ended period so a rate always exists.
      </Typography>
    ),
  },
  {
    id: "settings",
    title: "Settings & profile",
    body: (
      <Typography paragraph>
        <b>Settings</b> holds App Settings (including the LLM master switch), Entity Prefixes
        (mnemonic ID pad widths), and your profile (name, email, and date/number/time formats).
      </Typography>
    ),
  },
];

export default function Help() {
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
          <Chip key={s.id} label={s.title} component="a" href={`#help-${s.id}`} clickable size="small" />
        ))}
      </Stack>
      <Divider sx={{ mb: 2 }} />
      {SECTIONS.map((s) => (
        <Accordion key={s.id} id={`help-${s.id}`} defaultExpanded={s.id === "getting-started"}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1">{s.title}</Typography>
          </AccordionSummary>
          <AccordionDetails>{s.body}</AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
}