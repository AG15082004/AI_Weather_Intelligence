import { format, isValid, parseISO } from "date-fns";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HumidityData } from "@/types";

export interface HumidityChartProps {
  data: HumidityData[];
  height?: number;
}

function formatDateLabel(raw: string): string {
  if (!raw) return "";
  const parsed = parseISO(raw);
  if (isValid(parsed)) {
    return format(parsed, "MMM dd");
  }
  return raw;
}

export function HumidityChart({ data, height = 280 }: HumidityChartProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart
          data={data}
          margin={{ top: 10, right: 16, left: -8, bottom: 4 }}
        >
          <defs>
            <linearGradient id="humidityFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateLabel}
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={{ stroke: "#cbd5e1" }}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            unit="%"
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
            labelFormatter={(label) => formatDateLabel(String(label))}
            formatter={(value) => [`${Number(value).toFixed(1)}%`, "Relative Humidity"]}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
          <Area
            type="monotone"
            dataKey="humidity_pct"
            name="Humidity (%)"
            stroke="#10b981"
            strokeWidth={2.2}
            fill="url(#humidityFill)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
