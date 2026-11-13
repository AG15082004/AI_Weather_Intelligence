import { RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AssistantHeaderProps {
  onNewConversation: () => void;
  isGrounded?: boolean;
}

export function AssistantHeader({
  onNewConversation,
  isGrounded = true,
}: AssistantHeaderProps) {
  return (
    <header className="shrink-0 flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
        <h1 className="text-xl sm:text-2xl font-semibold tracking-tight text-slate-900">
          AI Assistant
        </h1>
        <div className="flex items-center gap-2 mt-1 sm:mt-0">
          <span className="hidden sm:inline text-slate-300">|</span>
          <span className="text-sm font-medium text-slate-600">
            Tamil Nadu Weather Intelligence Agent
          </span>
          {isGrounded && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 ring-1 ring-emerald-600/20">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Grounded AI
            </span>
          )}
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={onNewConversation}
        className="gap-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 border-slate-200 hover:bg-slate-50 transition-colors"
        title="Start fresh conversation"
      >
        <RotateCcw className="size-3.5 text-slate-500" />
        <span>New Conversation</span>
      </Button>
    </header>
  );
}
