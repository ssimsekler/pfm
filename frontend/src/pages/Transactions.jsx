// Transactions page: full CRUD via the reusable EntityManager, including
// multi-line split editing (SplitEditor) and Policy 1 handling.
import EntityManager from "../components/EntityManager";
import { ENTITIES } from "../entities";

export default function Transactions() {
  return <EntityManager entity="transactions" cfg={ENTITIES.transactions} />;
}