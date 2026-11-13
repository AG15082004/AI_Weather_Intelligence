import { useEffect, useRef, useState, type FormEvent, type UIEvent } from "react";
import {
  Bot,
  Send,
  Sparkles,
  RotateCcw,
  User,
  ArrowRight,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { chatWithAI, clearChatSession } from "@/api/endpoints";
import { API_BASE_URL } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { AIWeatherReportCard } from "@/components/ai/AIWeatherReportCard";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/types";

const SUGGESTED_PROMPTS = [
  "What is today's weather across Tamil Nadu?",
  "Which district is hottest today?",
  "Compare Chennai and Coimbatore weather.",
  "Show yesterday's rainfall across districts.",
  "Show all-time temperature and rainfall trends across Tamil Nadu.",
  "Which districts have unhealthy AQI?",
  "Compare this month and last month temperature.",
  "Generate a Tamil Nadu weather bulletin report.",
  "Which district has the coolest temperature?",
];

const INITIAL_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "### Tamil Nadu Weather Intelligence Assistant\n\n" +
    "Vanakkam! I am your AI meteorology specialist for Tamil Nadu. " +
    "Ask me about real-time district weather, rainfall analytics, historical heat patterns, air quality, or district comparisons across all 38 districts.",
  timestamp: new Date().toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  }),
  sources: ["Live Weather Observations"],
  follow_up_suggestions: [
    "What is today's weather across Tamil Nadu?",
    "Which district is the hottest right now?",
    "Show yesterday's rainfall distribution",
    "Which districts have unhealthy AQI?",
  ],
};

