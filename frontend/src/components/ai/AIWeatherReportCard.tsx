import React, { useMemo } from "react";
import {
  CloudSun,
  Thermometer,
  CloudRain,
  Wind,
  Droplets,
  Layers,
  MapPin,
  Clock,
  Database,
  Check,
  Copy,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AIInlineChart } from "@/components/charts/AIInlineChart";
import type { ChartSpec } from "@/types";

interface AIWeatherReportCardProps {
  content: string;
  chart?: ChartSpec | null;
  sources?: string[];
  intent?: string | null;
  district?: string | null;
  timestamp?: string | null;
  isError?: boolean;
}

/**
 * Format raw technical source names into clean user-friendly badges.
 * Strips database, schema, and table names such as [dbo].[gold_...].
 */
export function formatUserFriendlySource(rawSource?: string): string {
  if (!rawSource) return "Live Weather Observations";
  const s = rawSource.toLowerCase();
  if (s.includes("air_quality") || s.includes("aqi")) return "Air Quality Data";
  if (s.includes("rainfall")) return "Rainfall Intelligence";
  if (s.includes("daily") || s.includes("monthly") || s.includes("historical")) return "Historical Weather Data";
  if (s.includes("dim_district") || s.includes("registry") || s.includes("geolocation")) return "District Directory";
  if (s.includes("current") || s.includes("silver") || s.includes("gold_current")) return "Live Weather Observations";

  // Clean any remaining brackets or SQL artifacts
  const cleaned = rawSource
    .replace(/\[?dbo\]?\.?\[?[a-zA-Z0-9_]+\]?/gi, "")
    .replace(/Microsoft Fabric/gi, "Weather Platform")
    .replace(/Lakehouse/gi, "")
    .replace(/[\[\]\(\)]/g, "")
    .trim();

  return cleaned || "Live Weather Observations";
}

interface ParsedReport {
  title: string;
  leadParagraph: string;
  metrics: Array<{
    label: string;
    value: string;
    unit?: string;
    icon: React.ReactNode;
    color: string;
    sublabel?: string;
  }>;
  bulletPoints: string[];
  footerNote?: string;
}

/**
 * Strip technical database table names and schemas from text content.
 */
function cleanReportText(str: string): string {
  if (!str) return "";
  return str
    .replace(/Microsoft Fabric\s*\[?dbo\]?\.?\[?[a-zA-Z0-9_]+\]?/gi, "Live Weather Observations")
    .replace(/\[dbo\]\.\[?[a-zA-Z0-9_]+\]?/gi, "Weather Intelligence")
    .replace(/\[dbo\]\./gi, "");
}

