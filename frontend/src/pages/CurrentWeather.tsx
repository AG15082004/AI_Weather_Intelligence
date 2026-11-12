import { useMemo, useState } from "react";
import { format, isValid, parseISO } from "date-fns";
import {
  Cloud,
  CloudRain,
  Clock,
  Droplets,
  Gauge,
  LayoutGrid,
  List,
  Search,
  Sun,
  Thermometer,
  Wind,
  Calendar,
  Database,
} from "lucide-react";
import { getCurrentWeather } from "@/api/endpoints";
import { useApi } from "@/hooks/useApi";
import { getSampleCurrentWeather } from "@/lib/sampleData";
import { getIstTodayStr } from "@/lib/dateUtils";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { FabricStatusBanner } from "@/components/common/FabricStatusBanner";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { CurrentWeather as CurrentWeatherType } from "@/types";

function ConditionIcon({ condition }: { condition: string }) {
  const c = condition.toLowerCase();
  if (c.includes("rain") || c.includes("shower") || c.includes("drizzle")) {
    return <CloudRain className="size-5 text-blue-600" />;
  }
  if (c.includes("cloud") || c.includes("overcast")) {
    return <Cloud className="size-5 text-slate-500" />;
  }
  return <Sun className="size-5 text-amber-500" />;
}

function formatUpdated(raw: string): string {
  const parsed = parseISO(raw);
  if (isValid(parsed)) {
    return format(parsed, "MMM dd, HH:mm");
  }
  return raw;
}

const TABLE_COLUMNS: DataTableColumn<CurrentWeatherType>[] = [
  { key: "district", header: "District" },
  {
    key: "condition",
    header: "Condition",
    render: (v) => <span className="font-medium text-slate-800">{String(v)}</span>,
  },
  {
    key: "temperature",
    header: "Temp (°C)",
    align: "right",
    render: (v) => (
      <span className="font-semibold text-amber-600">{Number(v).toFixed(1)}°C</span>
    ),
  },
  {
    key: "feels_like",
    header: "Feels Like",
    align: "right",
    render: (v) => `${Number(v).toFixed(1)}°C`,
  },
  {
    key: "humidity",
    header: "Humidity",
    align: "right",
    render: (v) => `${Number(v).toFixed(0)}%`,
  },
  {
    key: "wind_speed",
    header: "Wind",
    align: "right",
    render: (v, row) => `${Number(v).toFixed(0)} km/h ${row.wind_direction || ""}`,
  },
  {
    key: "pressure",
    header: "Pressure",
    align: "right",
    render: (v) => `${Number(v).toFixed(0)} hPa`,
  },
  {
    key: "precipitation_mm",
    header: "Rain (mm)",
    align: "right",
    render: (v) => (
      <span className="font-semibold text-blue-600">
        {v != null ? `${Number(v).toFixed(2)} mm` : "0.00 mm"}
      </span>
    ),
  },
  {
    key: "last_updated",
    header: "Observation Time",
    align: "right",
    render: (v) => (
      <span className="text-xs text-slate-500">{formatUpdated(String(v))}</span>
    ),
  },
];

