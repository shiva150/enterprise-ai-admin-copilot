import type { TraceEntry } from "../store";

/** Prettify a tool name: query_db -> Query Db. Then hand-map common ones. */
const TOOL_TITLES: Record<string, string> = {
  query_db: "Query Database",
  fetch_logs: "Fetch Logs",
  retrieve_context: "Retrieve Context",
  trigger_action: "Trigger Action",
};

function prettify(s: string): string {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function titleFor(tool: string): string {
  return TOOL_TITLES[tool] ?? prettify(tool);
}

function describe(entry: TraceEntry): string {
  const args = entry.args ?? {};
  if (entry.tool === "query_db") {
    const table = String((args as { table?: unknown }).table ?? "");
    const filters = (args as { filters?: Record<string, unknown> }).filters;
    const filterStr =
      filters && Object.keys(filters).length > 0
        ? " where " +
          Object.entries(filters)
            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
            .join(", ")
        : "";
    return `Queried \`${table}\` table${filterStr}.`;
  }
  if (entry.tool === "fetch_logs") {
    const f = args as {
      service?: string;
      severity?: string;
      user_id?: string;
    };
    const parts = [
      f.service && `service=${f.service}`,
      f.severity && `severity=${f.severity}`,
      f.user_id && `user_id=${f.user_id}`,
    ].filter(Boolean);
    return `Fetched log entries${parts.length ? " with " + parts.join(", ") : ""}.`;
  }
  if (entry.tool === "retrieve_context") {
    const k = (args as { k?: number }).k ?? 3;
    return `Retrieved top-${k} policy and system-doc snippets.`;
  }
  return `Executed ${entry.tool}.`;
}

function parseIntent(reasoning: string): string | null {
  const m = reasoning.match(/Intent classified as:\s*([^\n.]+)\.?/i);
  return m ? m[1].trim() : null;
}

function answerBullets(answer: string, max = 5): string[] {
  return answer
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .slice(0, max);
}

type Props = {
  reasoning: string;
  trace: TraceEntry[];
  answer: string;
  latencyMs?: number;
  loading: boolean;
};

export function ReasoningTab({ reasoning, trace, answer, latencyMs, loading }: Props) {
  const intent = parseIntent(reasoning);
  const bullets = answerBullets(answer);
  const perStepMs =
    typeof latencyMs === "number" && trace.length > 0
      ? Math.max(1, Math.round(latencyMs / (trace.length + 1)))
      : null;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <span className="h-2 w-2 rounded-full bg-secondary-container"></span>
        <h4 className="font-label-sm text-label-sm text-on-surface uppercase tracking-wider">
          Execution Graph
        </h4>
      </div>

      {intent && (
        <div className="bg-surface-container-low border border-surface-variant rounded p-2 text-[11px] font-code-sm text-on-surface-variant">
          <span className="text-secondary">intent:</span>{" "}
          <span className="text-on-surface">{intent}</span>
        </div>
      )}

      <div className="relative border-l border-surface-variant ml-3 space-y-6 pb-4">
        {trace.map((entry, i) => (
          <div key={i} className="relative pl-6">
            <div className="absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-surface-container border-2 border-primary-container"></div>
            <div className="bg-surface-container-high border border-surface-variant rounded p-3">
              <div className="flex justify-between items-start mb-1">
                <span className="text-xs font-semibold text-on-surface">
                  {titleFor(entry.tool)}
                </span>
                <span className="text-[10px] text-on-surface-variant font-code-sm">
                  {perStepMs !== null ? `${perStepMs}ms` : "—"}
                </span>
              </div>
              <p className="text-xs text-on-surface-variant mb-2">{describe(entry)}</p>
              <div className="bg-background rounded p-1.5 border border-surface-variant font-code-sm text-[10px] text-secondary">
                Tool called: <span className="text-on-surface">{entry.tool}</span>
              </div>
            </div>
          </div>
        ))}

        {/* Synthesis step — processing while loading, complete when answer is present */}
        <div className="relative pl-6">
          <div
            className={
              "absolute -left-1.5 top-1 h-3 w-3 rounded-full bg-surface-container border-2 " +
              (loading
                ? "border-secondary-container shadow-[0_0_8px_rgba(3,181,211,0.4)]"
                : "border-primary-container")
            }
          ></div>
          <div
            className={
              "rounded p-3 border " +
              (loading
                ? "bg-surface-container-highest border-secondary/30"
                : "bg-surface-container-high border-surface-variant")
            }
          >
            <div className="flex justify-between items-start mb-1">
              <span className="text-xs font-semibold text-on-surface">
                Synthesize Answer
              </span>
              <span
                className={
                  "text-[10px] font-code-sm " +
                  (loading ? "text-secondary" : "text-on-surface-variant")
                }
              >
                {loading
                  ? "Processing..."
                  : typeof latencyMs === "number"
                  ? `${latencyMs}ms total`
                  : "done"}
              </span>
            </div>
            {bullets.length > 0 && (
              <ul className="text-xs text-on-surface-variant list-disc pl-4 space-y-1 mt-2">
                {bullets.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
