// Config-driven CRUD list report. Delegates to the reusable EntityManager,
// which provides list + create/edit/delete from the central entity registry.
import { Title } from "@ui5/webcomponents-react";
import EntityManager from "../components/EntityManager";
import { ENTITIES } from "../entities";

export default function EntityList({ entity }) {
  const cfg = ENTITIES[entity];
  if (!cfg) {
    return (
      <div>
        <Title level="H3">Unknown entity</Title>
        <p>No configuration for &quot;{entity}&quot;.</p>
      </div>
    );
  }
  return <EntityManager entity={entity} cfg={cfg} />;
}