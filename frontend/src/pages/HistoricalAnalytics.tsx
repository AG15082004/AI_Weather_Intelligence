import { useMemo, useState } from "react";
import {
  Calendar,
  Database,
  Flame,
  Snowflake,
  Thermometer,
} from "lucide-react";
import { getRainfall, getTemperature } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
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
import { RainfallChart } from "@/components/charts/RainfallChart";
import type { DateRangeParams, TemperatureData } from "@/types";

const HISTORICAL_COLUMNS: DataTableColumn<TemperatureData>[] = [
  { key: "date", header: "Observation Date" },
  {
    key: "district",
    header: "District",
    render: (v) => (v ? String(v) : "Statewide"),
  },
  {
    key: "max_temp",
    header: "Peak Temp (°C)",
    align: "right",
    render: (v) => (
      <span className="font-semibold text-rose-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
  {
    key: "avg_temp",
    header: "Mean Temp (°C)",
    align: "right",
    render: (v) => (
      <span className="font-medium text-amber-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
  {
    key: "min_temp",
    header: "Low Temp (°C)",
    align: "right",
    render: (v) => (
      <span className="font-medium text-blue-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
];

export function HistoricalAnalytics() {
  const [district, setDistrict] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [previewSample, setPreviewSample] = useState(false);

  const params: DateRangeParams = {
    district: district === "all" ? undefined : district,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  };

  const {
    data: tempRes,
    loading: tempLoading,
    error: tempError,
    refetch: refetchTemp,
  } = useApi(getTemperature, params);

  const {
    data: rainRes,
    refetch: refetchRain,
  } = useApi(getRainfall, params);

  const activeRows = useMemo(() => tempRes?.data ?? [], [tempRes?.data]);
  const activeRainRows = useMemo(() => rainRes?.data ?? [], [rainRes?.data]);

  const stats = useMemo(() => {
    if (activeRows.length === 0) {
      return { count: 0, avg: null, max: null, min: null };
    }
    const count = activeRows.length;
    const avg = activeRows.reduce((s, r) => s + r.avg_temp, 0) / count;
    const max = Math.max(...activeRows.map((r) => r.max_temp));
    const min = Math.min(...activeRows.map((r) => r.min_temp));
    return {
      count,
      avg: avg.toFixed(1),
      max: max.toFixed(1),
      min: min.toFixed(1),
    };
  }, [activeRows]);

  if (tempLoading && activeRows.length === 0) {
    return <LoadingSkeleton variant="page" count={4} />;
  }

  if (tempError && activeRows.length === 0) {
    return (
      <ErrorState
        message={tempError}
        onRetry={() => {
          void refetchTemp();
          void refetchRain();
        }}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-slate-900">
                Historical Weather Observations
              </h2>
              <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700 ring-1 ring-blue-700/10">
                Fabric Lakehouse Archive
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Multi-month Open-Meteo & WeatherAPI climate archives across all 38 districts
            </p>
          </div>

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
            setStartDate("");
            setEndDate("");
            setDistrict("all");
          }}
        />
      </div>

      <FabricStatusBanner
        status={tempRes?.status}
        isPreviewMode={previewSample}
        onTogglePreview={() => setPreviewSample((prev) => !prev)}
        onRefresh={() => {
          void refetchTemp();
          void refetchRain();
        }}
      />

      {/* Historical KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Observations Queried"
          value={stats.count ? `${stats.count.toLocaleString()} rows` : "—"}
          subtitle="Filtered window"
          icon={Database}
          accent="blue"
        />
        <KPICard
          title="Period Mean Temp"
          value={stats.avg ? `${stats.avg}°C` : "—"}
          subtitle={district === "all" ? "Statewide historical" : district}
          icon={Thermometer}
          accent="amber"
        />
        <KPICard
          title="Historical High"
          value={stats.max ? `${stats.max}°C` : "—"}
          subtitle="Peak in interval"
          icon={Flame}
          accent="rose"
        />
        <KPICard
          title="Historical Low"
          value={stats.min ? `${stats.min}°C` : "—"}
          subtitle="Minimum recorded"
          icon={Snowflake}
          accent="cyan"
        />
      </div>

      {activeRows.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No Historical Observations In Selected Range"
          message="Adjust the date range (e.g. 2026-01-01 to 2026-11-03) or select another district to inspect historical trends."
          actionLabel="Reset to Full Year 2026"
          onAction={() => {
            setStartDate("2026-01-01");
            setEndDate("2026-11-03");
            setDistrict("all");
          }}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard
              title="Historical Temperature Trajectory"
              subtitle="Daily max, average, and min temperature observations (°C)"
            >
              <TemperatureChart data={activeRows} height={320} />
            </ChartCard>

            <ChartCard
              title="Historical Precipitation Profile"
              subtitle="Precipitation recordings across selected interval (mm)"
            >
              <RainfallChart data={activeRainRows} height={320} />
            </ChartCard>
          </div>

          <ChartCard
            title="Historical Observation Log"
            subtitle="Microsoft Fabric Gold table records for selected dates"
          >
            <DataTable
              data={activeRows}
              columns={HISTORICAL_COLUMNS}
              searchPlaceholder="Search by date or district name..."
            />
          </ChartCard>
        </>
      )}
    </div>
  );
}
