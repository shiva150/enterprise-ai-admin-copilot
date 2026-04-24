import { useMemo } from "react";
import { useStore, type Message } from "../store";
import { ReasoningTab } from "./ReasoningTab";
import { TraceTab } from "./TraceTab";
import { SourcesTab } from "./SourcesTab";

type Tab = "reasoning" | "trace" | "sources";

function TabButton({
  icon,
  label,
  active,
  onClick,
  badge,
}: {
  icon: string;
  label: string;
  active: boolean;
  onClick: () => void;
  badge?: number;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "flex-1 py-3 px-4 text-sm font-medium border-b-2 transition-colors flex items-center justify-center gap-2 " +
        (active
          ? "text-primary border-primary bg-primary/5"
          : "text-on-surface-variant hover:text-on-surface hover:bg-surface-variant/50 border-transparent")
      }
    >
      <span className="material-symbols-outlined text-[18px]">{icon}</span>
      {label}
      {badge !== undefined && badge > 0 && (
        <span className="ml-0.5 text-[10px] font-code-sm px-1.5 py-[1px] rounded bg-surface-variant text-on-surface-variant">
          {badge}
        </span>
      )}
    </button>
  );
}

function EmptyContext() {
  return (
    <div className="text-center py-12 text-on-surface-variant">
      <span className="material-symbols-outlined text-[36px] opacity-50">info</span>
      <p className="mt-3 text-xs">
        Send a query to see reasoning, trace, and sources.
      </p>
    </div>
  );
}

export function ContextPanel() {
  const messages = useStore((s) => s.messages);
  const selected = useStore((s) => s.selected);
  const tab = useStore((s) => s.tab);
  const setTab = useStore((s) => s.setTab);
  const loading = useStore((s) => s.loading);

  const assistantMsg: Message | null = useMemo(() => {
    if (selected !== null) {
      const m = messages[selected];
      if (m && m.role === "assistant") return m;
    }
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === "assistant") return messages[i];
    }
    return null;
  }, [messages, selected]);

  const trace = assistantMsg && assistantMsg.role === "assistant" ? assistantMsg.trace : [];
  const reasoning = assistantMsg && assistantMsg.role === "assistant" ? assistantMsg.reasoning : "";
  const answer = assistantMsg && assistantMsg.role === "assistant" ? assistantMsg.content : "";
  const sources = assistantMsg && assistantMsg.role === "assistant" ? assistantMsg.sources : [];
  const latency =
    assistantMsg && assistantMsg.role === "assistant"
      ? assistantMsg.metrics?.latency_ms
      : undefined;

  return (
    <aside className="w-[450px] bg-surface-container flex flex-col shrink-0">
      {/* Tabs */}
      <div className="flex border-b border-surface-variant shrink-0 bg-surface-container-low">
        <TabButton
          icon="schema"
          label="Reasoning"
          active={tab === "reasoning"}
          onClick={() => setTab("reasoning" satisfies Tab)}
        />
        <TabButton
          icon="data_object"
          label="Trace"
          active={tab === "trace"}
          onClick={() => setTab("trace" satisfies Tab)}
          badge={trace.length}
        />
        <TabButton
          icon="library_books"
          label="Sources"
          active={tab === "sources"}
          onClick={() => setTab("sources" satisfies Tab)}
          badge={sources.length}
        />
      </div>

      {/* Tab Content Area */}
      <div className="flex-1 overflow-y-auto p-6">
        {!assistantMsg ? (
          <EmptyContext />
        ) : tab === "reasoning" ? (
          <ReasoningTab
            reasoning={reasoning}
            trace={trace}
            answer={answer}
            latencyMs={latency}
            loading={loading && selected === messages.length - 1}
          />
        ) : tab === "trace" ? (
          <TraceTab trace={trace} />
        ) : (
          <SourcesTab sources={sources} />
        )}
      </div>
    </aside>
  );
}
