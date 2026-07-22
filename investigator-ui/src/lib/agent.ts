import { HttpAgent } from "@ag-ui/client";

const BACKEND_URL =
  (import.meta.env.VITE_TRANSACTION_AGENT_URL as string | undefined) ??
  "http://localhost:8010";

export function createTransactionAgentClient(): HttpAgent {
  return new HttpAgent({ url: `${BACKEND_URL}/agent/run` });
}

export const ACTIONS_URL = `${BACKEND_URL}/actions/decision`;