export function AIWeatherReportCard({
  content,
  chart,
  sources,
  intent,
  district,
  timestamp,
  isError,
}: AIWeatherReportCardProps) {
  const [copied, setCopied] = React.useState(false);

  const cleanSource = useMemo(() => {
    return formatUserFriendlySource(sources && sources.length > 0 ? sources[0] : undefined);
  }, [sources]);

  const parsed = useMemo<ParsedReport>(() => {
    const lines = content.split("\n").map((l) => cleanReportText(l.trim())).filter(Boolean);
    let title = "Weather Intelligence Report";
    const bulletPoints: string[] = [];
    const leadLines: string[] = [];
    let footerNote: string | undefined;

    const metricsMap: Record<string, { label: string; value: string; unit?: string; icon: React.ReactNode; color: string; sublabel?: string }> = {};

    for (const line of lines) {
      // Header detection (### Title or **Title**)
      if (line.startsWith("###")) {
        title = line.replace(/^###\s*/, "").replace(/\*\*/g, "").trim();
        continue;
      }
      if (line.startsWith("**") && line.endsWith("**:") && !title) {
        title = line.replace(/\*\*/g, "").replace(/:$/, "").trim();
        continue;
      }

      // Footer audit provenance line (*Data source:...*)
      if (line.startsWith("*Data source:") || line.includes("Observation time:")) {
        footerNote = line.replace(/^\*|\*$/g, "").trim();
        continue;
      }

      // Bullet points
      if (line.startsWith("- ") || line.startsWith("* ")) {
        const text = line.replace(/^[-*]\s*/, "");

        // Extract structured metric tiles if present
        const lower = text.toLowerCase();
        if (lower.includes("average temperature:") || lower.includes("temperature:")) {
          const match = text.match(/(?:Average\s+)?Temperature:\s*\*\*?([0-9.]+)\s*°?C?\*\*?(?:\s*\((.*?)\))?/i);
          if (match) {
            metricsMap["temp"] = {
              label: "Avg Temperature",
              value: `${match[1]}°C`,
              icon: <Thermometer className="size-4 text-orange-500" />,
              color: "text-orange-600 bg-orange-50/70 border-orange-200/80",
              sublabel: match[2] || undefined,
            };
          }
        }
        if (lower.includes("humidity:") || lower.includes("relative humidity:")) {
          const match = text.match(/(?:Relative\s+)?Humidity:\s*\*\*?([0-9.]+)\s*%?\*\*?/i);
          if (match) {
            metricsMap["humidity"] = {
              label: "Avg Humidity",
              value: `${match[1]}%`,
              icon: <Droplets className="size-4 text-teal-600" />,
              color: "text-teal-700 bg-teal-50/70 border-teal-200/80",
            };
          }
        }
        if (lower.includes("rainfall:") || lower.includes("total rainfall:")) {
          const match = text.match(/(?:Total\s+)?Rainfall:\s*\*\*?(.*?)\*\*?$/i);
          if (match) {
            const rawVal = match[1].trim();
            const isUnmeasured = rawVal.toLowerCase().includes("unmeasured") || rawVal.toLowerCase().includes("missing");
            metricsMap["rainfall"] = {
              label: "Total Rainfall",
              value: isUnmeasured ? "Unmeasured" : rawVal.endsWith("mm") ? rawVal : `${rawVal} mm`,
              icon: <CloudRain className="size-4 text-sky-600" />,
              color: "text-sky-700 bg-sky-50/70 border-sky-200/80",
              sublabel: isUnmeasured ? "Data quality: Unmeasured" : undefined,
            };
          }
        }
        if (lower.includes("districts reporting:")) {
          const match = text.match(/Districts Reporting:\s*\*\*?(.*?)\*\*?$/i);
          if (match) {
            metricsMap["districts"] = {
              label: "Districts Active",
              value: match[1],
              icon: <MapPin className="size-4 text-blue-600" />,
              color: "text-blue-700 bg-blue-50/70 border-blue-200/80",
            };
          }
        }

        bulletPoints.push(text);
      } else {
        leadLines.push(line);
      }
    }

    return {
      title,
      leadParagraph: leadLines.join("\n\n"),
      metrics: Object.values(metricsMap),
      bulletPoints,
      footerNote,
    };
  }, [content]);

  const handleCopyText = () => {
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(content).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  const getHeaderIcon = () => {
    const t = parsed.title.toLowerCase();
    const i = (intent || "").toLowerCase();
    if (t.includes("rain") || i.includes("rain")) return <CloudRain className="size-4.5 text-sky-600" />;
    if (t.includes("hot") || t.includes("temp") || i.includes("temp")) return <Thermometer className="size-4.5 text-orange-500" />;
    if (t.includes("aqi") || t.includes("air") || i.includes("air")) return <Wind className="size-4.5 text-purple-600" />;
    if (t.includes("compare") || i.includes("comparison")) return <Layers className="size-4.5 text-blue-600" />;
    return <CloudSun className="size-4.5 text-blue-600" />;
  };

  if (isError) {
    return (
      <div className="space-y-2 text-sm leading-relaxed text-red-900">
        <div className="font-semibold text-red-800">Weather Intelligence Notice</div>
        <div>{content}</div>
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {/* Report Header */}
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex size-7 items-center justify-center rounded-md bg-slate-100/90 text-slate-700 shadow-2xs">
            {getHeaderIcon()}
          </div>
          <div>
            <h3 className="text-sm font-bold tracking-tight text-slate-900">{parsed.title}</h3>
            {district && (
              <span className="text-[11px] font-medium text-slate-500">
                District: <span className="font-semibold text-slate-700">{district}</span>
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={handleCopyText}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
          title="Copy response report"
        >
          {copied ? (
            <>
              <Check className="size-3 text-emerald-600" />
              <span className="text-[10px] text-emerald-600 font-medium">Copied</span>
            </>
          ) : (
            <>
              <Copy className="size-3" />
              <span className="text-[10px]">Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Key Metric Cards (Microsoft Fluent Tiles) */}
      {parsed.metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {parsed.metrics.map((m) => (
            <div
              key={m.label}
              className={`rounded-lg border p-2.5 shadow-2xs transition-all ${m.color}`}
            >
              <div className="flex items-center justify-between text-[11px] font-medium text-slate-600">
                <span>{m.label}</span>
                {m.icon}
              </div>
              <div className="mt-1 text-base font-bold tracking-tight text-slate-900">{m.value}</div>
              {m.sublabel && (
                <div className="mt-0.5 text-[10px] text-slate-500 font-normal truncate">
                  {m.sublabel}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Lead Text / Executive Summary */}
      {parsed.leadParagraph && (
        <div className="text-xs leading-relaxed text-slate-700 font-normal whitespace-pre-wrap">
          {parsed.leadParagraph}
        </div>
      )}

      {/* Structured Insights & Observations */}
      {parsed.bulletPoints.length > 0 && parsed.metrics.length === 0 && (
        <div className="space-y-1.5 rounded-lg bg-slate-50/70 p-3 border border-slate-200/60">
          <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
            Telemetry Insights
          </div>
          <ul className="space-y-1 text-xs text-slate-700">
            {parsed.bulletPoints.map((b, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span className="text-blue-500 font-bold">•</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Inline Chart Spec Renderer */}
      {chart && <AIInlineChart spec={chart} />}

      {/* Metadata & Clean Provenance Footer */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2 text-[11px] text-slate-500">
        <Badge
          variant="secondary"
          className="bg-sky-50 text-sky-800 border border-sky-200/70 text-[10px] font-medium px-2 py-0.5 flex items-center gap-1"
        >
          <Database className="size-2.5 text-sky-600" />
          {cleanSource}
        </Badge>

        {intent && (
          <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] text-slate-600 font-medium">
            {intent.replace(/_/g, " ")}
          </span>
        )}

        <div className="ml-auto flex items-center gap-1 text-[10px] text-slate-400">
          <Clock className="size-2.5" />
          <span>{timestamp || "Live"} (IST)</span>
        </div>
      </div>
    </div>
  );
}
