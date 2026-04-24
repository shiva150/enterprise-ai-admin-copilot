import { useStore, type Message } from "../store";
import { ActionCard } from "./ActionCard";

/** Split the answer into lead + rest so we can render the lead brighter
 *  and the remainder muted, matching the static mock's two-paragraph style. */
function splitAnswer(answer: string): { lead: string; rest: string } {
  const parts = answer.split(/(?<=\.)\s+/);
  const lead = parts[0] ?? answer;
  const rest = parts.slice(1).join(" ");
  return { lead, rest };
}

export function MessageBubble({
  message,
  index,
}: {
  message: Message;
  index: number;
}) {
  const selectMessage = useStore((s) => s.selectMessage);
  const selected = useStore((s) => s.selected);

  if (message.role === "user") {
    return (
      <div className="flex gap-4 justify-end">
        <div className="max-w-[80%] bg-surface-variant rounded-lg p-4 rounded-tr-none border border-outline-variant/30">
          <p className="font-body-md text-body-md text-on-surface">
            {message.content}
          </p>
        </div>
        <div className="h-8 w-8 rounded bg-surface-variant border border-outline-variant flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
            person
          </span>
        </div>
      </div>
    );
  }

  const isSelected = selected === index;
  const { lead, rest } = splitAnswer(message.content);

  return (
    <div className="flex gap-4">
      <div className="h-8 w-8 rounded bg-primary-container/10 border border-primary-container/30 flex items-center justify-center shrink-0 text-primary-container">
        <span className="material-symbols-outlined text-[18px]">smart_toy</span>
      </div>

      <div className="max-w-[85%] space-y-4">
        <button
          type="button"
          onClick={() => selectMessage(index)}
          className={
            "w-full text-left rounded-lg p-4 rounded-tl-none border transition-colors bg-surface-container-low " +
            (isSelected
              ? "border-primary-container/60 ring-1 ring-primary-container/30"
              : "border-surface-variant hover:border-primary-container/30")
          }
        >
          <p className="font-body-md text-body-md text-on-surface mb-3">{lead}</p>
          {rest && (
            <p className="font-body-md text-body-md text-on-surface-variant">{rest}</p>
          )}
        </button>

        {message.suggested_action && (
          <ActionCard
            messageIndex={index}
            suggested={message.suggested_action}
            executed={message.executed}
            error={message.action_error ?? null}
            metrics={message.metrics}
          />
        )}
      </div>
    </div>
  );
}
