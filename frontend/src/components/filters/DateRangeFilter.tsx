import React, { useState } from "react";
import {
  Calendar as CalendarIcon,
  RotateCcw,
  Clock,
  Check,
  AlertCircle,
  ArrowRightLeft,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DATE_PRESETS,
  type PresetKey,
  getPresetDateRange,
  getIstTodayStr,
  validateDateRange,
  formatDateRange,
} from "@/lib/dateUtils";
import { cn } from "@/lib/utils";

export interface DateFilterState {
  startDate: string;
  endDate: string;
  preset: PresetKey;
}

export interface DateRangeFilterProps {
  startDate: string;
  endDate: string;
  onApply?: (start: string, end: string, preset?: PresetKey) => void;
  onStartDateChange?: (date: string) => void;
  onEndDateChange?: (date: string) => void;
  onReset?: () => void;
  selectedDistrict?: string;
  className?: string;
  showComparisonToggle?: boolean;
  onToggleComparison?: () => void;
  isComparisonActive?: boolean;
}

export function DateRangeFilter({
  startDate,
  endDate,
  onApply,
  onStartDateChange,
  onEndDateChange,
  onReset,
  selectedDistrict,
  className,
  showComparisonToggle,
  onToggleComparison,
  isComparisonActive,
}: DateRangeFilterProps) {
  const todayIst = getIstTodayStr();

  // Local draft state for inputs before applying
  const [localStart, setLocalStart] = useState(startDate);
  const [localEnd, setLocalEnd] = useState(endDate);
  const [activePreset, setActivePreset] = useState<PresetKey>("last_7_days");
  const [validationError, setValidationError] = useState<string | null>(null);

  // Sync with incoming props if changed outside
  React.useEffect(() => {
    setLocalStart(startDate);
    setLocalEnd(endDate);
  }, [startDate, endDate]);

  const handlePresetChange = (presetKey: PresetKey) => {
    setActivePreset(presetKey);
    if (presetKey === "custom") {
      return; // allow user to edit dates freely
    }
    const range = getPresetDateRange(presetKey);
    setLocalStart(range.startDate);
    setLocalEnd(range.endDate);
    setValidationError(null);
    onStartDateChange?.(range.startDate);
    onEndDateChange?.(range.endDate);
    onApply?.(range.startDate, range.endDate, presetKey);
  };

  const handleApply = () => {
    const val = validateDateRange(localStart, localEnd);
    if (!val.valid) {
      setValidationError(val.error || "Invalid date range");
      return;
    }
    setValidationError(null);
    onStartDateChange?.(localStart);
    onEndDateChange?.(localEnd);
    onApply?.(localStart, localEnd, activePreset);
  };

  const handleReset = () => {
    const defaultRange = getPresetDateRange("last_7_days");
    setActivePreset("last_7_days");
    setLocalStart(defaultRange.startDate);
    setLocalEnd(defaultRange.endDate);
    setValidationError(null);
    if (onReset) {
      onReset();
    } else {
      onStartDateChange?.(defaultRange.startDate);
      onEndDateChange?.(defaultRange.endDate);
      onApply?.(defaultRange.startDate, defaultRange.endDate, "last_7_days");
    }
  };

  const hasChanges = localStart !== startDate || localEnd !== endDate;

  return (
    <div className={cn("space-y-2.5", className)}>
      {/* Primary Toolbar */}
      <div className="flex flex-wrap items-center gap-2.5 rounded-lg border border-slate-200 bg-white p-2.5 shadow-xs">
        {/* Preset Selector */}
        <div className="flex items-center gap-1.5">
          <CalendarIcon className="size-4 shrink-0 text-sky-600" />
          <span className="text-xs font-semibold text-slate-700">Preset:</span>
          <div className="relative">
            <select
              value={activePreset}
              onChange={(e) => handlePresetChange(e.target.value as PresetKey)}
              className="h-8 rounded-md border border-slate-300 bg-white py-1 pr-7 pl-2.5 text-xs font-medium text-slate-800 focus:border-sky-500 focus:ring-1 focus:ring-sky-500 focus:outline-hidden"
            >
              {DATE_PRESETS.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute top-2 right-2 size-3 text-slate-400" />
          </div>
        </div>

        <div className="hidden h-5 w-px bg-slate-200 sm:block" />

        {/* Start Date */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="range-start-date" className="text-xs text-slate-500">
            From:
          </label>
          <Input
            id="range-start-date"
            type="date"
            value={localStart}
            max={localEnd || todayIst}
            onChange={(e) => {
              setLocalStart(e.target.value);
              setActivePreset("custom");
              setValidationError(null);
            }}
            className="h-8 w-35 rounded-md border-slate-300 bg-white px-2 text-xs"
          />
        </div>

        {/* End Date */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="range-end-date" className="text-xs text-slate-500">
            To:
          </label>
          <Input
            id="range-end-date"
            type="date"
            value={localEnd}
            min={localStart}
            max={todayIst}
            onChange={(e) => {
              setLocalEnd(e.target.value);
              setActivePreset("custom");
              setValidationError(null);
            }}
            className="h-8 w-35 rounded-md border-slate-300 bg-white px-2 text-xs"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            onClick={handleApply}
            className="h-8 gap-1 bg-sky-600 px-3 text-xs font-medium text-white hover:bg-sky-700"
          >
            <Check className="size-3.5" />
            Apply
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleReset}
            className="h-8 gap-1 px-2 text-xs text-slate-500 hover:text-slate-800"
            title="Reset to Last 7 Days"
          >
            <RotateCcw className="size-3" />
            Reset
          </Button>
        </div>

        {/* Comparison Mode Toggle */}
        {showComparisonToggle && (
          <div className="ml-auto flex items-center">
            <Button
              variant={isComparisonActive ? "default" : "outline"}
              size="sm"
              onClick={onToggleComparison}
              className={cn(
                "h-8 gap-1.5 text-xs font-medium",
                isComparisonActive
                  ? "bg-indigo-600 text-white hover:bg-indigo-700"
                  : "border-slate-200 text-slate-700 hover:bg-slate-50"
              )}
            >
              <ArrowRightLeft className="size-3.5" />
              {isComparisonActive ? "Exit Comparison" : "Compare Periods"}
            </Button>
          </div>
        )}
      </div>

      {/* Validation Error Banner */}
      {validationError && (
        <div className="flex items-center gap-2 rounded-md border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs text-rose-700">
          <AlertCircle className="size-4 shrink-0 text-rose-500" />
          <span>{validationError}</span>
        </div>
      )}

      {/* Active Selection Banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-slate-100/80 px-3 py-1.5 text-xs text-slate-600">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="font-semibold text-slate-700">Date Range:</span>
            <span className="font-medium text-slate-900">
              {formatDateRange(startDate, endDate)}
            </span>
          </div>

          <div className="flex items-center gap-1">
            <span className="text-slate-400">•</span>
            <span className="font-semibold text-slate-700">District:</span>
            <span className="font-medium text-slate-900">
              {selectedDistrict && selectedDistrict !== "all"
                ? selectedDistrict
                : "All 38 Districts"}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="inline-flex items-center gap-1 rounded bg-sky-100 px-2 py-0.5 text-[11px] font-semibold text-sky-800">
            <Clock className="size-3" />
            IST (Asia/Kolkata)
          </span>
          {hasChanges && (
            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800">
              Unapplied Changes
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
