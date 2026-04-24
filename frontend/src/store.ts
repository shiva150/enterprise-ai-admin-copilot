import { create } from "zustand";

export type TraceEntry = {
  tool: string;
  args: Record<string, unknown>;
  result_count?: number;
  result_preview?: string[];
};

export type SuggestedAction = {
  action: string;
  params: Record<string, unknown>;
};

export type Metrics = {
  latency_ms?: number;
  tools_called?: number;
};

export type Message =
  | { role: "user"; content: string }
  | {
      role: "assistant";
      content: string;
      reasoning: string;
      sources: string[];
      trace: TraceEntry[];
      suggested_action: SuggestedAction | null;
      metrics: Metrics;
      executed: boolean;
      action_error?: string | null;
    };

type Tab = "reasoning" | "trace" | "sources";

type State = {
  messages: Message[];
  loading: boolean;
  actionPendingFor: number | null;
  selected: number | null;
  tab: Tab;
  error: string | null;
};

type Actions = {
  sendQuery: (query: string) => Promise<void>;
  executeAction: (messageIndex: number) => Promise<void>;
  selectMessage: (idx: number) => void;
  setTab: (tab: Tab) => void;
  dismissError: () => void;
};

export const useStore = create<State & Actions>((set, get) => ({
  messages: [],
  loading: false,
  actionPendingFor: null,
  selected: null,
  tab: "reasoning",
  error: null,

  sendQuery: async (query) => {
    const trimmed = query.trim();
    if (!trimmed || get().loading) return;
    set((s) => ({
      messages: [...s.messages, { role: "user", content: trimmed }],
      loading: true,
      error: null,
    }));
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
      }
      const data = await res.json();
      set((s) => {
        const msg: Message = {
          role: "assistant",
          content: data.answer ?? "",
          reasoning: data.reasoning ?? "",
          sources: data.sources ?? [],
          trace: data.trace ?? [],
          suggested_action: data.suggested_action ?? null,
          metrics: data.metrics ?? {},
          executed: false,
        };
        return {
          messages: [...s.messages, msg],
          loading: false,
          selected: s.messages.length,
          tab: "reasoning",
        };
      });
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : String(e) });
    }
  },

  executeAction: async (messageIndex) => {
    const msg = get().messages[messageIndex];
    if (!msg || msg.role !== "assistant" || !msg.suggested_action) return;
    set({ actionPendingFor: messageIndex, error: null });
    try {
      const res = await fetch("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(msg.suggested_action),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`HTTP ${res.status}: ${body || res.statusText}`);
      }
      await res.json();
      set((s) => ({
        actionPendingFor: null,
        messages: s.messages.map((m, i) =>
          i === messageIndex && m.role === "assistant"
            ? { ...m, executed: true, action_error: null }
            : m,
        ),
      }));
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      set((s) => ({
        actionPendingFor: null,
        messages: s.messages.map((m, i) =>
          i === messageIndex && m.role === "assistant"
            ? { ...m, action_error: msg }
            : m,
        ),
        error: msg,
      }));
    }
  },

  selectMessage: (idx) => set({ selected: idx, tab: "reasoning" }),
  setTab: (tab) => set({ tab }),
  dismissError: () => set({ error: null }),
}));
