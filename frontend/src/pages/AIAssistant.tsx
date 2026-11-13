import { useEffect, useRef, useState, type UIEvent } from "react";
import { Bot, RefreshCw, AlertCircle } from "lucide-react";
import { chatWithAI, clearChatSession } from "@/api/endpoints";
import { API_BASE_URL } from "@/api/client";
import { Card } from "@/components/ui/card";
import { AssistantHeader } from "@/components/ai/AssistantHeader";
import { ChatMessageItem } from "@/components/ai/ChatMessageItem";
import { ChatComposer } from "@/components/ai/ChatComposer";
import { WelcomeHero, ExploreSidebar } from "@/components/ai/SuggestedPrompts";
import type { ChatMessage } from "@/types";

export function AIAssistant() {
  const [conversationId, setConversationId] = useState<string>(() =>
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `session-${Date.now()}`
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  const chatContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);

  // Monitor user scrolling to avoid interrupting users reading earlier messages
  const handleScroll = (e: UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const distanceFromBottom =
      target.scrollHeight - target.scrollTop - target.clientHeight;
    isAtBottomRef.current = distanceFromBottom < 80;
  };

  // Scroll to bottom smoothly when appropriate
  useEffect(() => {
    if (isAtBottomRef.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isSending]);

  const handleNewConversation = async () => {
    if (conversationId) {
      try {
        await clearChatSession(conversationId);
      } catch {
        // Safe to ignore session reset errors
      }
    }
    const newId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `session-${Date.now()}`;
    setConversationId(newId);
    setMessages([]);
    setErrorBanner(null);
    isAtBottomRef.current = true;
  };

  const sendMessage = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isSending) return;

    const nowLabel = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: nowLabel,
    };

    setMessages((prev) => [...prev, userMessage]);
    setErrorBanner(null);
    setIsSending(true);

    // Scroll down when submitting
    isAtBottomRef.current = true;
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);

    try {
      const recentContext = messages
        .slice(-4)
        .map((m) => `${m.role}: ${m.content}`)
        .join("\n");

      // Natural conversational query without dashboard filter overrides
      const res = await chatWithAI(trimmed, recentContext, conversationId);

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: res.response || res.answer || "Weather analysis completed.",
        timestamp: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        }),
        intent: res.intent,
        district: res.district,
        districts: res.districts,
        confidence: res.confidence,
        sources: res.sources,
        applied_filters: res.applied_filters,
        observation_timestamp: res.observation_timestamp,
        chart: res.chart,
        follow_up_suggestions: res.follow_up_suggestions,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const rawMsg =
        err instanceof Error
          ? err.message
          : "Failed to contact the Weather Intelligence service.";

      let userFriendlyMsg = rawMsg;
      if (rawMsg.includes("Unable to reach") || rawMsg.includes("Network Error")) {
        userFriendlyMsg = `Unable to connect to the backend server. Please verify the backend service is running on ${API_BASE_URL}.`;
      } else if (rawMsg.includes("timed out") || rawMsg.includes("Lakehouse query timed out")) {
        userFriendlyMsg =
          "The query timed out while waiting for weather data. Please click Retry below to run the query again.";
      }

      setErrorBanner(userFriendlyMsg);
      setMessages((prev) => [
        ...prev,
        {
          id: `assistant-err-${Date.now()}`,
          role: "assistant",
          content: userFriendlyMsg,
          timestamp: new Date().toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          }),
          isError: true,
          retryQuery: trimmed,
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-4 h-[calc(100vh-8.5rem)] min-h-[580px]">
      {/* Central Conversational Panel */}
      <Card className="flex flex-col h-full bg-white shadow-xs border border-slate-200/90 lg:col-span-3 min-h-0 overflow-hidden rounded-xl">
        {/* Modern Header */}
        <AssistantHeader
          onNewConversation={handleNewConversation}
          isGrounded={true}
        />

        {/* Dismissable Error Banner */}
        {errorBanner && (
          <div className="shrink-0 flex items-center justify-between border-b border-amber-200 bg-amber-50/90 px-4 py-2 text-xs text-amber-900">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-4 shrink-0 text-amber-600" />
              <span>{errorBanner}</span>
            </div>
            <button
              type="button"
              onClick={() => setErrorBanner(null)}
              className="text-amber-700 hover:text-amber-950 font-semibold text-xs ml-3"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Scrollable Conversation Stream */}
        <div
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 min-h-0 overflow-y-auto px-4 sm:px-6 py-4 space-y-4 scroll-smooth flex flex-col"
        >
          {messages.length === 0 ? (
            <WelcomeHero
              onSelectPrompt={sendMessage}
              disabled={isSending}
            />
          ) : (
            messages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                isSending={isSending}
                onSelectSuggestion={sendMessage}
                onRetry={sendMessage}
              />
            ))
          )}

          {/* AI Thinking Animation State */}
          {isSending && (
            <div className="flex items-start gap-3 py-2">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-50 ring-1 ring-blue-200 shadow-2xs">
                <Bot className="size-4 animate-pulse text-blue-600" />
              </div>
              <div className="rounded-2xl rounded-tl-xs border border-slate-200 bg-slate-50/80 px-4 py-3 text-xs font-medium text-slate-600 flex items-center gap-2 shadow-2xs">
                <RefreshCw className="size-3.5 animate-spin text-blue-600" />
                <span>Synthesizing verified weather intelligence from Microsoft Fabric...</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} className="h-1" />
        </div>

        {/* Sticky Message Composer */}
        <ChatComposer
          onSend={sendMessage}
          isSending={isSending}
        />
      </Card>

      {/* Right Explore Panel (Compact & Hidden on Mobile/Tablet) */}
      <div className="hidden lg:flex lg:col-span-1 h-full min-h-0">
        <ExploreSidebar
          onSelectPrompt={sendMessage}
          disabled={isSending}
        />
      </div>
    </div>
  );
}
