import { useState } from "react";
import { Bot, User, Copy, Check, RefreshCw, ArrowRight } from "lucide-react";
import { MarkdownContent } from "./MarkdownContent";
import { ResponseEvidence } from "./ResponseEvidence";
import { AIInlineChart } from "@/components/charts/AIInlineChart";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

interface ChatMessageItemProps {
  message: ChatMessage;
  isSending?: boolean;
  onSelectSuggestion?: (prompt: string) => void;
  onRetry?: (prompt: string) => void;
}

export function ChatMessageItem({
  message,
  isSending = false,
  onSelectSuggestion,
  onRetry,
}: ChatMessageItemProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = () => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(message.content).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  // User Message
  if (isUser) {
    return (
      <div className="flex justify-end py-1">
        <div className="flex items-start gap-2.5 max-w-[85%] md:max-w-[75%] flex-row-reverse">
          <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-2xs mt-0.5">
            <User className="size-3.5" />
          </div>
          <div>
            <div className="rounded-2xl rounded-tr-xs bg-blue-600 px-4 py-2.5 text-sm text-white shadow-xs leading-relaxed">
              {message.content}
            </div>
            {message.timestamp && (
              <div className="mt-1 text-right text-[10px] text-slate-400 font-medium mr-1">
                {message.timestamp}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Assistant Message
  return (
    <div className="flex items-start gap-3 py-2">
      <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-700 ring-1 ring-slate-200/90 shadow-2xs mt-0.5">
        <Bot className="size-4 text-blue-600" />
      </div>

      <div className="flex-1 min-w-0 max-w-[96%] md:max-w-[92%]">
        <div
          className={cn(
            "group relative rounded-2xl rounded-tl-xs p-4 text-sm leading-relaxed transition-all",
            message.isError
              ? "border border-red-200 bg-red-50/60 text-red-900"
              : "border border-slate-200/80 bg-white text-slate-800 shadow-2xs"
          )}
        >
          {/* Copy Button */}
          {!message.isError && (
            <button
              type="button"
              onClick={handleCopy}
              className="absolute top-3 right-3 flex items-center gap-1 rounded-md p-1 text-slate-400 opacity-0 group-hover:opacity-100 hover:bg-slate-100 hover:text-slate-700 transition-all text-xs"
              title="Copy answer"
            >
              {copied ? (
                <>
                  <Check className="size-3.5 text-emerald-600" />
                  <span className="text-[10px] font-medium text-emerald-600">Copied</span>
                </>
              ) : (
                <Copy className="size-3.5" />
              )}
            </button>
          )}

          {/* Formatted Markdown Content */}
          <MarkdownContent content={message.content} />

          {/* Inline Recharts Visualization if present */}
          {message.chart && (
            <div className="mt-3">
              <AIInlineChart spec={message.chart} />
            </div>
          )}

          {/* Expandable Verified Lakehouse Evidence & Provenance */}
          <ResponseEvidence
            sources={message.sources}
            timestamp={message.observation_timestamp || message.timestamp}
            intent={message.intent}
            district={message.district}
          />

          {/* Error Retry Action */}
          {message.isError && message.retryQuery && onRetry && (
            <div className="mt-3 pt-2 border-t border-red-200/70">
              <button
                type="button"
                disabled={isSending}
                onClick={() => onRetry(message.retryQuery!)}
                className="inline-flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-900 hover:bg-red-200 transition-colors disabled:opacity-50"
              >
                <RefreshCw className="size-3" />
                Retry Query
              </button>
            </div>
          )}
        </div>

        {/* Suggested Follow-up Prompts */}
        {message.follow_up_suggestions && message.follow_up_suggestions.length > 0 && onSelectSuggestion && (
          <div className="mt-2.5 pl-1 space-y-1.5">
            <span className="text-[11px] font-semibold text-slate-500">
              Suggested Follow-ups:
            </span>
            <div className="flex flex-wrap gap-1.5">
              {message.follow_up_suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  disabled={isSending}
                  onClick={() => onSelectSuggestion(suggestion)}
                  className="flex items-center gap-1 rounded-full border border-sky-200 bg-sky-50/80 px-3 py-1 text-[11px] font-medium text-sky-800 transition-colors hover:bg-sky-100 hover:border-sky-300 disabled:opacity-50 shadow-2xs"
                >
                  <span>{suggestion}</span>
                  <ArrowRight className="size-2.5 text-sky-600" />
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
