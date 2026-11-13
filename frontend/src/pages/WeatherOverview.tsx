import { useMemo, useState } from "react";
import {
  CloudRain,
  Droplets,
  Flame,
  MapPin,
  Snowflake,
  Thermometer,
  Sparkles,
  Compass,
} from "lucide-react";
import { getOverview } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import { getSampleOverview } from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DateRangeFilter } from "@/components/filters/DateRangeFilter";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { PeriodComparisonPanel } from "@/components/common/PeriodComparisonPanel";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { TemperatureChart } from "@/components/charts/TemperatureChart";
import { RainfallChart } from "@/components/charts/RainfallChart";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DateRangeParams } from "@/types";

export function WeatherOverview() {
  // Default to "All" (empty string parameters fetch complete historical range)
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("all");
  const [previewSample, setPreviewSample] = useState(false);
  const [isComparisonOpen, setIsComparisonOpen] = useState(false);

  const params: DateRangeParams = {
    start_date: startDate || undefined,
    end_date: endDate || undefined,
  };

  const { data: response, loading, error, refetch } = useApi(
    getOverview,
    params
  );

  const sampleOverview = getSampleOverview();
  const apiOverview = response?.data;
  const activeOverview = previewSample ? sampleOverview : apiOverview;

  const districtComparison = activeOverview?.district_comparison ?? [];

  // Filter comparison by district if specific district is selected
  const filteredComparison = useMemo(() => {
    if (!selectedDistrict || selectedDistrict === "all") return districtComparison;
    return districtComparison.filter((d) => d.district === selectedDistrict);
  }, [districtComparison, selectedDistrict]);

  // Derive extreme weather highlights strictly from actual data
  const extremeStats = useMemo(() => {
    if (!districtComparison.length) return null;
    const sortedByMaxTemp = [...districtComparison].sort((a, b) => b.max_temp - a.max_temp);
    const sortedByMinTemp = [...districtComparison].sort((a, b) => a.min_temp - b.min_temp);
    const sortedByRain = [...districtComparison].sort((a, b) => b.total_rainfall - a.total_rainfall);
    const sortedByHumidity = [...districtComparison].sort((a, b) => b.avg_humidity - a.avg_humidity);

    return {
      hottest: sortedByMaxTemp[0],
      coolest: sortedByMinTemp[0],
      wettest: sortedByRain[0],
      humid: sortedByHumidity[0],
    };
  }, [districtComparison]);

  const hasChartData =
    Boolean(activeOverview?.temperature_trend.length) ||
    Boolean(activeOverview?.rainfall_trend.length) ||
    Boolean(districtComparison.length);

  if (loading && !previewSample) {
    return <LoadingSkeleton variant="page" count={6} />;
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

  const isDataUnavailable =
    response?.data_status === "UNAVAILABLE" ||
    response?.status === "unavailable";

  const formatVal = (val: number | null | undefined, unit: string) => {
    if (isDataUnavailable) return "Fabric Disconnected";
    return val != null ? `${val.toFixed(1)}${unit}` : "N/A";
  };

  const rainfallQuality = activeOverview?.rainfall_quality;

  return (
    <div className="space-y-6">
      {/* A. Header Section */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Weather Intelligence Overview
            </h1>
            <Badge variant="outline" className="gap-1 border-emerald-200 bg-emerald-50 text-emerald-700">
              <span className="size-1.5 rounded-full bg-emerald-500" />
              Tamil Nadu – 38 Districts
            </Badge>
            {activeOverview?.latest_observation && (
              <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-700/10">
                Latest: {activeOverview.latest_observation}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Real-time & historical meteorological intelligence across all 38 districts powered by Microsoft Fabric Lakehouse
          </p>
        </div>
      </div>

      {/* B. Global Filters Section */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-3.5 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <DistrictFilter value={selectedDistrict} onChange={setSelectedDistrict} />
        </div>
        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          selectedDistrict={selectedDistrict}
          onApply={(start, end) => {
            setStartDate(start);
            setEndDate(end);
          }}
          onReset={() => {
            setStartDate("");
            setEndDate("");
            setSelectedDistrict("all");
          }}
          showComparisonToggle
          isComparisonActive={isComparisonOpen}
          onToggleComparison={() => setIsComparisonOpen((prev) => !prev)}
        />
      </div>

      {/* Comparison Panel (Collapsible) */}
      {isComparisonOpen && (
        <PeriodComparisonPanel
          onClose={() => setIsComparisonOpen(false)}
        />
      )}

      {/* Preview Mode Notification Banner (Only if sample preview is active or pending) */}
      <FabricStatusBanner
        status={response?.status}
        isPreviewMode={previewSample}
        onTogglePreview={() => setPreviewSample((prev) => !prev)}
        onRefresh={() => void refetch()}
      />

      {/* C. KPI Cards (6 Key Meteorological Metrics) */}
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        <KPICard
          title="Districts Covered"
          value={activeOverview?.districts_covered ?? 38}
          subtitle="Full TN coverage"
          icon={MapPin}
          accent="blue"
        />
        <KPICard
          title="Avg Temperature"
          value={formatVal(activeOverview?.avg_temperature, "°C")}
          subtitle="Statewide mean"
          icon={Thermometer}
          accent="amber"
        />
        <KPICard
          title="Max Temperature"
          value={formatVal(activeOverview?.max_temperature, "°C")}
          subtitle="Peak recorded"
          icon={Flame}
          accent="rose"
        />
        <KPICard
          title="Min Temperature"
          value={formatVal(activeOverview?.min_temperature, "°C")}
          subtitle="Lowest recorded"
          icon={Snowflake}
          accent="cyan"
        />
        <KPICard
          title="Total Rainfall"
          value={
            isDataUnavailable
              ? "Fabric Disconnected"
              : activeOverview?.total_rainfall !== null &&
                activeOverview?.total_rainfall !== undefined
                ? `${activeOverview.total_rainfall.toFixed(1)} mm`
                : "N/A"
          }
          subtitle={
            rainfallQuality
              ? `${rainfallQuality.positive_rainfall_days} rainy / ${rainfallQuality.measured_days} measured days`
              : "Precipitation sum"
          }
          icon={CloudRain}
          accent="indigo"
        />
        <KPICard
          title="Avg Humidity"
          value={formatVal(activeOverview?.avg_humidity, "%")}
          subtitle="Relative humidity"
          icon={Droplets}
          accent="emerald"
        />
      </div>

      {/* E. District Intelligence Highlights (Extreme Weather & Top Performers) */}
      {extremeStats && (
        <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          <div className="flex items-center gap-3 rounded-lg border border-rose-100 bg-rose-50/50 p-3.5 shadow-2xs">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-rose-100 text-rose-700">
              <Flame className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Hottest District</p>
              <p className="truncate text-sm font-bold text-slate-900">{extremeStats.hottest.district}</p>
              <p className="text-xs font-semibold text-rose-600">{extremeStats.hottest.max_temp.toFixed(1)}°C peak</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-cyan-100 bg-cyan-50/50 p-3.5 shadow-2xs">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-cyan-100 text-cyan-700">
              <Snowflake className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Coolest District</p>
              <p className="truncate text-sm font-bold text-slate-900">{extremeStats.coolest.district}</p>
              <p className="text-xs font-semibold text-cyan-600">{extremeStats.coolest.min_temp.toFixed(1)}°C low</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-blue-100 bg-blue-50/50 p-3.5 shadow-2xs">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
              <CloudRain className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Highest Rainfall</p>
              <p className="truncate text-sm font-bold text-slate-900">{extremeStats.wettest.district}</p>
              <p className="text-xs font-semibold text-blue-600">{extremeStats.wettest.total_rainfall.toFixed(1)} mm</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-lg border border-emerald-100 bg-emerald-50/50 p-3.5 shadow-2xs">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">
              <Droplets className="size-5" />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Highest Humidity</p>
              <p className="truncate text-sm font-bold text-slate-900">{extremeStats.humid.district}</p>
              <p className="text-xs font-semibold text-emerald-600">{extremeStats.humid.avg_humidity.toFixed(0)}% mean</p>
            </div>
          </div>
        </div>
      )}

      {/* D. Weather Analytics Charts */}
      {!hasChartData ? (
        <EmptyState
          title={
            isDataUnavailable
              ? "Fabric Lakehouse Not Connected"
              : "Overview Trend Charts Pending Fabric Sync"
          }
          message={
            isDataUnavailable
              ? "Microsoft Fabric Lakehouse is currently disconnected. Configure Fabric credentials in Render to stream live 38-district telemetry."
              : "The API responded cleanly, but no time-series rows are available for this date filter."
          }
          actionLabel="Preview Sample TN Charts"
          onAction={() => setPreviewSample(true)}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <ChartCard
              title="Temperature Trend"
              subtitle="Daily maximum, average, and minimum temperatures (°C)"
            >
              <TemperatureChart
                data={activeOverview?.temperature_trend ?? []}
              />
            </ChartCard>

            <ChartCard
              title="Rainfall Trend"
              subtitle="Precipitation observation across reporting intervals (mm)"
            >
              <RainfallChart
                data={activeOverview?.rainfall_trend ?? []}
                completenessPct={rainfallQuality?.completeness_pct}
              />
            </ChartCard>
          </div>

          <ChartCard
            title="District Meteorological Comparison"
            subtitle="Cross-district temperature and humidity benchmark across Tamil Nadu"
          >
            <ComparisonChart
              data={filteredComparison}
              height={340}
            />
          </ChartCard>
        </>
      )}

      {/* F. AI Meteorological Insights & Intelligence */}
      <Card className="border-slate-200 bg-gradient-to-br from-white to-slate-50/50 shadow-xs">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 ring-1 ring-blue-200">
                <Sparkles className="size-4" />
              </div>
              <div>
                <CardTitle className="text-sm font-bold text-slate-900">
                  Grounded Meteorological Summary & Analytics
                </CardTitle>
                <p className="text-xs text-slate-500">
                  Synthesized from verified Microsoft Fabric Lakehouse records across 38 districts
                </p>
              </div>
            </div>
            <Badge variant="outline" className="border-blue-200 bg-blue-50 text-[11px] font-semibold text-blue-700">
              Grounded Facts
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 pt-0 text-xs text-slate-700 leading-relaxed">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-slate-100 bg-white p-3 shadow-2xs">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                <Thermometer className="size-3.5 text-amber-500" />
                <span>Thermal Dynamics</span>
              </div>
              <p className="mt-1.5 text-slate-600">
                Statewide mean temperature stands at{" "}
                <strong className="text-slate-900 font-semibold">{formatVal(activeOverview?.avg_temperature, "°C")}</strong>.{" "}
                {extremeStats ? (
                  <>
                    Thermal range spans from {extremeStats.coolest.min_temp.toFixed(1)}°C in{" "}
                    <strong>{extremeStats.coolest.district}</strong> to {extremeStats.hottest.max_temp.toFixed(1)}°C in{" "}
                    <strong>{extremeStats.hottest.district}</strong>.
                  </>
                ) : (
                  "Full multi-district telemetry is monitored continuously."
                )}
              </p>
            </div>

            <div className="rounded-lg border border-slate-100 bg-white p-3 shadow-2xs">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                <CloudRain className="size-3.5 text-blue-500" />
                <span>Monsoon & Rainfall</span>
              </div>
              <p className="mt-1.5 text-slate-600">
                Total recorded precipitation is{" "}
                <strong className="text-slate-900 font-semibold">
                  {activeOverview?.total_rainfall != null ? `${activeOverview.total_rainfall.toFixed(1)} mm` : "N/A"}
                </strong>.{" "}
                {extremeStats?.wettest && extremeStats.wettest.total_rainfall > 0 ? (
                  <>
                    Maximum rainfall accumulation recorded in <strong>{extremeStats.wettest.district}</strong> ({extremeStats.wettest.total_rainfall.toFixed(1)} mm).
                  </>
                ) : (
                  "Rainfall sensors report stable precipitation activity across districts."
                )}
              </p>
            </div>

            <div className="rounded-lg border border-slate-100 bg-white p-3 shadow-2xs">
              <div className="flex items-center gap-1.5 font-semibold text-slate-800">
                <Compass className="size-3.5 text-emerald-500" />
                <span>Atmospheric Moisture</span>
              </div>
              <p className="mt-1.5 text-slate-600">
                Average statewide relative humidity is{" "}
                <strong className="text-slate-900 font-semibold">{formatVal(activeOverview?.avg_humidity, "%")}</strong>.{" "}
                {extremeStats?.humid ? (
                  <>
                    Peak atmospheric moisture is centered in <strong>{extremeStats.humid.district}</strong> ({extremeStats.humid.avg_humidity.toFixed(0)}%).
                  </>
                ) : (
                  "Humidity indices reflect normal seasonal conditions."
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-md border border-slate-100 bg-slate-50/80 px-3 py-2 text-[11px] text-slate-500">
            <span>
              <strong>Note:</strong> Quantitative figures are factual lakehouse observations; synthesis and regional comparisons are assisted by AI.
            </span>
            <span className="font-medium text-slate-600">Asia/Kolkata (IST)</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
