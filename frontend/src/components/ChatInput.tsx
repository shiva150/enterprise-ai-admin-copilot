import { useState, type KeyboardEvent } from "react";
import { useStore } from "../store";

export function ChatInput() {
  const [text, setText] = useState("");
  const sendQuery = useStore((s) => s.sendQuery);
  const loading = useStore((s) => s.loading);

  const submit = () => {
    if (!text.trim() || loading) return;
    void sendQuery(text);
    setText("");
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="p-4 border-t border-surface-variant bg-surface-container-low shrink-0">
      <div className="relative flex items-center">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          placeholder="Instruct the agent..."
          rows={1}
          className="w-full bg-surface-container-highest border border-surface-variant rounded-lg pl-4 pr-12 py-3 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20 resize-none font-body-md"
        />
        <button
          onClick={submit}
          disabled={!text.trim() || loading}
          className="absolute right-2 h-8 w-8 rounded bg-primary/10 text-primary hover:bg-primary/20 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          aria-label="Send"
        >
          <span
            className="material-symbols-outlined text-[18px]"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            send
          </span>
        </button>
      </div>
      <div className="flex justify-between items-center mt-2 px-1">
        <div className="flex gap-2">
          <button className="text-[10px] text-on-surface-variant hover:text-on-surface flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px]">attach_file</span>{" "}
            Attach context
          </button>
        </div>
        <span className="text-[10px] text-on-surface-variant">
          Shift + Enter for new line
        </span>
      </div>
    </div>
  );
}
