/**
 * Date and Time utilities for Tamil Nadu Weather Intelligence Platform.
 * All operations are strictly anchored to Asia/Kolkata (IST = UTC+5:30).
 */

export interface DateRange {
  startDate: string; // YYYY-MM-DD
  endDate: string;   // YYYY-MM-DD
}

export type PresetKey =
  | "all"
  | "all_available"
  | "today"
  | "yesterday"
  | "last_7_days"
  | "last_15_days"
  | "last_30_days"
  | "last_90_days"
  | "this_week"
  | "last_week"
  | "this_month"
  | "last_month"
  | "this_year"
  | "custom";

export interface PresetOption {
  key: PresetKey;
  label: string;
  description: string;
}

export const DATE_PRESETS: PresetOption[] = [
  { key: "all", label: "All", description: "Complete historical data range across all observations" },
  { key: "today", label: "Today", description: "Current calendar date in IST" },
  { key: "yesterday", label: "Yesterday", description: "Previous calendar date in IST" },
  { key: "last_7_days", label: "Last 7 Days", description: "Past 7 days including today" },
  { key: "last_15_days", label: "Last 15 Days", description: "Past 15 days including today" },
  { key: "last_30_days", label: "Last 30 Days", description: "Past 30 days including today" },
  { key: "last_90_days", label: "Last 90 Days", description: "Past 90 days including today" },
  { key: "this_week", label: "This Week", description: "Monday of current week through today" },
  { key: "last_week", label: "Last Week", description: "Previous week (Mon – Sun)" },
  { key: "this_month", label: "This Month", description: "1st of current month through today" },
  { key: "last_month", label: "Last Month", description: "Full previous calendar month" },
  { key: "this_year", label: "This Year", description: "Jan 1 of current year through today" },
  { key: "custom", label: "Custom Range", description: "User specified date range" },
];

/**
 * Returns today's date formatted as YYYY-MM-DD in Asia/Kolkata timezone.
 */
export function getIstTodayStr(): string {
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
  return formatter.format(new Date());
}

/**
 * Helper to parse YYYY-MM-DD into a localized UTC Date object for math without local browser offset drift.
 */
