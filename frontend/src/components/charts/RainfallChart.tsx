import { format, isValid, parseISO } from "date-fns";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Info } from "lucide-react";
import type { RainfallData } from "@/types";

export interface RainfallChartProps {
  data: RainfallData[];
  height?: number;
  xKey?: "date" | "district";
  completenessPct?: number;
}

function formatXLabel(raw: string, xKey: "date" | "district"): string {
  if (!raw) return "";
  if (xKey === "date") {
    const parsed = parseISO(raw);
    if (isValid(parsed)) {
      return format(parsed, "MMM dd");
    }
  }
  return raw;
}

export function RainfallChart({
  data,
  height = 300,
  xKey = "date",
  completenessPct,
}: RainfallChartProps) {
  const hasValidMeasurements = data.some(
    (d) => d.rainfall_mm !== null && d.rainfall_mm !== undefined && !Number.isNaN(d.rainfall_mm)
  );

  if (!data.length || !hasValidMeasurements) {
    return (
      <div
        className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 bg-slate-50/60 p-6 text-center"
        style={{ height }}
      >
        <div className="flex size-10 items-center justify-center rounded-full bg-amber-100 text-amber-600">
          <Info className="size-5" />
        </div>
        <h4 className="mt-3 text-xs font-semibold text-slate-800">
          Rainfall Measurements Unavailable
        </h4>
        <p className="mt-1 max-w-sm text-xs text-slate-500">
          Open-Meteo ERA5-Land model reports NULL precipitation for historical dates.
          Real rainfall measurements exist for current observation telemetry (Nov 10–12, 2026).
        </p>
      </div>
    );
  }

  // Sanitize data for Recharts, preserving 0 as 0 and null as null
  const sanitizedData = data.map((d) => ({
    ...d,
    rainfall_mm: d.rainfall_mm ?? 0,
    isUnmeasured: d.rainfall_mm === null || d.rainfall_mm === undefined,
  }));

  return (
    <div style={{ width: "100%", height }} className="relative">
      {completenessPct !== undefined && completenessPct < 100 && (
        <div className="absolute top-0 right-2 z-10 rounded bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
          Reporting Completeness: {completenessPct.toFixed(0)}%
        </div>
      )}
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={sanitizedData}
          margin={{ top: 10, right: 16, left: -4, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey={xKey}
            tickFormatter={(val) => formatXLabel(String(val), xKey)}
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={{ stroke: "#cbd5e1" }}
            tickLine={false}
          />
          <YAxis
            unit=" mm"
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#ffffff",
              borderColor: "#e2e8f0",
              borderRadius: "8px",
              boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)",
              fontSize: "12px",
            }}
            labelFormatter={(label) => formatXLabel(String(label), xKey)}
            formatter={(value, _name, item) => {
              if (item?.payload?.isUnmeasured) {
                return ["Unmeasured (NULL)", "Rainfall"];
              }
              return [`${Number(value).toFixed(2)} mm`, "Rainfall"];
            }}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
          <Bar
            dataKey="rainfall_mm"
            name="Rainfall (mm)"
            fill="#3b82f6"
            radius={[6, 6, 0, 0]}
            maxBarSize={42}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
