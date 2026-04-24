import { useEffect, useRef } from "react";
import { useStore } from "../store";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";

const DEMO_QUERIES = [
  "Why did user U002 lose access?",
  "Show failed jobs",
  "What permissions does auditor have?",
  "Restart failed ETL job",
  "Why did ETL fail and what should I do?",
];

function EmptyState() {
  const sendQuery = useStore((s) => s.sendQuery);
  return (
    <div className="text-center py-8">
      <span className="material-symbols-outlined text-[40px] text-primary-container/60">
        smart_toy
      </span>
      <h3 className="mt-2 font-label-sm text-label-sm text-on-surface uppercase tracking-wider">
        Ready to investigate
      </h3>
      <p className="text-[10px] text-on-surface-variant mb-5 font-code-sm">
        mock mode · deterministic · no API calls
      </p>
      <div className="space-y-2 max-w-md mx-auto">
        {DEMO_QUERIES.map((q) => (
          <button
            key={q}
            onClick={() => sendQuery(q)}
            className="w-full text-left px-4 py-2 rounded border border-surface-variant bg-surface-container-low hover:bg-surface-variant hover:border-primary-container/40 transition-colors text-sm text-on-surface-variant hover:text-on-surface"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex gap-4">
      <div className="h-8 w-8 rounded bg-primary-container/10 border border-primary-container/30 flex items-center justify-center shrink-0 text-primary-container">
        <span className="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>
      <div className="bg-surface-container-low rounded-lg p-4 rounded-tl-none border border-surface-variant inline-flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse" />
        <span
          className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"
          style={{ animationDelay: "150ms" }}
        />
        <span
          className="w-1.5 h-1.5 rounded-full bg-primary-container animate-pulse"
          style={{ animationDelay: "300ms" }}
        />
      </div>
    </div>
  );
}

export function ChatPane() {
  const messages = useStore((s) => s.messages);
  const loading = useStore((s) => s.loading);
  const error = useStore((s) => s.error);
  const dismissError = useStore((s) => s.dismissError);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, loading]);

  return (
    <section className="flex-1 flex flex-col border-r border-surface-variant bg-surface-container-lowest min-w-[400px]">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-surface-variant flex justify-between items-center bg-surface-container-low shrink-0">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary">smart_toy</span>
          <h3 className="font-label-sm text-label-sm text-on-surface font-semibold">
            DevOps Copilot v4
          </h3>
        </div>
        <button className="text-xs text-on-surface-variant hover:text-primary transition-colors flex items-center gap-1">
          <span className="material-symbols-outlined text-[16px]">history</span> History
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="px-4 py-2 bg-error-container/30 border-b border-error/30 text-[12px] text-error flex items-center justify-between">
          <span>⚠ {error}</span>
          <button
            onClick={dismissError}
            className="text-error hover:text-on-surface transition-colors"
            aria-label="Dismiss"
          >
            <span className="material-symbols-outlined text-[16px]">close</span>
          </button>
        </div>
      )}

      {/* Chat History */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((m, i) => <MessageBubble key={i} message={m} index={i} />)
        )}
        {loading && <TypingIndicator />}
      </div>

      {/* Input Area */}
      <ChatInput />
    </section>
  );
}