export function CurrentWeather() {
  const todayIst = getIstTodayStr(); // e.g. "2026-11-12"
  const yesterdayIst = "2026-11-11";

  const [selectedDate, setSelectedDate] = useState<string>(todayIst);
  const [district, setDistrict] = useState("all");
  const [search, setSearch] = useState("");
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");
  const [previewSample, setPreviewSample] = useState(false);

  const isToday = selectedDate === todayIst;
  const isYesterday = selectedDate === yesterdayIst;

  const apiParams = useMemo(() => {
    const p: { district?: string; date?: string } = {};
    if (district !== "all") p.district = district;
    if (selectedDate) p.date = selectedDate;
    return p;
  }, [district, selectedDate]);

  const { data: response, loading, error, refetch } = useApi(
    getCurrentWeather,
    apiParams
  );

  const activeCards: CurrentWeatherType[] = useMemo(() => {
    const source = previewSample
      ? getSampleCurrentWeather()
      : response?.data ?? [];

    return source.filter((item) => {
      if (district !== "all" && item.district !== district) return false;
      if (
        search.trim() &&
        !item.district.toLowerCase().includes(search.trim().toLowerCase())
      ) {
        return false;
      }
      return true;
    });
  }, [previewSample, response?.data, district, search]);

  if (loading && !previewSample) {
    return <LoadingSkeleton variant="cards" count={8} />;
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
      {/* Day Mode Selector Toolbar */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-slate-700">Observation Window:</span>
            <div className="flex rounded-md bg-slate-100 p-0.5">
              <button
                type="button"
                onClick={() => setSelectedDate(todayIst)}
                className={cn(
                  "rounded px-3 py-1.5 text-xs font-semibold transition-colors",
                  isToday
                    ? "bg-sky-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                )}
              >
                Today (Live Snapshot)
              </button>
              <button
                type="button"
                onClick={() => setSelectedDate(yesterdayIst)}
                className={cn(
                  "rounded px-3 py-1.5 text-xs font-semibold transition-colors",
                  isYesterday
                    ? "bg-sky-600 text-white shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
                )}
              >
                Yesterday (Nov 11 Observations)
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Calendar className="size-4 text-slate-400" />
            <label htmlFor="custom-date-picker" className="text-xs text-slate-500">
              Specific Date:
            </label>
            <Input
              id="custom-date-picker"
              type="date"
              max={todayIst}
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="h-8 w-36 bg-white text-xs"
            />
          </div>
        </div>

        {/* Source and Data Quality Notice */}
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-600 border border-slate-100">
          <div className="flex items-center gap-2">
            <Database className="size-4 text-sky-600" />
            <span>
              <strong>Data Source: </strong>
              {isToday ? (
                <span>
                  Microsoft Fabric Lakehouse <code className="text-slate-800 font-semibold">[dbo].[gold_current_weather_latest]</code> (Live 3-hourly telemetry)
                </span>
              ) : (
                <span>
                  Microsoft Fabric Lakehouse <code className="text-slate-800 font-semibold">[dbo].[silver_weather_current]</code> (342 actual observation runs on {selectedDate})
                </span>
              )}
            </span>
          </div>

          <span className="inline-flex items-center gap-1 rounded bg-sky-100 px-2 py-0.5 text-[11px] font-semibold text-sky-800">
            <Clock className="size-3" />
            Asia/Kolkata (IST)
          </span>
        </div>
      </div>

      {/* Filter and View Toggle */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-2xs sm:flex-row sm:items-center sm:justify-between">
        <div className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-slate-400" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search district weather..."
            className="bg-white pl-8"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <DistrictFilter value={district} onChange={setDistrict} />
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5">
            <Button
              type="button"
              variant={viewMode === "cards" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("cards")}
              className="h-8 gap-1 px-2.5 text-xs"
            >
              <LayoutGrid className="size-3.5" />
              Cards
            </Button>
            <Button
              type="button"
              variant={viewMode === "table" ? "default" : "ghost"}
              size="sm"
              onClick={() => setViewMode("table")}
              className="h-8 gap-1 px-2.5 text-xs"
            >
              <List className="size-3.5" />
              Table
            </Button>
          </div>
        </div>
      </div>

      <FabricStatusBanner
        status={response?.status}
        isPreviewMode={previewSample}
        onTogglePreview={() => setPreviewSample((prev) => !prev)}
        onRefresh={() => void refetch()}
      />

      {activeCards.length === 0 ? (
        <EmptyState
          icon={Sun}
          title={`No Observations for ${selectedDate}`}
          message="No telemetry records exist in Fabric silver_weather_current for this date. Historical hourly ingestion was initialized recently."
          actionLabel="View Today's Telemetry"
          onAction={() => setSelectedDate(todayIst)}
        />
      ) : viewMode === "table" ? (
        <Card className="bg-white shadow-xs">
          <CardHeader className="border-b border-slate-100 pb-3">
            <CardTitle className="text-base font-semibold text-slate-900">
              Observations Log — {selectedDate} ({activeCards.length} Districts Reporting)
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-4">
            <DataTable
              data={activeCards}
              columns={TABLE_COLUMNS}
              searchPlaceholder="Filter current weather observations..."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {activeCards.map((item) => (
            <Card
              key={item.district}
              className="bg-white shadow-xs transition-shadow hover:shadow-md"
            >
              <CardHeader className="border-b border-slate-100 pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-base font-semibold text-slate-900">
                      {item.district}
                    </CardTitle>
                    <p className="mt-0.5 text-xs text-slate-500">
                      {item.condition}
                    </p>
                  </div>
                  <div className="flex size-9 items-center justify-center rounded-lg bg-slate-50 ring-1 ring-slate-200/70">
                    <ConditionIcon condition={item.condition} />
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-4 pt-3">
                <div className="flex items-baseline justify-between">
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold tracking-tight text-slate-900">
                      {item.temperature.toFixed(1)}°
                    </span>
                    <span className="text-sm font-medium text-slate-500">C</span>
                  </div>
                  <Badge variant="secondary" className="gap-1 text-xs">
                    <Thermometer className="size-3 text-amber-500" />
                    Feels {item.feels_like.toFixed(1)}°C
                  </Badge>
                </div>

                <div className="grid grid-cols-3 gap-2 rounded-lg bg-slate-50 p-2.5 text-xs">
                  <div className="flex flex-col gap-0.5">
                    <span className="flex items-center gap-1 text-slate-500">
                      <Droplets className="size-3 text-blue-500" />
                      Humidity
                    </span>
                    <span className="font-semibold text-slate-800">
                      {item.humidity}%
                    </span>
                  </div>

                  <div className="flex flex-col gap-0.5">
                    <span className="flex items-center gap-1 text-slate-500">
                      <Wind className="size-3 text-emerald-500" />
                      Wind
                    </span>
                    <span className="font-semibold text-slate-800">
                      {item.wind_speed.toFixed(0)} km/h {item.wind_direction}
                    </span>
                  </div>

                  <div className="flex flex-col gap-0.5">
                    <span className="flex items-center gap-1 text-slate-500">
                      <CloudRain className="size-3 text-sky-500" />
                      Rainfall
                    </span>
                    <span className="font-semibold text-slate-800">
                      {item.precipitation_mm != null ? `${item.precipitation_mm.toFixed(2)} mm` : "0.0 mm"}
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <div className="flex items-center gap-1">
                    <Gauge className="size-3 text-slate-400" />
                    <span>{item.pressure} hPa</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock className="size-3" />
                    <span>{formatUpdated(item.last_updated)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
