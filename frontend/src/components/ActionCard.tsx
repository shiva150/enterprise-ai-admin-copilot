import { useStore, type Metrics, type SuggestedAction } from "../store";

/** Friendly display metadata per action name. */
const ACTION_META: Record<string, { title: string; description: string }> = {
  restart_job: {
    title: "Restart Failed Job",
    description:
      "Re-queue the failed job with its original parameters. Appropriate for transient connection or timeout errors.",
  },
  reassign_role: {
    title: "Reassign Role",
    description:
      "Change the user's role to the target role. Propagation to downstream systems can take up to 5 minutes.",
  },
  reset_password: {
    title: "Reset Password",
    description:
      "Force a password reset for the user. Current credentials will be invalidated immediately.",
  },
  suspend_user: {
    title: "Suspend User",
    description: "Block authentication and terminate active sessions.",
  },
  unsuspend_user: {
    title: "Unsuspend User",
    description:
      "Restore the user's active status. Existing role grants are preserved.",
  },
};

function prettify(name: string): string {
  return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function codePreview(a: SuggestedAction): string {
  const params = JSON.stringify(a.params ?? {});
  return `"action": "${a.action}", "params": ${params}`;
}

function metaLabel(args: {
  executed: boolean;
  metrics?: Metrics;
  error?: string | null;
}): string {
  if (args.error) return "Failed";
  if (args.executed) return "Executed";
  if (args.metrics?.tools_called !== undefined) {
    return `Tools: ${args.metrics.tools_called}`;
  }
  return "Proposed";
}

type Props = {
  messageIndex: number;
  suggested: SuggestedAction;
  executed: boolean;
  error?: string | null;
  metrics?: Metrics;
};

export function ActionCard({
  messageIndex,
  suggested,
  executed,
  error,
  metrics,
}: Props) {
  const executeAction = useStore((s) => s.executeAction);
  const pendingFor = useStore((s) => s.actionPendingFor);
  const pending = pendingFor === messageIndex;

  const meta = ACTION_META[suggested.action] ?? {
    title: prettify(suggested.action),
    description: "Propose this admin action. Operator confirmation required.",
  };

  return (
    <div className="bg-surface-container rounded border border-secondary/30 overflow-hidden">
      <div className="px-4 py-2 border-b border-surface-variant bg-surface-container-high flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px] text-secondary">
            build
          </span>
          <span className="text-xs font-semibold text-on-surface uppercase tracking-wider">
            Suggested Action
          </span>
        </div>
        <span className="text-[10px] text-on-surface-variant font-code-sm">
          {metaLabel({ executed, metrics, error })}
        </span>
      </div>
      <div className="p-4">
        <h4 className="font-label-sm text-label-sm text-on-surface mb-1">
          {meta.title}
        </h4>
        <p className="text-sm text-on-surface-variant mb-4">{meta.description}</p>

        <div className="bg-background rounded p-2 mb-4 font-code-sm text-code-sm text-tertiary-fixed border border-surface-variant overflow-x-auto">
          <code>{codePreview(suggested)}</code>
        </div>

        {error && !executed && (
          <div className="mb-3 px-3 py-2 rounded border border-error/40 bg-error-container/20 text-[11px] text-error">
            {error}
          </div>
        )}

        {executed ? (
          <div className="w-full bg-secondary/15 text-secondary border border-secondary/40 font-label-sm text-label-sm py-2 px-4 rounded flex items-center justify-center gap-2">
            <span className="material-symbols-outlined text-[18px]">check_circle</span>
            Executed (simulated)
          </div>
        ) : (
          <button
            onClick={() => executeAction(messageIndex)}
            disabled={pending}
            className="w-full bg-primary hover:bg-primary-fixed disabled:opacity-50 disabled:cursor-wait transition-colors text-on-primary font-label-sm text-label-sm py-2 px-4 rounded flex items-center justify-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">play_arrow</span>
            {pending ? "Executing..." : "Execute Action"}
          </button>
        )}
      </div>
    </div>
  );
}
