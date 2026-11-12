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

export interface ComparisonBarSeries {
  dataKey: string;
  label: string;
  color: string;
  unit?: string;
}

export interface ComparisonChartProps<T extends object> {
  data: T[];
  xKey?: string;
  series?: ComparisonBarSeries[];
  height?: number;
}

const DEFAULT_SERIES: ComparisonBarSeries[] = [
  { dataKey: "max_temp", label: "Max Temp (°C)", color: "#f43f5e", unit: "°C" },
  { dataKey: "avg_temp", label: "Avg Temp (°C)", color: "#f59e0b", unit: "°C" },
  { dataKey: "avg_humidity", label: "Humidity (%)", color: "#3b82f6", unit: "%" },
];

export function ComparisonChart<T extends object>({
  data,
  xKey = "district",
  series = DEFAULT_SERIES,
  height = 320,
}: ComparisonChartProps<T>) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 10, right: 16, left: -4, bottom: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis
            dataKey={xKey}
            tick={{ fontSize: 11, fill: "#64748b" }}
            axisLine={{ stroke: "#cbd5e1" }}
            tickLine={false}
            interval={0}
            angle={-20}
            textAnchor="end"
            height={52}
          />
          <YAxis
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
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "8px" }} />
          {series.map((bar) => (
            <Bar
              key={bar.dataKey}
              dataKey={bar.dataKey}
              name={bar.label}
              fill={bar.color}
              radius={[4, 4, 0, 0]}
              maxBarSize={26}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
