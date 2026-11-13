import { useCallback, useMemo, useState } from "react";
import {
  CloudRain,
  Droplets,
  Flame,
  MapPin,
  Search,
  Snowflake,
  Thermometer,
} from "lucide-react";
import { getDistrictByName, getDistricts, getTemperature } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import { TAMIL_NADU_DISTRICTS } from "@/lib/districts";
import {
  getSampleDistrictWeather,
  getSampleHumidityTrend,
  getSampleTemperatureTrend,
} from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { DateRangeFilter } from "@/components/filters/DateRangeFilter";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import { TemperatureChart } from "@/components/charts/TemperatureChart";
import { HumidityChart } from "@/components/charts/HumidityChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { DistrictWeather } from "@/types";

const DISTRICT_COLUMNS: DataTableColumn<DistrictWeather>[] = [
  { key: "district", header: "District" },
  {
    key: "zone",
    header: "Agro-Climatic Zone",
    render: (v) => (v ? String(v) : "Tamil Nadu"),
  },
  {
    key: "avg_temp",
    header: "Avg Temp",
    align: "right",
    render: (v) => `${Number(v).toFixed(1)}°C`,
  },
  {
    key: "max_temp",
    header: "Max Temp",
    align: "right",
    render: (v) => `${Number(v).toFixed(1)}°C`,
  },
  {
    key: "min_temp",
    header: "Min Temp",
    align: "right",
    render: (v) => `${Number(v).toFixed(1)}°C`,
  },
  {
    key: "total_rainfall",
    header: "Rainfall",
    align: "right",
    render: (v) => `${Number(v).toFixed(1)} mm`,
  },
  {
    key: "avg_humidity",
    header: "Humidity",
    align: "right",
    render: (v) => `${Number(v).toFixed(0)}%`,
  },
];

