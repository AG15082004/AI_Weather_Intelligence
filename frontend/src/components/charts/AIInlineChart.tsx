import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Check, Copy, TrendingUp } from "lucide-react";
import type { ChartSpec } from "@/types";

interface AIInlineChartProps {
  spec: ChartSpec;
  height?: number;
}

// Professional Microsoft Weather Analytics palette
const MICROSOFT_WEATHER_PALETTE = [
  "#f97316", // Temperature Primary (Orange)
  "#0ea5e9", // Rainfall Primary (Sky/Blue)
  "#0d9488", // Humidity Primary (Teal)
  "#8b5cf6", // AQI Primary (Purple)
  "#16a34a", // Normal/Good (Green)
  "#d97706", // Warning (Amber)
  "#dc2626", // Critical (Red)
];

export function AIInlineChart({ spec, height = 260 }: AIInlineChartProps) {
  const { type, title, x_axis, y_axis, series, data } = spec;
  const [copied, setCopied] = useState(false);

  const shouldRotateLabels = useMemo(() => {
    if (!data || data.length === 0) return false;
    const hasLongName = data.some((d) => String(d[x_axis] || "").length > 6);
    return data.length > 4 || hasLongName;
  }, [data, x_axis]);

  const resolvedSeries = useMemo(() => {
    if (series && series.length > 0) {
      return series.map((s, idx) => ({
        ...s,
        color: s.color || MICROSOFT_WEATHER_PALETTE[idx % MICROSOFT_WEATHER_PALETTE.length],
      }));
    }
    // Infer from data if series not explicitly defined
    if (data && data.length > 0) {
      const keys = Object.keys(data[0]).filter((k) => k !== x_axis);
      return keys.map((k, idx) => ({
        name: k,
        key: k,
        color: MICROSOFT_WEATHER_PALETTE[idx % MICROSOFT_WEATHER_PALETTE.length],
      }));
    }
    return [];
  }, [series, data, x_axis]);

  const handleCopyData = () => {
    if (!data) return;
    const text = JSON.stringify(data, null, 2);
    if (navigator?.clipboard) {
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  if (!data || data.length === 0) {
    return null;
  }

  const chartHeight = shouldRotateLabels ? Math.max(height, 275) : height;

  const formatTooltip = (val: unknown, name: unknown) => {
    if (val == null) return ["Unmeasured", String(name)];
    const num = Number(val);
    if (isNaN(num)) return [String(val), String(name)];

    const nameStr = String(name || "").toLowerCase();
    const titleStr = (title || "").toLowerCase();

    if (nameStr.includes("temp") || titleStr.includes("temp") || titleStr.includes("hot") || titleStr.includes("cool")) {
      return [`${num.toFixed(1)} °C`, String(name)];
    }
    if (nameStr.includes("rain") || titleStr.includes("rain") || titleStr.includes("precip")) {
      return [`${num.toFixed(1)} mm`, String(name)];
    }
    if (nameStr.includes("humid") || titleStr.includes("humid")) {
      return [`${num.toFixed(0)} %`, String(name)];
    }
    if (nameStr.includes("aqi") || titleStr.includes("aqi") || titleStr.includes("air")) {
      return [`${num.toFixed(0)} AQI`, String(name)];
    }
    return [num.toFixed(1), String(name)];
  };

  return (
    <div className="mt-3.5 overflow-hidden rounded-xl border border-slate-200/90 bg-white shadow-xs">
      {/* Chart Header */}
      <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50/60 px-4 py-2.5">
        <div className="flex items-center gap-2">
          {type === "line" || type === "area" ? (
            <TrendingUp className="size-4 text-blue-600" />
          ) : (
            <BarChart3 className="size-4 text-blue-600" />
          )}
          <h4 className="text-xs font-bold tracking-tight text-slate-900">{title}</h4>
        </div>
        <div className="flex items-center gap-2">
          {y_axis && (
            <span className="rounded bg-slate-200/70 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
              {y_axis}
            </span>
          )}
          <button
            type="button"
            onClick={handleCopyData}
            className="flex items-center gap-1 rounded p-1 text-[11px] text-slate-400 hover:bg-slate-200/60 hover:text-slate-700 transition-colors"
            title="Copy chart data (JSON)"
          >
            {copied ? (
              <>
                <Check className="size-3 text-emerald-600" />
                <span className="text-[10px] text-emerald-600">Copied</span>
              </>
            ) : (
              <Copy className="size-3" />
            )}
          </button>
        </div>
      </div>

      {/* Chart Area */}
      <div className="p-3 pt-4" style={{ width: "100%", height: chartHeight }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === "line" ? (
            <LineChart
              data={data}
              margin={{
                top: 8,
                right: 16,
                left: -12,
                bottom: shouldRotateLabels ? 36 : 10,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey={x_axis}
                interval={0}
                angle={shouldRotateLabels ? -28 : 0}
                textAnchor={shouldRotateLabels ? "end" : "middle"}
                height={shouldRotateLabels ? 45 : 25}
                tick={{ fontSize: 11, fill: "#475569", fontWeight: 500 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={formatTooltip}
                contentStyle={{
                  backgroundColor: "#ffffff",
                  borderRadius: "8px",
                  borderColor: "#e2e8f0",
                  fontSize: "12px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
              {resolvedSeries.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.name}
                  stroke={s.color}
                  strokeWidth={2.5}
                  dot={{ r: 3.5, strokeWidth: 1.5, fill: "#ffffff" }}
                  activeDot={{ r: 5 }}
                />
              ))}
            </LineChart>
          ) : type === "area" ? (
            <AreaChart
              data={data}
              margin={{
                top: 8,
                right: 16,
                left: -12,
                bottom: shouldRotateLabels ? 36 : 10,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey={x_axis}
                interval={0}
                angle={shouldRotateLabels ? -28 : 0}
                textAnchor={shouldRotateLabels ? "end" : "middle"}
                height={shouldRotateLabels ? 45 : 25}
                tick={{ fontSize: 11, fill: "#475569", fontWeight: 500 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={formatTooltip}
                contentStyle={{
                  backgroundColor: "#ffffff",
                  borderRadius: "8px",
                  borderColor: "#e2e8f0",
                  fontSize: "12px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
              {resolvedSeries.map((s) => (
                <Area
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.name}
                  stroke={s.color}
                  strokeWidth={2}
                  fill={s.color}
                  fillOpacity={0.2}
                />
              ))}
            </AreaChart>
          ) : (
            <BarChart
              data={data}
              margin={{
                top: 8,
                right: 16,
                left: -12,
                bottom: shouldRotateLabels ? 38 : 10,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
              <XAxis
                dataKey={x_axis}
                interval={0}
                angle={shouldRotateLabels ? -28 : 0}
                textAnchor={shouldRotateLabels ? "end" : "middle"}
                height={shouldRotateLabels ? 48 : 25}
                tick={{ fontSize: 11, fill: "#475569", fontWeight: 500 }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "#64748b" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                formatter={formatTooltip}
                contentStyle={{
                  backgroundColor: "#ffffff",
                  borderRadius: "8px",
                  borderColor: "#e2e8f0",
                  fontSize: "12px",
                  boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                }}
              />
              <Legend wrapperStyle={{ fontSize: "11px", paddingTop: "6px" }} />
              {resolvedSeries.map((s) => (
                <Bar
                  key={s.key}
                  dataKey={s.key}
                  name={s.name}
                  fill={s.color}
                  radius={[5, 5, 0, 0]}
                  maxBarSize={42}
                />
              ))}
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
