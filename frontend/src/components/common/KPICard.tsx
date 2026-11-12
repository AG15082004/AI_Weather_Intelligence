import type { LucideIcon } from "lucide-react";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export type KPIAccent =
  | "blue"
  | "emerald"
  | "amber"
  | "rose"
  | "cyan"
  | "indigo"
  | "slate";

const ACCENT_STYLES: Record<
  KPIAccent,
  { border: string; iconBg: string; iconText: string }
> = {
  blue: {
    border: "border-t-blue-600",
    iconBg: "bg-blue-50",
    iconText: "text-blue-600",
  },
  emerald: {
    border: "border-t-emerald-500",
    iconBg: "bg-emerald-50",
    iconText: "text-emerald-600",
  },
  amber: {
    border: "border-t-amber-500",
    iconBg: "bg-amber-50",
    iconText: "text-amber-600",
  },
  rose: {
    border: "border-t-rose-500",
    iconBg: "bg-rose-50",
    iconText: "text-rose-600",
  },
  cyan: {
    border: "border-t-cyan-500",
    iconBg: "bg-cyan-50",
    iconText: "text-cyan-600",
  },
  indigo: {
    border: "border-t-indigo-500",
    iconBg: "bg-indigo-50",
    iconText: "text-indigo-600",
  },
  slate: {
    border: "border-t-slate-500",
    iconBg: "bg-slate-100",
    iconText: "text-slate-600",
  },
};

export interface KPICardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  change?: string;
  trend?: "up" | "down" | "neutral";
  icon: LucideIcon;
  accent?: KPIAccent;
  className?: string;
}

export function KPICard({
  title,
  value,
  subtitle,
  change,
  trend = "neutral",
  icon: Icon,
  accent = "blue",
  className,
}: KPICardProps) {
  const styles = ACCENT_STYLES[accent];

  return (
    <Card
      className={cn(
        "border-t-3 bg-white shadow-xs transition-shadow hover:shadow-sm",
        styles.border,
        className
      )}
    >
      <CardContent className="pt-1">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium tracking-wide text-slate-500 uppercase">
              {title}
            </p>
            <p className="mt-2 text-2xl font-bold tracking-tight text-slate-900">
              {value}
            </p>
          </div>
          <div
            className={cn(
              "flex size-10 shrink-0 items-center justify-center rounded-lg",
              styles.iconBg,
              styles.iconText
            )}
          >
            <Icon className="size-5" />
          </div>
        </div>

        {(subtitle || change) && (
          <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
            {change && (
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium",
                  trend === "up" && "bg-emerald-50 text-emerald-700",
                  trend === "down" && "bg-rose-50 text-rose-700",
                  trend === "neutral" && "bg-slate-100 text-slate-600"
                )}
              >
                {trend === "up" && <TrendingUp className="size-3" />}
                {trend === "down" && <TrendingDown className="size-3" />}
                {trend === "neutral" && <Minus className="size-3" />}
                {change}
              </span>
            )}
            {subtitle && (
              <span className="truncate text-slate-500">{subtitle}</span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