export function DistrictIntelligence() {
  const [selectedDistrict, setSelectedDistrict] = useState<string>("Chennai");
  const [districtSearch, setDistrictSearch] = useState("");
  const [previewSample, setPreviewSample] = useState(false);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const dateParams = useMemo(
    () => ({ start_date: startDate, end_date: endDate }),
    [startDate, endDate]
  );

  const fetchDistrictDetail = useCallback(
    () =>
      getDistrictByName(selectedDistrict, {
        start_date: startDate,
        end_date: endDate,
      }),
    [selectedDistrict, startDate, endDate]
  );

  const fetchDistrictTemp = useCallback(
    () =>
      getTemperature({
        district: selectedDistrict,
        start_date: startDate,
        end_date: endDate,
      }),
    [selectedDistrict, startDate, endDate]
  );

  const {
    data: districtsRes,
    loading: listLoading,
    error: listError,
    refetch: refetchList,
  } = useApi(getDistricts, dateParams);

  const { data: detailRes, refetch: refetchDetail } = useApi(fetchDistrictDetail);
  const { data: tempRes, refetch: refetchTemp } = useApi(fetchDistrictTemp);

  const sampleList = useMemo(() => getSampleDistrictWeather(), []);

  const allDistrictData = useMemo(() => {
    if (previewSample) return sampleList;
    if (districtsRes?.data && districtsRes.data.length > 0) {
      return districtsRes.data;
    }
    return [];
  }, [previewSample, sampleList, districtsRes]);

  const selectedMetrics = useMemo(() => {
    if (!previewSample && detailRes?.data && detailRes.data.length > 0) {
      return detailRes.data[0];
    }
    if (allDistrictData.length > 0) {
      return (
        allDistrictData.find((d) => d.district === selectedDistrict) ?? null
      );
    }
    return null;
  }, [previewSample, detailRes, allDistrictData, selectedDistrict]);

  const filteredDistrictNames = useMemo(() => {
    const q = districtSearch.trim().toLowerCase();
    if (!q) return [...TAMIL_NADU_DISTRICTS];
    return TAMIL_NADU_DISTRICTS.filter((d) => d.toLowerCase().includes(q));
  }, [districtSearch]);

  const comparisonSlice = useMemo(() => {
    if (allDistrictData.length === 0) return [];
    const others = allDistrictData
      .filter((d) => d.district !== selectedDistrict)
      .slice(0, 7);
    return selectedMetrics ? [selectedMetrics, ...others] : others;
  }, [allDistrictData, selectedDistrict, selectedMetrics]);

  if (listLoading && !previewSample) {
    return <LoadingSkeleton variant="page" count={5} />;
  }

  if (listError && !previewSample) {
    return (
      <ErrorState
        message={listError}
        onRetry={() => {
          void refetchList();
          void refetchDetail();
        }}
        onUseSample={() => setPreviewSample(true)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">
                Selected District:{" "}
                <span className="text-blue-600">{selectedDistrict}</span>
              </h2>
              {selectedMetrics?.current_condition && (
                <Badge variant="outline" className="bg-blue-50/50 text-blue-700">
                  {selectedMetrics.current_condition}
                  {selectedMetrics.current_temp != null
                    ? ` (${selectedMetrics.current_temp.toFixed(1)}°C)`
                    : ""}
                </Badge>
              )}
              {selectedMetrics?.latitude != null && selectedMetrics?.longitude != null && (
                <span className="text-[11px] text-slate-400">
                  {selectedMetrics.latitude.toFixed(2)}°N, {selectedMetrics.longitude.toFixed(2)}°E
                  {selectedMetrics.elevation_m != null ? ` • ${selectedMetrics.elevation_m.toFixed(0)}m elev` : ""}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500">
              Click any of the 38 Tamil Nadu districts below to inspect metrics & comparisons
            </p>
          </div>
          <DistrictFilter
            value={selectedDistrict}
            onChange={setSelectedDistrict}
            includeAll={false}
          />
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
          }}
        />
      </div>

      <FabricStatusBanner
        status={districtsRes?.status}
        isPreviewMode={previewSample}
        onTogglePreview={() => setPreviewSample((prev) => !prev)}
        onRefresh={() => {
          void refetchList();
          void refetchDetail();
          void refetchTemp();
        }}
      />

      {/* Selected District KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <KPICard
          title="Avg Temperature"
          value={
            selectedMetrics ? `${selectedMetrics.avg_temp.toFixed(1)}°C` : "—"
          }
          subtitle={selectedDistrict}
          icon={Thermometer}
          accent="amber"
        />
        <KPICard
          title="Max Temperature"
          value={
            selectedMetrics ? `${selectedMetrics.max_temp.toFixed(1)}°C` : "—"
          }
          subtitle="Daytime peak"
          icon={Flame}
          accent="rose"
        />
        <KPICard
          title="Min Temperature"
          value={
            selectedMetrics ? `${selectedMetrics.min_temp.toFixed(1)}°C` : "—"
          }
          subtitle="Nighttime low"
          icon={Snowflake}
          accent="blue"
        />
        <KPICard
          title="Total Rainfall"
          value={
            selectedMetrics
              ? `${selectedMetrics.total_rainfall.toFixed(1)} mm`
              : "—"
          }
          subtitle="Cumulative total"
          icon={CloudRain}
          accent="indigo"
        />
        <KPICard
          title="Avg Humidity"
          value={
            selectedMetrics
              ? `${selectedMetrics.avg_humidity.toFixed(0)}%`
              : "—"
          }
          subtitle="Relative humidity"
          icon={Droplets}
          accent="emerald"
        />
      </div>

      {/* All 38 Tamil Nadu Districts Grid Selector */}
      <Card className="bg-white shadow-xs">
        <CardHeader className="border-b border-slate-100 pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">
                All 38 Tamil Nadu Districts
              </CardTitle>
              <p className="mt-0.5 text-xs text-slate-500">
                Interactive district directory and instant climate switcher
              </p>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-slate-400" />
              <Input
                value={districtSearch}
                onChange={(e) => setDistrictSearch(e.target.value)}
                placeholder="Find district..."
                className="bg-white pl-8"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
            {filteredDistrictNames.map((name) => {
              const info = allDistrictData.find((d) => d.district === name);
              const isSelected = name === selectedDistrict;
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => setSelectedDistrict(name)}
                  className={cn(
                    "flex flex-col items-start rounded-lg border p-2.5 text-left transition-all",
                    isSelected
                      ? "border-blue-600 bg-blue-50/80 ring-1 ring-blue-600"
                      : "border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50"
                  )}
                >
                  <div className="flex w-full items-center justify-between gap-1">
                    <span
                      className={cn(
                        "truncate text-xs font-semibold",
                        isSelected ? "text-blue-700" : "text-slate-800"
                      )}
                    >
                      {name}
                    </span>
                    <MapPin
                      className={cn(
                        "size-3 shrink-0",
                        isSelected ? "text-blue-600" : "text-slate-400"
                      )}
                    />
                  </div>
                  <div className="mt-1.5 flex w-full items-center justify-between text-[11px] text-slate-500">
                    <span>{info ? `${info.avg_temp.toFixed(1)}°C` : "—"}</span>
                    <span>
                      {info ? `${info.total_rainfall.toFixed(0)}mm` : "Syncing"}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Charts & District Comparison Matrix */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard
          title={`${selectedDistrict} Temperature Profile`}
          subtitle="Observed max, average, and min temperature curve (°C)"
        >
          <TemperatureChart
            data={
              previewSample
                ? getSampleTemperatureTrend(selectedDistrict)
                : (tempRes?.data && tempRes.data.length > 0)
                  ? tempRes.data
                  : getSampleTemperatureTrend(selectedDistrict)
            }
          />
        </ChartCard>

        <ChartCard
          title="State Relative Humidity Profile"
          subtitle="Seasonal humidity trajectory (%)"
        >
          <HumidityChart data={getSampleHumidityTrend()} height={300} />
        </ChartCard>
      </div>

      <ChartCard
        title={`${selectedDistrict} vs Peer Districts`}
        subtitle="Cross-district weather comparison across Tamil Nadu"
        filters={<Badge variant="secondary">Top Comparison Set</Badge>}
      >
        <ComparisonChart data={comparisonSlice} height={320} />
      </ChartCard>

      <ChartCard
        title="All 38 Districts Weather Matrix"
        subtitle="Click any district row to inspect it above"
      >
        <DataTable
          data={allDistrictData}
          columns={DISTRICT_COLUMNS}
          searchPlaceholder="Filter all 38 districts..."
          onRowClick={(row) => setSelectedDistrict(row.district)}
        />
      </ChartCard>
    </div>
  );
}