function parseYmd(ymd: string): Date {
  const [y, m, d] = ymd.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

/**
 * Format UTC Date to YYYY-MM-DD.
 */
function toYmd(d: Date): string {
  const year = d.getUTCFullYear();
  const month = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Calculate the date range for any of the 13 supported presets in IST.
 */
export function getPresetDateRange(preset: PresetKey): DateRange {
  const todayStr = getIstTodayStr();
  const todayDate = parseYmd(todayStr);

  switch (preset) {
    case "today":
      return { startDate: todayStr, endDate: todayStr };

    case "yesterday": {
      const yesterday = new Date(todayDate);
      yesterday.setUTCDate(yesterday.getUTCDate() - 1);
      const yStr = toYmd(yesterday);
      return { startDate: yStr, endDate: yStr };
    }

    case "last_7_days": {
      const start = new Date(todayDate);
      start.setUTCDate(start.getUTCDate() - 6);
      return { startDate: toYmd(start), endDate: todayStr };
    }

    case "last_15_days": {
      const start = new Date(todayDate);
      start.setUTCDate(start.getUTCDate() - 14);
      return { startDate: toYmd(start), endDate: todayStr };
    }

    case "last_30_days": {
      const start = new Date(todayDate);
      start.setUTCDate(start.getUTCDate() - 29);
      return { startDate: toYmd(start), endDate: todayStr };
    }

    case "last_90_days": {
      const start = new Date(todayDate);
      start.setUTCDate(start.getUTCDate() - 89);
      return { startDate: toYmd(start), endDate: todayStr };
    }

    case "this_week": {
      // Monday = 1, Sunday = 0
      const day = todayDate.getUTCDay();
      const diffToMonday = day === 0 ? 6 : day - 1;
      const monday = new Date(todayDate);
      monday.setUTCDate(monday.getUTCDate() - diffToMonday);
      return { startDate: toYmd(monday), endDate: todayStr };
    }

    case "last_week": {
      const day = todayDate.getUTCDay();
      const diffToMonday = day === 0 ? 6 : day - 1;
      const thisMonday = new Date(todayDate);
      thisMonday.setUTCDate(thisMonday.getUTCDate() - diffToMonday);

      const lastMonday = new Date(thisMonday);
      lastMonday.setUTCDate(lastMonday.getUTCDate() - 7);

      const lastSunday = new Date(lastMonday);
      lastSunday.setUTCDate(lastSunday.getUTCDate() + 6);
      return { startDate: toYmd(lastMonday), endDate: toYmd(lastSunday) };
    }

    case "this_month": {
      const firstOfMonth = new Date(
        Date.UTC(todayDate.getUTCFullYear(), todayDate.getUTCMonth(), 1)
      );
      return { startDate: toYmd(firstOfMonth), endDate: todayStr };
    }

    case "last_month": {
      const firstOfLastMonth = new Date(
        Date.UTC(todayDate.getUTCFullYear(), todayDate.getUTCMonth() - 1, 1)
      );
      const lastOfLastMonth = new Date(
        Date.UTC(todayDate.getUTCFullYear(), todayDate.getUTCMonth(), 0)
      );
      return {
        startDate: toYmd(firstOfLastMonth),
        endDate: toYmd(lastOfLastMonth),
      };
    }

    case "this_year": {
      const firstOfYear = new Date(Date.UTC(todayDate.getUTCFullYear(), 0, 1));
      return { startDate: toYmd(firstOfYear), endDate: todayStr };
    }

    case "all":
    case "all_available":
      return { startDate: "", endDate: "" };

    case "custom":
    default:
      return { startDate: "", endDate: "" };
  }
}

/**
 * Validates start and end dates against IST rules.
 */
export function validateDateRange(
  startDate?: string,
  endDate?: string
): { valid: boolean; error?: string } {
  if (!startDate && !endDate) {
    return { valid: true };
  }
  const todayStr = getIstTodayStr();
  if (startDate && startDate > todayStr) {
    return { valid: false, error: "Start date cannot be in the future (IST)." };
  }
  if (endDate && endDate > todayStr) {
    return { valid: false, error: "End date cannot be in the future (IST)." };
  }
  if (startDate && endDate && startDate > endDate) {
    return { valid: false, error: "Start date cannot be later than end date." };
  }
  return { valid: true };
}

/**
 * Format date range for friendly header banner:
 * e.g. "November 6, 2026 – November 12, 2026"
 */
export function formatDateRange(
  startDate?: string,
  endDate?: string
): string {
  if (!startDate && !endDate) return "All Available Records";
  const options: Intl.DateTimeFormatOptions = {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  };
  const fmt = new Intl.DateTimeFormat("en-US", options);

  const startFmt = startDate ? fmt.format(parseYmd(startDate)) : "Earliest";
  const endFmt = endDate ? fmt.format(parseYmd(endDate)) : "Latest";

  if (startDate === endDate) return startFmt;
  return `${startFmt} – ${endFmt}`;
}

/**
 * Preset comparisons for Period A vs Period B.
 */
export interface ComparisonPreset {
  key: "today_vs_yesterday" | "this_week_vs_last_week" | "this_month_vs_last_month";
  label: string;
  periodA: DateRange;
  periodB: DateRange;
}

export function getComparisonPresets(): ComparisonPreset[] {
  const todayRange = getPresetDateRange("today");
  const yesterdayRange = getPresetDateRange("yesterday");
  const thisWeekRange = getPresetDateRange("this_week");
  const lastWeekRange = getPresetDateRange("last_week");
  const thisMonthRange = getPresetDateRange("this_month");
  const lastMonthRange = getPresetDateRange("last_month");

  return [
    {
      key: "today_vs_yesterday",
      label: "Today vs Yesterday",
      periodA: todayRange,
      periodB: yesterdayRange,
    },
    {
      key: "this_week_vs_last_week",
      label: "This Week vs Last Week",
      periodA: thisWeekRange,
      periodB: lastWeekRange,
    },
    {
      key: "this_month_vs_last_month",
      label: "This Month vs Last Month",
      periodA: thisMonthRange,
      periodB: lastMonthRange,
    },
  ];
}

