// Config-driven CRUD list report → reusable EntityManager (MUI).
import { Typography } from "@mui/material";
import EntityManager from "../components/EntityManager";
import { ENTITIES } from "../entities";

export default function EntityList({ entity }) {
  const cfg = ENTITIES[entity];
  if (!cfg) {
    return <Typography>Unknown entity: {entity}</Typography>;
  }
  return <EntityManager entity={entity} cfg={cfg} />;
}