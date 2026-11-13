import { useState } from "react";
import {
  CloudRain,
  Droplets,
  Flame,
  MapPin,
  Snowflake,
  Thermometer,
  ShieldCheck,
  AlertTriangle,
} from "lucide-react";
import { getOverview } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import { getSampleOverview } from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DateRangeFilter } from "@/components/filters/DateRangeFilter";
import { PeriodComparisonPanel } from "@/components/common/PeriodComparisonPanel";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { DataReliabilityStatus } from "@/components/common/DataReliabilityStatus";
import { OperationalMonitoringCard } from "@/components/common/OperationalMonitoringCard";
import { TemperatureChart } from "@/components/charts/TemperatureChart";
import { RainfallChart } from "@/components/charts/RainfallChart";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import type { DateRangeParams } from "@/types";

export function WeatherOverview() {
  const [startDate, setStartDate] = useState("2026-11-06");
  const [endDate, setEndDate] = useState("2026-11-12");
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

  const hasChartData =
    Boolean(activeOverview?.temperature_trend.length) ||
    Boolean(activeOverview?.rainfall_trend.length) ||
    Boolean(activeOverview?.district_comparison.length);

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
    <div className="space-y-5">
      <div className="flex flex-col gap-2">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold tracking-tight text-slate-900">
                Tamil Nadu Weather Intelligence Overview
              </h2>
              {activeOverview?.latest_observation && (
                <span className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-blue-700/10">
                  Latest: {activeOverview.latest_observation}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Aggregated analytics across all 38 districts powered by Microsoft Fabric Lakehouse
            </p>
          </div>
        </div>

        {/* Date Filter Toolbar */}
        <DateRangeFilter
          startDate={startDate}
          endDate={endDate}
          onApply={(start, end) => {
            setStartDate(start);
            setEndDate(end);
          }}
          onReset={() => {
            setStartDate("2026-11-06");
            setEndDate("2026-11-12");
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

      <FabricStatusBanner
        status={response?.status}
        isPreviewMode={previewSample}
        onTogglePreview={() => setPreviewSample((prev) => !prev)}
        onRefresh={() => void refetch()}
      />

      {/* Centralized Phase 9 Data Reliability & Freshness Indicator */}
      <DataReliabilityStatus
        status={response?.data_status}
        dataSource={response?.data_source}
        lastRefresh={response?.last_successful_refresh}
        dataAgeSeconds={response?.data_age_seconds}
        isStale={response?.is_stale}
        warning={response?.warning}
        onRefresh={() => void refetch()}
        isRefreshing={loading}
      />

      {/* Operational Observability & Health Monitoring */}
      <OperationalMonitoringCard />

      {/* 6 KPI Cards */}
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

      {/* Rainfall Data Quality Metadata Badge */}
      {rainfallQuality && (
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white p-3 text-xs shadow-xs">
          <div className="flex items-center gap-2">
            {rainfallQuality.status === "complete" ? (
              <ShieldCheck className="size-4 text-emerald-600" />
            ) : (
              <AlertTriangle className="size-4 text-amber-500" />
            )}
            <span className="font-semibold text-slate-800">
              Rainfall Pipeline Quality:
            </span>
            <span className="text-slate-600">{rainfallQuality.message}</span>
          </div>

          <div className="flex items-center gap-3 text-slate-500">
            <span>
              Completeness:{" "}
              <strong className="text-slate-800">
                {rainfallQuality.completeness_pct.toFixed(0)}%
              </strong>
            </span>
            <span>•</span>
            <span>
              Measured Zero:{" "}
              <strong className="text-slate-800">
                {rainfallQuality.measured_zero_days} days
              </strong>
            </span>
            <span>•</span>
            <span>
              Positive:{" "}
              <strong className="text-slate-800">
                {rainfallQuality.positive_rainfall_days} days
              </strong>
            </span>
            <span>•</span>
            <span>
              Unmeasured (NULL):{" "}
              <strong className="text-rose-600">
                {rainfallQuality.missing_days} days
              </strong>
            </span>
          </div>
        </div>
      )}

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
              subtitle="Daily/monthly maximum, average, and minimum temperatures (°C)"
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
            title="District Comparison"
            subtitle="Cross-district temperature and humidity benchmark across Tamil Nadu"
          >
            <ComparisonChart
              data={activeOverview?.district_comparison ?? []}
              height={340}
            />
          </ChartCard>
        </>
      )}
    </div>
  );
}
