import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { Send, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatComposerProps {
  onSend: (message: string) => void;
  isSending: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatComposer({
  onSend,
  isSending,
  disabled = false,
  placeholder = "Ask anything about Tamil Nadu weather...",
}: ChatComposerProps) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      const newHeight = Math.min(textareaRef.current.scrollHeight, 140);
      textareaRef.current.style.height = `${Math.max(newHeight, 44)}px`;
    }
  }, [text]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || isSending || disabled) return;
    onSend(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "44px";
    }
  };

  const isButtonDisabled = !text.trim() || isSending || disabled;

  return (
    <div className="shrink-0 border-t border-slate-200 bg-white p-4">
      <div className="mx-auto max-w-4xl relative rounded-xl border border-slate-200 bg-slate-50/50 shadow-xs focus-within:border-blue-500 focus-within:bg-white focus-within:ring-1 focus-within:ring-blue-500 transition-all">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isSending || disabled}
          rows={1}
          className="w-full resize-none bg-transparent px-4 py-3 pr-14 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden disabled:opacity-50 min-h-[44px] max-h-[140px] leading-relaxed"
        />

        <div className="absolute right-2 bottom-2">
          <Button
            type="button"
            size="sm"
            onClick={handleSubmit}
            disabled={isButtonDisabled}
            className="size-8 p-0 rounded-lg bg-blue-600 hover:bg-blue-700 text-white shadow-2xs transition-all disabled:opacity-40 disabled:hover:bg-blue-600"
            title="Send message (Enter)"
          >
            {isSending ? (
              <Loader2 className="size-4 animate-spin text-white" />
            ) : (
              <Send className="size-3.5 text-white" />
            )}
          </Button>
        </div>
      </div>
      <div className="mt-1.5 text-center text-[11px] text-slate-400">
        Press <kbd className="font-mono text-[10px] bg-slate-100 rounded px-1">Enter</kbd> to send, <kbd className="font-mono text-[10px] bg-slate-100 rounded px-1">Shift + Enter</kbd> for a new line
      </div>
    </div>
  );
}
