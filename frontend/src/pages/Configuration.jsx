// Configuration page (MUI): code values + config entities (full CRUD).
import { Box, Typography, Stack } from "@mui/material";
import CodeValueManager from "../components/CodeValueManager";
import EntityManager from "../components/EntityManager";
import { ENTITIES } from "../entities";

const CONFIG_ENTITIES = [
  "llm-providers",
  "integration-endpoints",
  "categorization-rules",
  "currency-rates",
  "holiday-calendars",
];

export default function Configuration() {
  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Configuration</Typography>
      <Stack spacing={3}>
        <CodeValueManager />
        {CONFIG_ENTITIES.map((key) => (
          <EntityManager key={key} entity={key} cfg={ENTITIES[key]} />
        ))}
      </Stack>
    </Box>
  );
}