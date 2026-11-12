import { useMemo, useState } from "react";
import { Activity, AlertCircle, ShieldCheck, Wind } from "lucide-react";
import { getAirQuality } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import { getSampleAirQuality } from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { DateRangeFilter } from "@/components/common/DateRangeFilter";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AirQuality as AirQualityType, DateRangeParams } from "@/types";

function getAqiBadgeClass(category: string): string {
  const cat = (category || "").toLowerCase();
  if (cat.includes("good")) return "bg-emerald-100 text-emerald-700";
  if (cat.includes("satisfactory")) return "bg-blue-100 text-blue-700";
  if (cat.includes("moderate")) return "bg-amber-100 text-amber-800";
  if (cat.includes("sensitive")) return "bg-orange-100 text-orange-800";
  if (cat.includes("very")) return "bg-purple-100 text-purple-800";
  if (cat.includes("hazard")) return "bg-red-200 text-red-900";
  return "bg-rose-100 text-rose-700";
}

const AQI_COLUMNS: DataTableColumn<AirQualityType>[] = [
  { key: "district", header: "District" },
  {
    key: "aqi",
    header: "AQI",
    align: "right",
    render: (v) => <span className="font-bold text-slate-900">{String(v)}</span>,
  },
  {
    key: "category",
    header: "Category",
    align: "center",
    render: (v) => (
      <Badge className={getAqiBadgeClass(String(v))}>{String(v)}</Badge>
    ),
  },
  {
    key: "pm25",
    header: "PM2.5 (µg/m³)",
    align: "right",
    render: (v) => Number(v).toFixed(1),
  },
  {
    key: "pm10",
    header: "PM10 (µg/m³)",
    align: "right",
    render: (v) => Number(v).toFixed(1),
  },
  {
    key: "no2",
    header: "NO₂",
    align: "right",
    render: (v) => Number(v).toFixed(1),
  },
  {
    key: "so2",
    header: "SO₂",
    align: "right",
    render: (v) => Number(v).toFixed(1),
  },
  {
    key: "o3",
    header: "O₃",
    align: "right",
    render: (v) => Number(v).toFixed(1),
  },
];

export function AirQuality() {
  const [district, setDistrict] = useState("all");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [previewSample, setPreviewSample] = useState(false);

  const params: DateRangeParams = {
    district: district === "all" ? undefined : district,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  };

  const { data: response, loading, error, refetch } = useApi(
    getAirQuality,
    params
  );

  const activeRows = useMemo(() => {
    const list = previewSample
      ? getSampleAirQuality()
      : response?.data ?? [];
    if (district === "all") return list;
    return list.filter((row) => row.district === district);
  }, [previewSample, response?.data, district]);

  const summary = useMemo(() => {
    if (activeRows.length === 0) {
      return { avgAqi: null, avgPm25: null, avgPm10: null, cleanCount: 0 };
    }
    const avgAqi = Math.round(
      activeRows.reduce((s, r) => s + r.aqi, 0) / activeRows.length
    );
    const avgPm25 = (
      activeRows.reduce((s, r) => s + r.pm25, 0) / activeRows.length
    ).toFixed(1);
    const avgPm10 = (
      activeRows.reduce((s, r) => s + r.pm10, 0) / activeRows.length
    ).toFixed(1);
    const cleanCount = activeRows.filter((r) => r.aqi <= 100).length;

    return { avgAqi, avgPm25, avgPm10, cleanCount };
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
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs lg:flex-row lg:items-center lg:justify-between">
        <DistrictFilter value={district} onChange={setDistrict} />
        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
          onReset={() => {
            setStartDate("");
            setEndDate("");
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
          title="Average AQI"
          value={summary.avgAqi ?? "—"}
          subtitle={district === "all" ? "State mean index" : district}
          icon={Wind}
          accent="blue"
        />
        <KPICard
          title="Mean PM2.5"
          value={summary.avgPm25 ? `${summary.avgPm25} µg/m³` : "—"}
          subtitle="Fine particulates"
          icon={Activity}
          accent="amber"
        />
        <KPICard
          title="Mean PM10"
          value={summary.avgPm10 ? `${summary.avgPm10} µg/m³` : "—"}
          subtitle="Coarse particulates"
          icon={AlertCircle}
          accent="rose"
        />
        <KPICard
          title="Good / Satisfactory"
          value={activeRows.length ? `${summary.cleanCount}/${activeRows.length}` : "—"}
          subtitle="Districts <= 100 AQI"
          icon={ShieldCheck}
          accent="emerald"
        />
      </div>

      {activeRows.length === 0 ? (
        <EmptyState
          icon={Wind}
          title="Air Quality Telemetry Pending"
          message="AQI readings and pollutant breakdowns (PM2.5, PM10, CO, NO2, SO2, O3) will appear here once Fabric ingestion is active."
          actionLabel="Preview Sample AQI Data"
          onAction={() => setPreviewSample(true)}
        />
      ) : (
        <>
          <ChartCard
            title="District Air Quality & Particulate Comparison"
            subtitle="AQI, PM2.5, and PM10 levels across Tamil Nadu districts"
          >
            <ComparisonChart
              data={activeRows.slice(0, 12)}
              height={320}
              series={[
                { dataKey: "aqi", label: "AQI", color: "#3b82f6" },
                { dataKey: "pm25", label: "PM2.5 (µg/m³)", color: "#f59e0b" },
                { dataKey: "pm10", label: "PM10 (µg/m³)", color: "#f43f5e" },
              ]}
            />
          </ChartCard>

          {/* Highlighted AQI cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {activeRows.slice(0, 8).map((row) => (
              <Card key={row.district} className="bg-white shadow-xs">
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm font-semibold text-slate-900">
                      {row.district}
                    </CardTitle>
                    <Badge className={getAqiBadgeClass(row.category)}>
                      {row.category}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-baseline justify-between">
                    <span className="text-3xl font-bold text-slate-900">
                      {row.aqi}
                    </span>
                    <span className="text-xs text-slate-500">
                      Dominant: {row.dominant_pollutant || "PM2.5"}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-1.5 rounded-lg bg-slate-50 p-2 text-[11px]">
                    <div>
                      <p className="text-slate-400">PM2.5</p>
                      <p className="font-semibold text-slate-700">{row.pm25}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">PM10</p>
                      <p className="font-semibold text-slate-700">{row.pm10}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">CO</p>
                      <p className="font-semibold text-slate-700">{row.co}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">NO₂</p>
                      <p className="font-semibold text-slate-700">{row.no2}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">SO₂</p>
                      <p className="font-semibold text-slate-700">{row.so2}</p>
                    </div>
                    <div>
                      <p className="text-slate-400">O₃</p>
                      <p className="font-semibold text-slate-700">{row.o3}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <ChartCard
            title="Full District Pollutant Index"
            subtitle="Detailed particulate and gas concentration metrics"
          >
            <DataTable
              data={activeRows}
              columns={AQI_COLUMNS}
              searchPlaceholder="Search district or AQI category..."
            />
          </ChartCard>
        </>
      )}
    </div>
  );
}
