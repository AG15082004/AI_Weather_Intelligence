import { useMemo, useState } from "react";
import { AlertTriangle, CloudDrizzle, CloudRain, Droplets } from "lucide-react";
import { getDistricts, getRainfall } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import {
  getSampleDistrictWeather,
  getSampleRainfallTrend,
} from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { DateRangeFilter } from "@/components/filters/DateRangeFilter";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { RainfallChart } from "@/components/charts/RainfallChart";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import { Badge } from "@/components/ui/badge";
import type { DateRangeParams, RainfallData } from "@/types";

function RainfallIntensityBadge({ category }: { category?: string }) {
  const cat = category || "Dry";
  const cls =
    cat === "Heavy"
      ? "bg-rose-100 text-rose-700 font-semibold"
      : cat === "Moderate"
        ? "bg-amber-100 text-amber-700 font-medium"
        : cat === "Light"
          ? "bg-blue-100 text-blue-700 font-medium"
          : cat === "Unmeasured"
            ? "bg-slate-100 text-slate-500 italic"
            : "bg-emerald-50 text-emerald-700";
  return <Badge className={cls}>{cat}</Badge>;
}

const COLUMNS: DataTableColumn<RainfallData>[] = [
  { key: "date", header: "Date" },
  {
    key: "district",
    header: "District",
    render: (v) => (v ? String(v) : "State Average"),
  },
  {
    key: "rainfall_mm",
    header: "Rainfall (mm)",
    align: "right",
    render: (v) => {
      if (v === null || v === undefined) {
        return <span className="text-slate-400 italic">Unmeasured</span>;
      }
      return (
        <span className="font-semibold text-blue-600">
          {Number(v).toFixed(2)} mm
        </span>
      );
    },
  },
  {
    key: "cumulative_mm",
    header: "Cumulative (mm)",
    align: "right",
    render: (v) => (v != null ? `${Number(v).toFixed(2)} mm` : "—"),
  },
  {
    key: "category",
    header: "Classification",
    align: "center",
    render: (v) => <RainfallIntensityBadge category={v ? String(v) : undefined} />,
  },
];

export function RainfallAnalytics() {
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
    getRainfall,
    params
  );

  const { data: districtsResponse } = useApi(getDistricts);

  const activeRows = useMemo(() => {
    if (previewSample) {
      return getSampleRainfallTrend(
        district === "all" ? undefined : district
      );
    }
    return response?.data ?? [];
  }, [previewSample, district, response?.data]);

  const districtRainfall = useMemo(() => {
    if (previewSample) {
      const all = getSampleDistrictWeather();
      if (district !== "all") {
        return all.filter((d) => d.district === district);
      }
      return [...all]
        .sort((a, b) => b.total_rainfall - a.total_rainfall)
        .slice(0, 10);
    }
    const all = districtsResponse?.data ?? [];
    if (district !== "all") {
      return all.filter((d) => d.district === district);
    }
    return [...all]
      .sort((a, b) => b.total_rainfall - a.total_rainfall)
      .slice(0, 10);
  }, [previewSample, districtsResponse?.data, district]);

  const metrics = useMemo(() => {
    if (activeRows.length === 0) {
      return { total: null, avg: null, peak: null, heavyCount: 0, measuredCount: 0 };
    }
    const measuredRows = activeRows.filter((r) => r.rainfall_mm !== null && r.rainfall_mm !== undefined);
    if (measuredRows.length === 0) {
      return { total: null, avg: null, peak: null, heavyCount: 0, measuredCount: 0 };
    }

    const total = measuredRows.reduce((s, r) => s + (r.rainfall_mm || 0), 0);
    const peak = Math.max(...measuredRows.map((r) => r.rainfall_mm || 0));
    const heavyCount = measuredRows.filter(
      (r) => (r.rainfall_mm || 0) >= 64.5 || r.category === "Heavy"
    ).length;

    return {
      total: total.toFixed(2),
      avg: (total / measuredRows.length).toFixed(2),
      peak: peak.toFixed(2),
      heavyCount,
      measuredCount: measuredRows.length,
    };
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
    <div className="space-y-5">
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Rainfall"
          value={metrics.total ? `${metrics.total} mm` : "Unmeasured"}
          subtitle={
            metrics.measuredCount > 0
              ? `${metrics.measuredCount} measured observation periods`
              : "Precipitation not recorded"
          }
          icon={CloudRain}
          accent="blue"
        />
        <KPICard
          title="Average Per Interval"
          value={metrics.avg ? `${metrics.avg} mm` : "Unmeasured"}
          subtitle="Mean measured precipitation"
          icon={CloudDrizzle}
          accent="cyan"
        />
        <KPICard
          title="Peak Precipitation"
          value={metrics.peak ? `${metrics.peak} mm` : "Unmeasured"}
          subtitle="Highest recorded event"
          icon={Droplets}
          accent="emerald"
        />
        <KPICard
          title="Heavy Rainfall Events"
          value={metrics.measuredCount > 0 ? metrics.heavyCount : "0"}
          subtitle=">= 64.5 mm (IMD Heavy)"
          icon={AlertTriangle}
          accent="rose"
        />
      </div>

      {activeRows.length === 0 ? (
        <EmptyState
          title="No Rainfall Observations Available"
          message="No records found for the selected date range. Select 'Today' or 'Yesterday' to view actual current precipitation telemetry."
          actionLabel="Preview Sample Rainfall Analytics"
          onAction={() => setPreviewSample(true)}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ChartCard
              title="Precipitation Observations"
              subtitle="Precipitation totals (mm) across selected dates"
            >
              <RainfallChart data={activeRows} height={310} />
            </ChartCard>

            <ChartCard
              title="Top Rainfall Districts"
              subtitle="District-level precipitation comparison (mm)"
            >
              <ComparisonChart
                data={districtRainfall}
                height={310}
                series={[
                  {
                    dataKey: "total_rainfall",
                    label: "Total Rainfall (mm)",
                    color: "#3b82f6",
                  },
                  {
                    dataKey: "avg_humidity",
                    label: "Avg Humidity (%)",
                    color: "#10b981",
                  },
                ]}
              />
            </ChartCard>
          </div>

          <ChartCard
            title="Rainfall Observations & IMD Classification"
            subtitle="Distinguishes measured positive, measured zero (dry), and unmeasured dates"
          >
            <DataTable
              data={activeRows}
              columns={COLUMNS}
              searchPlaceholder="Search rainfall logs..."
            />
          </ChartCard>
        </>
      )}
    </div>
  );
}
