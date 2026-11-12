import { useMemo, useState } from "react";
import { Flame, Snowflake, Thermometer, TrendingUp } from "lucide-react";
import { getDistricts, getTemperature } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import {
  getSampleDistrictWeather,
  getSampleTemperatureTrend,
} from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { DateRangeFilter } from "@/components/common/DateRangeFilter";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { TemperatureChart } from "@/components/charts/TemperatureChart";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DateRangeParams, TemperatureData } from "@/types";

const COLUMNS: DataTableColumn<TemperatureData>[] = [
  { key: "date", header: "Date" },
  {
    key: "district",
    header: "District",
    render: (v) => (v ? String(v) : "State Average"),
  },
  {
    key: "max_temp",
    header: "Max (°C)",
    align: "right",
    render: (v) => (
      <span className="font-medium text-rose-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
  {
    key: "avg_temp",
    header: "Avg (°C)",
    align: "right",
    render: (v) => (
      <span className="font-medium text-amber-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
  {
    key: "min_temp",
    header: "Min (°C)",
    align: "right",
    render: (v) => (
      <span className="font-medium text-blue-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
];

export function TemperatureAnalytics() {
  const [district, setDistrict] = useState("all");
  const [startDate, setStartDate] = useState("2026-11-06");
  const [endDate, setEndDate] = useState("2026-11-12");
  const [previewSample, setPreviewSample] = useState(false);

  const params: DateRangeParams = {
    district: district === "all" ? undefined : district,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  };

  const { data: response, loading, error, refetch } = useApi(
    getTemperature,
    params
  );

  const { data: districtsResponse } = useApi(getDistricts);

  const activeRows = useMemo(() => {
    if (previewSample) {
      return getSampleTemperatureTrend(
        district === "all" ? undefined : district
      );
    }
    return response?.data ?? [];
  }, [previewSample, district, response?.data]);

  const districtBenchmarks = useMemo(() => {
    if (previewSample) {
      const all = getSampleDistrictWeather();
      if (district !== "all") {
        return all.filter((d) => d.district === district);
      }
      return all.slice(0, 10);
    }
    const all = districtsResponse?.data ?? [];
    if (district !== "all") {
      return all.filter((d) => d.district === district);
    }
    return all.slice(0, 10);
  }, [previewSample, districtsResponse?.data, district]);

  const stats = useMemo(() => {
    if (activeRows.length === 0) {
      return { avg: null, max: null, min: null, range: null };
    }
    const avg =
      activeRows.reduce((sum, r) => sum + r.avg_temp, 0) / activeRows.length;
    const max = Math.max(...activeRows.map((r) => r.max_temp));
    const min = Math.min(...activeRows.map((r) => r.min_temp));
    return {
      avg: avg.toFixed(1),
      max: max.toFixed(1),
      min: min.toFixed(1),
      range: (max - min).toFixed(1),
    };
  }, [activeRows]);

  const distributionBuckets = useMemo(() => {
    const buckets = [
      { range: "< 20°C", count: 0 },
      { range: "20-25°C", count: 0 },
      { range: "25-30°C", count: 0 },
      { range: "30-35°C", count: 0 },
      { range: "> 35°C", count: 0 },
    ];
    for (const row of activeRows) {
      const t = row.avg_temp;
      if (t < 20) buckets[0].count += 1;
      else if (t < 25) buckets[1].count += 1;
      else if (t < 30) buckets[2].count += 1;
      else if (t < 35) buckets[3].count += 1;
      else buckets[4].count += 1;
    }
    return buckets;
  }, [activeRows]);

  if (loading && !previewSample) {
    return <LoadingSkeleton variant="page" count={4} />;
  }

  if (error && !previewSample) {
    return (
      <ErrorState
        message={error}
        onRetry={() => void refetch()}
        onUseSample={() => setPreviewSample(true)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <DistrictFilter value={district} onChange={setDistrict} />
        </div>
        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          selectedDistrict={district}
          onApply={(start, end) => {
            setStartDate(start);
            setEndDate(end);
          }}
          onReset={() => {
            setStartDate("2026-11-06");
            setEndDate("2026-11-12");
          }}
        />
      </div>

      <FabricStatusBanner
        status={response?.status}
        isPreviewMode={previewSample}
        onTogglePreview={() => setPreviewSample((prev) => !prev)}
        onRefresh={() => void refetch()}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Mean Temperature"
          value={stats.avg ? `${stats.avg}°C` : "—"}
          subtitle={district === "all" ? "State average" : district}
          icon={Thermometer}
          accent="amber"
        />
        <KPICard
          title="Peak Maximum"
          value={stats.max ? `${stats.max}°C` : "—"}
          subtitle="Highest reading"
          icon={Flame}
          accent="rose"
        />
        <KPICard
          title="Minimum Recorded"
          value={stats.min ? `${stats.min}°C` : "—"}
          subtitle="Coolest reading"
          icon={Snowflake}
          accent="blue"
        />
        <KPICard
          title="Thermal Spread"
          value={stats.range ? `${stats.range}°C` : "—"}
          subtitle="Max - Min variance"
          icon={TrendingUp}
          accent="emerald"
        />
      </div>

      {activeRows.length === 0 ? (
        <EmptyState
          title="No Temperature Readings Available"
          message="Temperature analytics will populate automatically once Microsoft Fabric SQL data is synced."
          actionLabel="Preview Sample Temperature Analytics"
          onAction={() => setPreviewSample(true)}
        />
      ) : (
        <>
          <ChartCard
            title="Daily & Monthly Temperature Trends"
            subtitle="Maximum, average, and minimum temperature trajectory"
          >
            <TemperatureChart data={activeRows} height={320} />
          </ChartCard>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard
              title="Temperature Distribution"
              subtitle="Observation frequency grouped by temperature band"
            >
              <div style={{ width: "100%", height: 290 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={distributionBuckets}
                    margin={{ top: 10, right: 16, left: -12, bottom: 4 }}
                  >
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#e2e8f0"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="range"
                      tick={{ fontSize: 12, fill: "#64748b" }}
                      axisLine={{ stroke: "#cbd5e1" }}
                      tickLine={false}
                    />
                    <YAxis
                      allowDecimals={false}
                      tick={{ fontSize: 12, fill: "#64748b" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip />
                    <Bar
                      dataKey="count"
                      name="Intervals"
                      fill="#f59e0b"
                      radius={[6, 6, 0, 0]}
                      maxBarSize={48}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard
              title="District Thermal Comparison"
              subtitle="Max, average, and min temperatures across districts"
            >
              <ComparisonChart
                data={districtBenchmarks}
                height={290}
                series={[
                  { dataKey: "max_temp", label: "Max (°C)", color: "#f43f5e" },
                  { dataKey: "avg_temp", label: "Avg (°C)", color: "#f59e0b" },
                  { dataKey: "min_temp", label: "Min (°C)", color: "#3b82f6" },
                ]}
              />
            </ChartCard>
          </div>

          <ChartCard
            title="Temperature Readings Log"
            subtitle="Sortable tabular view of temperature observations"
          >
            <DataTable
              data={activeRows}
              columns={COLUMNS}
              searchPlaceholder="Filter by date or district..."
            />
          </ChartCard>
        </>
      )}
    </div>
  );
}
