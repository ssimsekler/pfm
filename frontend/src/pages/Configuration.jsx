// Configuration page (MUI): code values + config entities (full CRUD).
// Holiday calendars get a row action to open the day/weekend editor (A.1).
import { useState } from "react";
import { Box, Typography, Stack, Tooltip } from "@mui/material";
import EventIcon from "@mui/icons-material/Event";
import CodeValueManager from "../components/CodeValueManager";
import EntityManager from "../components/EntityManager";
import HolidayDaysDialog from "../components/HolidayDaysDialog";
import { ENTITIES } from "../entities";

const CONFIG_ENTITIES = [
  "llm-providers",
  "integration-endpoints",
  "categorization-rules",
  "currency-rates",
];

export default function Configuration() {
  const [calendar, setCalendar] = useState(null);

  const holidayActions = [
    {
      icon: <EventIcon fontSize="small" />,
      tooltip: "Edit holidays & weekend",
      onClick: (row) => setCalendar(row),
    },
  ];

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Configuration</Typography>
      <Stack spacing={3}>
        <CodeValueManager />
        {CONFIG_ENTITIES.map((key) => (
          <EntityManager key={key} entity={key} cfg={ENTITIES[key]} />
        ))}
        <EntityManager
          entity="holiday-calendars"
          cfg={ENTITIES["holiday-calendars"]}
          rowActions={holidayActions}
        />
      </Stack>

      {calendar ? (
        <HolidayDaysDialog calendar={calendar} onClose={() => setCalendar(null)} />
      ) : null}
    </Box>
  );
}