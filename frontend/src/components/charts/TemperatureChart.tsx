import { format, isValid, parseISO } from "date-fns";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TemperatureData } from "@/types";

export interface TemperatureChartProps {
  data: TemperatureData[];
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

export function TemperatureChart({ data, height = 300 }: TemperatureChartProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 10, right: 16, left: -8, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateLabel}
            tick={{ fontSize: 12, fill: "#64748b" }}
            axisLine={{ stroke: "#cbd5e1" }}
            tickLine={false}
          />
          <YAxis
            unit="°C"
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
            formatter={(value, name) => [`${Number(value).toFixed(1)} °C`, String(name)]}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
          <Line
            type="monotone"
            dataKey="max_temp"
            name="Max Temp"
            stroke="#f43f5e"
            strokeWidth={2.2}
            dot={{ r: 3, fill: "#f43f5e" }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="avg_temp"
            name="Avg Temp"
            stroke="#f59e0b"
            strokeWidth={2.2}
            dot={{ r: 3, fill: "#f59e0b" }}
            activeDot={{ r: 5 }}
          />
          <Line
            type="monotone"
            dataKey="min_temp"
            name="Min Temp"
            stroke="#3b82f6"
            strokeWidth={2.2}
            dot={{ r: 3, fill: "#3b82f6" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
