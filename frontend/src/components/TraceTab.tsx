import type { TraceEntry } from "../store";

function TraceCard({ entry, index }: { entry: TraceEntry; index: number }) {
  return (
    <div className="bg-surface-container-high border border-surface-variant rounded p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-on-surface-variant font-code-sm">
            #{index + 1}
          </span>
          <span className="text-xs font-semibold text-secondary font-code-sm">
            {entry.tool}
          </span>
        </div>
        {entry.result_count !== undefined && (
          <span className="text-[10px] text-on-surface-variant font-code-sm">
            → {entry.result_count} result{entry.result_count === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <div className="bg-background rounded p-2 font-code-sm text-[11px] text-tertiary-fixed border border-surface-variant overflow-x-auto">
        <pre className="whitespace-pre-wrap break-all">
          {JSON.stringify(entry.args, null, 2)}
        </pre>
      </div>

      {entry.result_preview && entry.result_preview.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wider text-on-surface-variant mb-1">
            preview
          </div>
          <div className="flex flex-wrap gap-1.5">
            {entry.result_preview.map((p, i) => (
              <span
                key={i}
                className="text-[10px] px-2 py-0.5 rounded bg-surface-variant text-on-surface font-code-sm"
              >
                {p}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function TraceTab({ trace }: { trace: TraceEntry[] }) {
  if (trace.length === 0) {
    return (
      <div className="text-center py-12 text-on-surface-variant">
        <span className="material-symbols-outlined text-[36px] opacity-50">info</span>
        <p className="mt-3 text-xs">No tool calls for this message.</p>
      </div>
    );
  }
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 mb-2">
        <span className="h-2 w-2 rounded-full bg-secondary-container"></span>
        <h4 className="font-label-sm text-label-sm text-on-surface uppercase tracking-wider">
          Tool calls ({trace.length})
        </h4>
      </div>
      {trace.map((e, i) => (
        <TraceCard key={i} entry={e} index={i} />
      ))}
    </div>
  );
}
