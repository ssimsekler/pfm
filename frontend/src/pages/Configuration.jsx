// Configuration page: full CRUD for config data (ADR #32/#34).
//   - Code values via CodeValueManager (respects system-locked lists).
//   - LLM providers, integration endpoints, categorization rules, currency
//     rates, holiday calendars via the reusable EntityManager.
import { Title } from "@ui5/webcomponents-react";
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
    <div>
      <Title level="H3" style={{ marginBottom: "1rem" }}>Configuration</Title>

      <CodeValueManager />

      {CONFIG_ENTITIES.map((key) => (
        <div key={key} style={{ marginTop: "1.5rem" }}>
          <EntityManager entity={key} cfg={ENTITIES[key]} />
        </div>
      ))}
    </div>
  );
}