export function AIAssistant() {
  const [conversationId, setConversationId] = useState<string>(() =>
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : `session-${Date.now()}`
  );
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
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
    setMessages([INITIAL_MESSAGE]);
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
    setInput("");
    setErrorBanner(null);
    setIsSending(true);

    // Force scroll down when sending user message
    isAtBottomRef.current = true;
    setTimeout(() => {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);

    try {
      const recentContext = messages
        .slice(-4)
        .map((m) => `${m.role}: ${m.content}`)
        .join("\n");

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

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    void sendMessage(input);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-4 h-[calc(100vh-8.5rem)] min-h-[560px]">
      {/* Central AI Conversation Panel (3 cols) */}
      <Card className="flex flex-col h-full bg-white shadow-xs border border-slate-200/90 lg:col-span-3 min-h-0 overflow-hidden">
        {/* Fixed Header */}
        <CardHeader className="shrink-0 flex flex-row items-center justify-between border-b border-slate-100 bg-white px-5 py-3.5 z-10">
          <div className="flex items-center gap-3">
            <div className="flex size-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
              <Bot className="size-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CardTitle className="text-base font-bold text-slate-900 tracking-tight">
                  Tamil Nadu Weather Intelligence Agent
                </CardTitle>
                <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 ring-1 ring-emerald-600/20">
                  Grounded Intelligence
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Natural-language meteorological observations & analytics across all 38 districts
              </p>
            </div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleNewConversation}
            className="gap-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 border-slate-200 hover:bg-slate-50"
            title="Start fresh conversation"
          >
            <RotateCcw className="size-3.5" />
            New Conversation
          </Button>
        </CardHeader>

        {/* Error Notification Banner if any */}
        {errorBanner && (
          <div className="shrink-0 flex items-center justify-between border-b border-amber-200 bg-amber-50/80 px-4 py-2 text-xs text-amber-900">
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

        {/* Independent Scrollable Chat Area */}
        <div
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 min-h-0 overflow-y-auto px-4 md:px-6 py-4 space-y-4 scroll-smooth"
        >
          {messages.map((msg) => {
            const isUser = msg.role === "user";

            if (isUser) {
              return (
                <div key={msg.id} className="flex justify-end">
                  <div className="flex items-start gap-2.5 max-w-[80%] flex-row-reverse">
                    <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white shadow-2xs">
                      <User className="size-3.5" />
                    </div>
                    <div>
                      <div className="rounded-2xl rounded-tr-xs bg-blue-600 px-4 py-2.5 text-sm text-white shadow-xs leading-relaxed">
                        {msg.content}
                      </div>
                      <div className="mt-1 text-right text-[10px] text-slate-400 font-medium mr-1">
                        {msg.timestamp}
                      </div>
                    </div>
                  </div>
                </div>
              );
            }

            // Assistant Message
            return (
              <div key={msg.id} className="flex items-start gap-3 w-full">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-slate-700 ring-1 ring-slate-200 shadow-2xs mt-1">
                  <Bot className="size-4.5 text-blue-600" />
                </div>

                <div className="flex-1 min-w-0 max-w-[95%]">
                  <div
                    className={cn(
                      "rounded-2xl rounded-tl-xs border p-4 text-sm leading-relaxed shadow-xs transition-all",
                      msg.isError
                        ? "border-red-200 bg-red-50/60"
                        : "border-slate-200/90 bg-white"
                    )}
                  >
                    <AIWeatherReportCard
                      content={msg.content}
                      chart={msg.chart}
                      sources={msg.sources}
                      intent={msg.intent}
                      district={msg.district}
                      timestamp={msg.observation_timestamp || msg.timestamp}
                      isError={msg.isError}
                    />

                    {/* Recoverable Retry Action */}
                    {msg.isError && msg.retryQuery && (
                      <div className="mt-3 pt-2.5 border-t border-red-200/70">
                        <button
                          type="button"
                          disabled={isSending}
                          onClick={() => void sendMessage(msg.retryQuery!)}
                          className="inline-flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-xs font-semibold text-red-900 transition-colors hover:bg-red-200 disabled:opacity-50"
                        >
                          <RefreshCw className="size-3" />
                          Retry Query
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Follow-up Suggestion Chips */}
                  {msg.follow_up_suggestions && msg.follow_up_suggestions.length > 0 && (
                    <div className="mt-2.5 pl-1 space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-500">
                        Suggested Follow-ups:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.follow_up_suggestions.map((suggestion) => (
                          <button
                            key={suggestion}
                            type="button"
                            disabled={isSending}
                            onClick={() => void sendMessage(suggestion)}
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
          })}

          {/* AI Thinking / Loading Indicator */}
          {isSending && (
            <div className="flex items-start gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-blue-50 ring-1 ring-blue-200 shadow-2xs">
                <Bot className="size-4.5 animate-pulse text-blue-600" />
              </div>
              <div className="rounded-2xl rounded-tl-xs border border-slate-200 bg-slate-50/80 px-4 py-3 text-xs font-medium text-slate-600 flex items-center gap-2">
                <RefreshCw className="size-3.5 animate-spin text-blue-600" />
                <span>Synthesizing verified weather intelligence...</span>
              </div>
            </div>
          )}

          <div ref={bottomRef} className="h-1" />
        </div>

        {/* Fixed Message Input Bar */}
        <div className="shrink-0 border-t border-slate-200 bg-white p-3.5 md:p-4 z-10">
          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about weather, temperature, rainfall, AQI, rankings, or district comparisons..."
              disabled={isSending}
              className="h-10.5 flex-1 bg-slate-50/90 text-sm focus-visible:bg-white border-slate-200 focus-visible:border-blue-500 rounded-lg"
            />
            <Button
              type="submit"
              disabled={isSending || !input.trim()}
              className="h-10.5 gap-1.5 px-5 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-xs transition-all disabled:opacity-50"
            >
              <Send className="size-4" />
              <span>Send</span>
            </Button>
          </form>
        </div>
      </Card>

      {/* Right Weather Intelligence Prompts Panel (1 col) */}
      <Card className="flex flex-col h-full bg-white shadow-xs border border-slate-200/90 overflow-hidden min-h-0">
        <CardHeader className="shrink-0 border-b border-slate-100 px-4 py-3.5">
          <div className="flex items-center gap-2">
            <Sparkles className="size-4 text-blue-600" />
            <CardTitle className="text-sm font-bold text-slate-900 tracking-tight">
              Weather Intelligence Prompts
            </CardTitle>
          </div>
          <p className="text-[11px] text-slate-500">
            One-click questions for instant analytics
          </p>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-y-auto space-y-2 p-3.5 scroll-smooth">
          {SUGGESTED_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={isSending}
              onClick={() => void sendMessage(prompt)}
              className="w-full rounded-lg border border-slate-200/80 bg-slate-50/70 p-2.5 text-left text-xs font-medium leading-relaxed text-slate-700 transition-all hover:border-blue-300 hover:bg-blue-50/70 hover:text-blue-700 hover:shadow-2xs disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
