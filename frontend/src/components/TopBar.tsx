import { useStore } from "../store";

export function TopBar() {
  const loading = useStore((s) => s.loading);
  const hasAssistant = useStore((s) =>
    s.messages.some((m) => m.role === "assistant"),
  );
  const statusLabel = loading ? "Thinking" : hasAssistant ? "Active" : "Idle";

  return (
    <header className="hidden md:flex items-center justify-between h-16 px-6 border-b border-surface-variant bg-surface-container shrink-0 z-30">
      <div className="flex items-center gap-4">
        <h2 className="font-headline-lg text-headline-lg text-on-surface">
          Agent Investigation: CL-492
        </h2>
        <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-primary-container/20 text-primary-container border border-primary-container/30">
          {statusLabel}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <button className="text-on-surface-variant hover:text-on-surface transition-colors p-2 rounded hover:bg-surface-variant">
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button className="text-on-surface-variant hover:text-on-surface transition-colors p-2 rounded hover:bg-surface-variant">
          <span className="material-symbols-outlined">help_outline</span>
        </button>
        <button className="text-on-surface-variant hover:text-on-surface transition-colors p-2 rounded hover:bg-surface-variant">
          <span className="material-symbols-outlined">account_circle</span>
        </button>
      </div>
    </header>
  );
}
