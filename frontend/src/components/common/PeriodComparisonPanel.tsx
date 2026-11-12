import { useState, useEffect } from "react";
import {
  ArrowRightLeft,
  TrendingDown,
  TrendingUp,
  Minus,
  AlertCircle,
  Thermometer,
  CloudRain,
  Droplets,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { getComparison } from "@/api/endpoints";
import {
  getComparisonPresets,
  type ComparisonPreset,
  formatDateRange,
  getIstTodayStr,
  validateDateRange,
} from "@/lib/dateUtils";
import type { PeriodComparisonData, MetricDelta } from "@/types";
import { cn } from "@/lib/utils";

interface PeriodComparisonPanelProps {
  district?: string;
  className?: string;
  onClose?: () => void;
}

export function PeriodComparisonPanel({
  district,
  className,
  onClose,
}: PeriodComparisonPanelProps) {
  const presets = getComparisonPresets();
  const [activePreset, setActivePreset] = useState<ComparisonPreset["key"]>(
    "today_vs_yesterday"
  );
  const [data, setData] = useState<PeriodComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Custom range states
  const [isCustom, setIsCustom] = useState(false);
  const today = getIstTodayStr();
  const [pAStart, setPAStart] = useState("2026-11-12");
  const [pAEnd, setPAEnd] = useState("2026-11-12");
  const [pBStart, setPBStart] = useState("2026-11-11");
  const [pBEnd, setPBEnd] = useState("2026-11-11");

  const fetchComparison = async (
    startA: string,
    endA: string,
    startB: string,
    endB: string
  ) => {
    setLoading(true);
    setError(null);
    try {
      const res = await getComparison({
        period_a_start: startA,
        period_a_end: endA,
        period_b_start: startB,
        period_b_end: endB,
        district: district && district !== "all" ? district : undefined,
      });
      if (res.data) {
        setData(res.data);
      } else {
        setError(res.message || "No comparison data returned");
      }
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to load comparison data"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isCustom) {
      const current = presets.find((p) => p.key === activePreset);
      if (current) {
        fetchComparison(
          current.periodA.startDate,
          current.periodA.endDate,
          current.periodB.startDate,
          current.periodB.endDate
        );
      }
    }
  }, [activePreset, district, isCustom]);

  const handleCustomApply = () => {
    const valA = validateDateRange(pAStart, pAEnd);
    if (!valA.valid) {
      setError(`Period A error: ${valA.error}`);
      return;
    }
    const valB = validateDateRange(pBStart, pBEnd);
    if (!valB.valid) {
      setError(`Period B error: ${valB.error}`);
      return;
    }
    setError(null);
    fetchComparison(pAStart, pAEnd, pBStart, pBEnd);
  };

  const renderMetricDelta = (
    label: string,
    icon: React.ReactNode,
    delta?: MetricDelta
  ) => {
    if (!delta) return null;
    const isUp = delta.direction === "up";
    const isDown = delta.direction === "down";

    return (
      <div className="flex flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-xs">
        <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
          <span className="flex items-center gap-1.5">
            {icon}
            {label}
          </span>
          <span
            className={cn(
              "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] font-bold",
              isUp
                ? "bg-rose-100 text-rose-700"
                : isDown
                  ? "bg-blue-100 text-blue-700"
                  : "bg-slate-100 text-slate-700"
            )}
          >
            {isUp && <TrendingUp className="size-3" />}
            {isDown && <TrendingDown className="size-3" />}
            {!isUp && !isDown && <Minus className="size-3" />}
            {delta.percentage_change !== null
              ? `${delta.percentage_change > 0 ? "+" : ""}${delta.percentage_change.toFixed(1)}%`
              : delta.absolute_change !== null
                ? `${delta.absolute_change > 0 ? "+" : ""}${delta.absolute_change.toFixed(1)} ${delta.unit}`
                : "N/A"}
          </span>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 border-t border-slate-100 pt-2 text-xs">
          <div>
            <span className="text-[11px] text-slate-500">Period A (Current)</span>
            <div className="text-base font-bold text-slate-900">
              {delta.current_val !== null ? `${delta.current_val} ${delta.unit}` : "N/A"}
            </div>
          </div>
          <div>
            <span className="text-[11px] text-slate-500">Period B (Baseline)</span>
            <div className="text-base font-semibold text-slate-600">
              {delta.previous_val !== null ? `${delta.previous_val} ${delta.unit}` : "N/A"}
            </div>
          </div>
        </div>

        <div className="mt-2 text-[11px] text-slate-500">
          Net Difference:{" "}
          <span className="font-semibold text-slate-800">
            {delta.absolute_change !== null
              ? `${delta.absolute_change > 0 ? "+" : ""}${delta.absolute_change.toFixed(1)} ${delta.unit}`
              : "N/A"}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className={cn("space-y-4 rounded-xl border border-indigo-100 bg-indigo-50/40 p-4", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-indigo-100 pb-3">
        <div className="flex items-center gap-2">
          <ArrowRightLeft className="size-5 text-indigo-600" />
          <h3 className="text-sm font-bold text-slate-800">
            Weather Period Intelligence Comparison
          </h3>
          <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-bold text-indigo-800">
            {district && district !== "all" ? district : "All Tamil Nadu"}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex rounded-md bg-white p-0.5 shadow-xs">
            {presets.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => {
                  setIsCustom(false);
                  setActivePreset(p.key);
                }}
                className={cn(
                  "rounded px-2.5 py-1 text-xs font-medium transition-colors",
                  !isCustom && activePreset === p.key
                    ? "bg-indigo-600 text-white font-semibold"
                    : "text-slate-600 hover:text-slate-900"
                )}
              >
                {p.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => setIsCustom(true)}
              className={cn(
                "rounded px-2.5 py-1 text-xs font-medium transition-colors",
                isCustom
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-600 hover:text-slate-900"
              )}
            >
              Custom
            </button>
          </div>

          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 text-xs text-slate-500 hover:text-slate-800"
            >
              Close
            </Button>
          )}
        </div>
      </div>

      {isCustom && (
        <div className="grid grid-cols-1 gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-700">
              Period A (Target Window)
            </span>
            <div className="flex items-center gap-2">
              <input
                type="date"
                max={today}
                value={pAStart}
                onChange={(e) => setPAStart(e.target.value)}
                className="h-8 rounded border border-slate-300 px-2 text-xs"
              />
              <span className="text-xs text-slate-400">to</span>
              <input
                type="date"
                max={today}
                value={pAEnd}
                onChange={(e) => setPAEnd(e.target.value)}
                className="h-8 rounded border border-slate-300 px-2 text-xs"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <span className="text-xs font-semibold text-slate-700">
              Period B (Baseline Window)
            </span>
            <div className="flex items-center gap-2">
              <input
                type="date"
                max={today}
                value={pBStart}
                onChange={(e) => setPBStart(e.target.value)}
                className="h-8 rounded border border-slate-300 px-2 text-xs"
              />
              <span className="text-xs text-slate-400">to</span>
              <input
                type="date"
                max={today}
                value={pBEnd}
                onChange={(e) => setPBEnd(e.target.value)}
                className="h-8 rounded border border-slate-300 px-2 text-xs"
              />
              <Button
                size="sm"
                onClick={handleCustomApply}
                className="h-8 bg-indigo-600 px-3 text-xs text-white hover:bg-indigo-700"
              >
                Compare
              </Button>
            </div>
          </div>
        </div>
      )}

      {loading && (
        <div className="py-6 text-center text-xs text-slate-500 animate-pulse">
          Computing period comparison across Fabric lakehouse records...
        </div>
      )}

      {error && !loading && (
        <div className="flex items-center gap-2 rounded-md bg-rose-50 p-3 text-xs text-rose-700">
          <AlertCircle className="size-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {data && !loading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              Comparing{" "}
              <strong className="text-slate-800">{data.period_a_label}</strong> (
              {formatDateRange(data.period_a_range.start, data.period_a_range.end)}) vs{" "}
              <strong className="text-slate-800">{data.period_b_label}</strong> (
              {formatDateRange(data.period_b_range.start, data.period_b_range.end)})
            </span>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {renderMetricDelta(
              "Temperature",
              <Thermometer className="size-4 text-rose-500" />,
              data.temperature
            )}
            {renderMetricDelta(
              "Precipitation",
              <CloudRain className="size-4 text-sky-500" />,
              data.rainfall
            )}
            {renderMetricDelta(
              "Relative Humidity",
              <Droplets className="size-4 text-indigo-500" />,
              data.humidity
            )}
          </div>
        </div>
      )}
    </div>
  );
}
