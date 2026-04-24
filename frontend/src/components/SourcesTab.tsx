import { useMemo } from "react";

const LABELS: Record<string, string> = {
  users_table: "Users",
  jobs_table: "Jobs",
  logs: "Logs",
  rag: "RAG / docs",
};

export function SourcesTab({ sources }: { sources: string[] }) {
  const grouped = useMemo(() => {
    const m: Record<string, string[]> = {};
    for (const s of sources) {
      const kind = s.includes(":") ? s.split(":", 1)[0] : "misc";
      (m[kind] ||= []).push(s);
    }
    return m;
  }, [sources]);

  if (sources.length === 0) {
    return (
      <div className="text-center py-12 text-on-surface-variant">
        <span className="material-symbols-outlined text-[36px] opacity-50">info</span>
        <p className="mt-3 text-xs">No sources cited for this message.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 mb-2">
        <span className="h-2 w-2 rounded-full bg-secondary-container"></span>
        <h4 className="font-label-sm text-label-sm text-on-surface uppercase tracking-wider">
          Data planes consulted ({sources.length})
        </h4>
      </div>
      {Object.entries(grouped).map(([kind, items]) => (
        <div key={kind}>
          <h5 className="text-[10px] font-medium text-on-surface-variant uppercase tracking-wider mb-2">
            {LABELS[kind] ?? kind}
          </h5>
          <div className="space-y-1.5">
            {items.map((s, i) => (
              <div
                key={i}
                className="bg-surface-container-high border border-surface-variant rounded p-2 text-[11px] font-code-sm text-tertiary-fixed break-all"
              >
                {s}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
