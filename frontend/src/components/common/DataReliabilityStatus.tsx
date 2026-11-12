import {
  CheckCircle2,
  Clock,
  Database,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Layers,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { DataStatus, ReliabilitySummary } from "@/types";

interface DataReliabilityStatusProps {
  status?: DataStatus;
  dataSource?: string;
  lastRefresh?: string | null;
  dataAgeSeconds?: number | null;
  isStale?: boolean;
  warning?: string | null;
  reliabilitySummary?: ReliabilitySummary | null;
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

export function formatDataAge(seconds?: number | null): string {
  if (seconds == null || seconds < 0) return "Recent";
  if (seconds < 60) return `${Math.round(seconds)}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ${minutes % 60}m ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ${hours % 24}h ago`;
}

export function DataReliabilityStatus({
  status = "LIVE",
  dataSource = "Microsoft Fabric Lakehouse",
  lastRefresh,
  dataAgeSeconds,
  isStale = false,
  warning,
  reliabilitySummary,
  onRefresh,
  isRefreshing = false,
}: DataReliabilityStatusProps) {
  // Use summary status if available, otherwise prop status
  const effectiveStatus: DataStatus = reliabilitySummary?.overall_status || status;
  const effectiveSource: string = reliabilitySummary?.overall_source || dataSource;
  const effectiveRefresh: string =
    reliabilitySummary?.last_successful_refresh || lastRefresh || "Asia/Kolkata IST";
  const effectiveStale: boolean =
    reliabilitySummary?.is_stale !== undefined ? reliabilitySummary.is_stale : isStale;

  const renderStatusBadge = () => {
    switch (effectiveStatus) {
      case "LIVE":
        return (
          <Badge className="gap-1.5 border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800 shadow-2xs">
            <span className="relative flex size-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex size-2 rounded-full bg-emerald-500"></span>
            </span>
            <CheckCircle2 className="size-3 text-emerald-600" />
            LIVE FABRIC
          </Badge>
        );
      case "CACHED":
        return (
          <Badge className="gap-1.5 border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-semibold text-amber-800 shadow-2xs">
            <Clock className="size-3 text-amber-600" />
            CACHED {dataAgeSeconds ? `(${formatDataAge(dataAgeSeconds)})` : ""}
          </Badge>
        );
      case "FALLBACK":
        return (
          <Badge className="gap-1.5 border-slate-300 bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 shadow-2xs">
            <HelpCircle className="size-3 text-slate-500" />
            FALLBACK (SIMULATED)
          </Badge>
        );
      case "UNAVAILABLE":
      default:
        return (
          <Badge className="gap-1.5 border-rose-300 bg-rose-50 px-2.5 py-0.5 text-xs font-semibold text-rose-800 shadow-2xs">
            <XCircle className="size-3 text-rose-600" />
            UNAVAILABLE (OFFLINE)
          </Badge>
        );
    }
  };

  const getSourceIconColor = () => {
    switch (effectiveStatus) {
      case "LIVE":
        return "text-emerald-600 bg-emerald-50 border-emerald-200";
      case "CACHED":
        return "text-amber-600 bg-amber-50 border-amber-200";
      case "FALLBACK":
        return "text-slate-600 bg-slate-50 border-slate-200";
      case "UNAVAILABLE":
        return "text-rose-600 bg-rose-50 border-rose-200";
    }
  };

  return (
    <Card className="overflow-hidden border-slate-200/90 bg-white shadow-xs">
      {/* Subtle warning banner when data is stale or cached */}
      {(effectiveStale || effectiveStatus === "CACHED") && (
        <div className="flex items-center gap-2 border-b border-amber-200 bg-amber-50/90 px-4 py-2 text-xs font-medium text-amber-800">
          <AlertTriangle className="size-4 shrink-0 text-amber-600" />
          <span>
            {warning ||
              `Displaying cached data from ${effectiveRefresh}. Live Microsoft Fabric refresh is pending.`}
          </span>
        </div>
      )}

      {/* Red Alert Banner when data is UNAVAILABLE */}
      {effectiveStatus === "UNAVAILABLE" && (
        <div className="flex items-center gap-2 border-b border-rose-200 bg-rose-50 px-4 py-2.5 text-xs font-medium text-rose-800">
          <XCircle className="size-4 shrink-0 text-rose-600" />
          <span>
            {warning ||
              "Microsoft Fabric Lakehouse is currently unreachable and no cache is present. Metrics are marked as Data Offline (N/A) without generating fabricated data."}
          </span>
        </div>
      )}

      <CardContent className="p-3.5 sm:p-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          {/* Left Column: Data Origin & Badge */}
          <div className="flex items-center gap-3">
            <div
              className={`flex size-9 items-center justify-center rounded-lg border ${getSourceIconColor()}`}
            >
              <Database className="size-4.5" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Data Reliability Status
                </span>
                {renderStatusBadge()}
              </div>
              <p className="text-sm font-medium text-slate-800">
                Source: <span className="font-semibold">{effectiveSource}</span>
              </p>
            </div>
          </div>

          {/* Right Column: Metadata pills & Actions */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
            {lastRefresh && (
              <div className="flex items-center gap-1.5 rounded-md bg-slate-50 px-2.5 py-1 ring-1 ring-slate-200">
                <Clock className="size-3.5 text-slate-400" />
                <span>
                  Refreshed:{" "}
                  <strong className="font-medium text-slate-700">
                    {effectiveRefresh}
                  </strong>
                </span>
              </div>
            )}

            {dataAgeSeconds != null && (
              <div className="flex items-center gap-1.5 rounded-md bg-slate-50 px-2.5 py-1 ring-1 ring-slate-200">
                <span>
                  Age:{" "}
                  <strong className="font-medium text-slate-700">
                    {formatDataAge(dataAgeSeconds)}
                  </strong>
                </span>
              </div>
            )}

            {reliabilitySummary?.datasets && (
              <div className="hidden items-center gap-1 rounded-md bg-blue-50/70 px-2.5 py-1 text-blue-700 ring-1 ring-blue-200 md:flex">
                <Layers className="size-3.5 text-blue-600" />
                <span>
                  Gold Tables:{" "}
                  <strong className="font-semibold text-blue-800">
                    {Object.keys(reliabilitySummary.datasets).length} tracked
                  </strong>
                </span>
              </div>
            )}

            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                disabled={isRefreshing}
                className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 disabled:opacity-50"
                title="Trigger data reliability check"
              >
                <RefreshCw
                  className={`size-3 text-slate-500 ${isRefreshing ? "animate-spin" : ""}`}
                />
                Refresh
              </button>
            )}
          </div>
        </div>

        {/* Dataset breakdown if summary is present */}
        {reliabilitySummary?.datasets && (
          <div className="mt-3 border-t border-slate-100 pt-2.5">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-slate-500">
              <span className="font-medium text-slate-600">Freshness Tracking:</span>
              {Object.entries(reliabilitySummary.datasets).map(([name, ds]) => {
                const label = name.replace("gold_", "").replace("_analytics", "").replace("_latest", "");
                const isDsLive = ds.status === "LIVE";
                return (
                  <span key={name} className="flex items-center gap-1">
                    <span
                      className={`size-1.5 rounded-full ${
                        isDsLive ? "bg-emerald-500" : ds.status === "CACHED" ? "bg-amber-400" : "bg-rose-400"
                      }`}
                    />
                    <span className="font-mono text-slate-600">{label}:</span>
                    <span className={isDsLive ? "text-emerald-700 font-medium" : "text-amber-700"}>
                      {ds.status}
                    </span>
                  </span>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
