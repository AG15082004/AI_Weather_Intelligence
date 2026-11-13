import { Sparkles, Thermometer, CloudRain, Wind, Layers, ArrowUpRight } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

const CORE_SUGGESTED_PROMPTS = [
  {
    text: "Which district recorded the highest temperature today?",
    category: "Temperature",
    icon: Thermometer,
    color: "text-orange-500",
  },
  {
    text: "What is today's average temperature across Tamil Nadu?",
    category: "Statewide",
    icon: Layers,
    color: "text-amber-500",
  },
  {
    text: "Which district received the highest rainfall?",
    category: "Precipitation",
    icon: CloudRain,
    color: "text-blue-500",
  },
  {
    text: "Compare Chennai and Coimbatore weather.",
    category: "Comparison",
    icon: Layers,
    color: "text-indigo-500",
  },
  {
    text: "Which districts have the highest AQI?",
    category: "Air Quality",
    icon: Wind,
    color: "text-emerald-500",
  },
  {
    text: "Show rainfall trends for the last 30 days.",
    category: "Trends",
    icon: CloudRain,
    color: "text-sky-500",
  },
];

interface WelcomeHeroProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

export function WelcomeHero({ onSelectPrompt, disabled = false }: WelcomeHeroProps) {
  return (
    <div className="mx-auto my-auto max-w-2xl py-8 px-4 text-center">
      <div className="mx-auto mb-4 flex size-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-600 ring-1 ring-blue-100 shadow-xs">
        <Sparkles className="size-6 text-blue-600" />
      </div>

      <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-slate-900">
        How can I help you understand Tamil Nadu weather?
      </h2>

      <p className="mt-2 text-sm text-slate-500 max-w-lg mx-auto leading-relaxed">
        Ask questions about temperature, rainfall, air quality, historical patterns, and district comparisons across all 38 districts.
      </p>

      <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
        {CORE_SUGGESTED_PROMPTS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => onSelectPrompt(item.text)}
              className="group flex flex-col justify-between rounded-xl border border-slate-200/90 bg-white p-3.5 shadow-2xs hover:border-blue-400 hover:bg-blue-50/40 hover:shadow-xs transition-all disabled:opacity-50 text-left"
            >
              <div className="flex items-center justify-between">
                <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 group-hover:text-blue-600 transition-colors">
                  <Icon className={`size-3.5 ${item.color}`} />
                  {item.category}
                </span>
                <ArrowUpRight className="size-3.5 text-slate-300 group-hover:text-blue-600 transition-colors" />
              </div>
              <p className="mt-2 text-xs sm:text-sm font-medium text-slate-800 group-hover:text-blue-900 leading-snug">
                {item.text}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface ExploreSidebarProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

export function ExploreSidebar({ onSelectPrompt, disabled = false }: ExploreSidebarProps) {
  return (
    <Card className="flex flex-col h-full bg-white shadow-xs border border-slate-200/90 overflow-hidden min-h-0">
      <CardHeader className="shrink-0 border-b border-slate-100 px-4 py-3.5">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-blue-600" />
          <CardTitle className="text-sm font-bold text-slate-900 tracking-tight">
            Explore Weather Insights
          </CardTitle>
        </div>
        <p className="text-[11px] text-slate-500">
          One-click questions for instant analytics
        </p>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 overflow-y-auto space-y-2 p-3 scroll-smooth">
        {CORE_SUGGESTED_PROMPTS.map((item, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(item.text)}
            className="w-full rounded-lg border border-slate-200/80 bg-slate-50/70 p-2.5 text-left text-xs font-medium leading-relaxed text-slate-700 transition-all hover:border-blue-300 hover:bg-blue-50/70 hover:text-blue-700 hover:shadow-2xs disabled:opacity-50"
          >
            {item.text}
          </button>
        ))}
      </CardContent>
    </Card>
  );
}
