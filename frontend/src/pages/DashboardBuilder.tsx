import { useEffect, useState, type FormEvent } from "react";
import {
  BarChart3,
  CloudRain,
  Droplets,
  Gauge,
  LayoutGrid,
  Loader2,
  MapPin,
  Sparkles,
  Thermometer,
  Wand2,
} from "lucide-react";
import { generateDashboard, getDashboardPresets } from "@/api/endpoints";
import {
  getSampleDistrictWeather,
  getSampleHumidityTrend,
  getSampleOverview,
  getSampleRainfallTrend,
  getSampleTemperatureTrend,
} from "@/lib/sampleData";
import { KPICard } from "@/components/common/KPICard";
import { ChartCard } from "@/components/common/ChartCard";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { DistrictFilter } from "@/components/common/DistrictFilter";
import { TemperatureChart } from "@/components/charts/TemperatureChart";
import { RainfallChart } from "@/components/charts/RainfallChart";
import { HumidityChart } from "@/components/charts/HumidityChart";
import { ComparisonChart } from "@/components/charts/ComparisonChart";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { DashboardSpec, DashboardWidget, DistrictWeather } from "@/types";

const FALLBACK_PRESETS: DashboardSpec[] = [
  {
    id: "overview",
    title: "State Overview",
    description: "High-level weather summary for all 38 Tamil Nadu districts",
    widgets: [
      { type: "stat_card", title: "Avg Temperature", metric: "avg_temperature", config: {} },
      { type: "stat_card", title: "Total Rainfall", metric: "total_rainfall", config: {} },
      { type: "stat_card", title: "Avg Humidity", metric: "avg_humidity", config: {} },
      { type: "line_chart", title: "Temperature Trend", metric: "temperature_trend", config: {} },
      { type: "bar_chart", title: "Rainfall by District", metric: "rainfall_by_district", config: {} },
    ],
  },
  {
    id: "temperature_monitor",
    title: "Temperature Monitor",
    description: "Thermal trajectory and district peak comparisons",
    widgets: [
      { type: "stat_card", title: "Peak Temperature", metric: "max_temperature", config: {} },
      { type: "stat_card", title: "Lowest Temperature", metric: "min_temperature", config: {} },
      { type: "line_chart", title: "Temperature Trend", metric: "temperature_trend", config: {} },
      { type: "bar_chart", title: "District Comparison", metric: "district_comparison", config: {} },
    ],
  },
  {
    id: "rainfall_tracker",
    title: "Rainfall Tracker",
    description: "Monsoon precipitation monitoring and cumulative depth",
    widgets: [
      { type: "stat_card", title: "Total Rainfall", metric: "total_rainfall", config: {} },
      { type: "stat_card", title: "Avg Humidity", metric: "avg_humidity", config: {} },
      { type: "bar_chart", title: "Monthly Rainfall", metric: "rainfall_trend", config: {} },
      { type: "table", title: "District Rainfall Summary", metric: "district_table", config: {} },
    ],
  },
];

const TABLE_COLUMNS: DataTableColumn<DistrictWeather>[] = [
  { key: "district", header: "District" },
  {
    key: "avg_temp",
    header: "Avg Temp",
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

function renderKpiWidget(widget: DashboardWidget, idx: number) {
  const overview = getSampleOverview();
  const metric = (widget.metric || widget.title || "").toLowerCase();

  if (metric.includes("rain")) {
    return (
      <KPICard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        value={`${overview.total_rainfall?.toFixed(0) ?? "—"} mm`}
        subtitle="Preview baseline"
        icon={CloudRain}
        accent="blue"
      />
    );
  }
  if (metric.includes("humid")) {
    return (
      <KPICard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        value={`${overview.avg_humidity?.toFixed(1) ?? "—"}%`}
        subtitle="Preview baseline"
        icon={Droplets}
        accent="emerald"
      />
    );
  }
  if (metric.includes("max")) {
    return (
      <KPICard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        value={`${overview.max_temperature?.toFixed(1) ?? "—"}°C`}
        subtitle="Peak recorded"
        icon={Thermometer}
        accent="rose"
      />
    );
  }
  if (metric.includes("min")) {
    return (
      <KPICard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        value={`${overview.min_temperature?.toFixed(1) ?? "—"}°C`}
        subtitle="Coolest recorded"
        icon={Thermometer}
        accent="cyan"
      />
    );
  }
  if (metric.includes("aqi")) {
    return (
      <KPICard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        value="68 AQI"
        subtitle="Satisfactory"
        icon={Gauge}
        accent="indigo"
      />
    );
  }

  return (
    <KPICard
      key={`${widget.title}-${idx}`}
      title={widget.title}
      value={`${overview.avg_temperature?.toFixed(1) ?? "—"}°C`}
      subtitle="38 districts"
      icon={Thermometer}
      accent="amber"
    />
  );
}

function renderRichWidget(
  widget: DashboardWidget,
  idx: number,
  districtScope?: string
) {
  const metric = (widget.metric || widget.title || "").toLowerCase();
  const districts = getSampleDistrictWeather();
  const scopedDistrict =
    districtScope && districtScope !== "all" ? districtScope : undefined;

  if (widget.type === "line_chart") {
    if (metric.includes("rain")) {
      return (
        <ChartCard
          key={`${widget.title}-${idx}`}
          title={widget.title}
          subtitle="Generated precipitation view"
        >
          <RainfallChart data={getSampleRainfallTrend(scopedDistrict)} />
        </ChartCard>
      );
    }
    if (metric.includes("humid")) {
      return (
        <ChartCard
          key={`${widget.title}-${idx}`}
          title={widget.title}
          subtitle="Generated humidity area chart"
        >
          <HumidityChart data={getSampleHumidityTrend()} />
        </ChartCard>
      );
    }
    return (
      <ChartCard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        subtitle={scopedDistrict ? `${scopedDistrict} temperature curve` : "State temperature curve"}
      >
        <TemperatureChart data={getSampleTemperatureTrend(scopedDistrict)} />
      </ChartCard>
    );
  }

  if (widget.type === "table") {
    return (
      <ChartCard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        subtitle="Generated district breakdown table"
        className="lg:col-span-2"
      >
        <DataTable
          data={
            scopedDistrict
              ? districts.filter((d) => d.district === scopedDistrict)
              : districts.slice(0, 12)
          }
          columns={TABLE_COLUMNS}
          searchable={false}
        />
      </ChartCard>
    );
  }

  if (widget.type === "bar_chart" || widget.type === "chart") {
    if (metric.includes("trend") && metric.includes("rain")) {
      return (
        <ChartCard
          key={`${widget.title}-${idx}`}
          title={widget.title}
          subtitle="Monthly rainfall distribution"
        >
          <RainfallChart data={getSampleRainfallTrend(scopedDistrict)} />
        </ChartCard>
      );
    }
    return (
      <ChartCard
        key={`${widget.title}-${idx}`}
        title={widget.title}
        subtitle="District meteorological comparison"
      >
        <ComparisonChart
          data={
            scopedDistrict
              ? districts.filter((d) => d.district === scopedDistrict)
              : districts.slice(0, 8)
          }
        />
      </ChartCard>
    );
  }

  // Fallback for pie_chart / map / heatmap / gauge widgets
  return (
    <ChartCard
      key={`${widget.title}-${idx}`}
      title={widget.title}
      subtitle={`Widget type: ${widget.type.replace("_", " ")}`}
      filters={
        <Badge variant="secondary" className="gap-1 text-xs">
          <MapPin className="size-3 text-blue-600" />
          {scopedDistrict || "All 38 Districts"}
        </Badge>
      }
    >
      <ComparisonChart
        data={
          scopedDistrict
            ? districts.filter((d) => d.district === scopedDistrict)
            : districts.slice(0, 8)
        }
        series={[
          {
            dataKey: "total_rainfall",
            label: "Rainfall (mm)",
            color: "#3b82f6",
          },
          {
            dataKey: "avg_temp",
            label: "Avg Temp (°C)",
            color: "#f59e0b",
          },
        ]}
      />
    </ChartCard>
  );
}

export function DashboardBuilder() {
  const [prompt, setPrompt] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("all");
  const [presets, setPresets] = useState<DashboardSpec[]>(FALLBACK_PRESETS);
  const [activeSpec, setActiveSpec] = useState<DashboardSpec>(
    FALLBACK_PRESETS[0]
  );
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getDashboardPresets()
      .then((list) => {
        if (active && list.length > 0) {
          setPresets(list);
          setActiveSpec(list[0]);
        }
      })
      .catch(() => {
        // Keep built-in fallback presets when backend is offline
      });
    return () => {
      active = false;
    };
  }, []);

  const handleGenerate = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || generating) return;

    setGenerating(true);
    setNotice(null);

    try {
      const spec = await generateDashboard({
        prompt: trimmed,
        districts:
          selectedDistrict !== "all" ? [selectedDistrict] : undefined,
      });
      setActiveSpec(spec);
      if (spec.fallback && spec.error) {
        setNotice(spec.error);
      }
    } catch (err) {
      const msg =
        err instanceof Error ? err.message : "Backend generation unavailable.";
      setNotice(
        `${msg} Generated an intelligent local layout preview for your prompt.`
      );
      setActiveSpec({
        title: `Custom: ${trimmed.slice(0, 48)}`,
        description: trimmed,
        districts: selectedDistrict !== "all" ? [selectedDistrict] : [],
        widgets: [
          { type: "stat_card", title: "Avg Temperature", metric: "avg_temperature", config: {} },
          { type: "stat_card", title: "Total Rainfall", metric: "total_rainfall", config: {} },
          { type: "stat_card", title: "Avg Humidity", metric: "avg_humidity", config: {} },
          { type: "line_chart", title: "Temperature Trajectory", metric: "temperature_trend", config: {} },
          { type: "bar_chart", title: "Rainfall Distribution", metric: "rainfall_trend", config: {} },
        ],
        fallback: true,
      });
    } finally {
      setGenerating(false);
    }
  };

  const kpiWidgets = activeSpec.widgets.filter(
    (w) => w.type === "kpi" || w.type === "stat_card"
  );
  const visualWidgets = activeSpec.widgets.filter(
    (w) => w.type !== "kpi" && w.type !== "stat_card"
  );
  const districtScope =
    activeSpec.districts?.[0] ??
    (selectedDistrict !== "all" ? selectedDistrict : undefined);

  return (
    <div className="space-y-6">
      {/* Prompt Builder Controls */}
      <Card className="bg-white shadow-xs">
        <CardHeader className="border-b border-slate-100 pb-4">
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
              <Wand2 className="size-4" />
            </div>
            <div>
              <CardTitle className="text-base font-semibold text-slate-900">
                AI Weather Dashboard Generator
              </CardTitle>
              <p className="text-xs text-slate-500">
                Describe the Tamil Nadu weather dashboard you want to compose
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="space-y-4 pt-4">
          <form
            onSubmit={handleGenerate}
            className="flex flex-col gap-3 md:flex-row"
          >
            <Input
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., Build a Northeast Monsoon dashboard comparing Chennai, Cuddalore, and Nagapattinam rainfall"
              className="h-10 flex-1 bg-slate-50 focus-visible:bg-white"
            />
            <DistrictFilter
              value={selectedDistrict}
              onChange={setSelectedDistrict}
            />
            <Button
              type="submit"
              disabled={generating || !prompt.trim()}
              className="h-10 gap-1.5 px-5"
            >
              {generating ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              {generating ? "Generating..." : "Generate Dashboard"}
            </Button>
          </form>

          {/* Preset switcher */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 text-xs font-medium text-slate-500">
              <LayoutGrid className="size-3.5" />
              Presets:
            </span>
            {presets.map((preset) => (
              <Button
                key={preset.id || preset.title}
                type="button"
                variant={
                  activeSpec.title === preset.title ? "default" : "outline"
                }
                size="sm"
                onClick={() => {
                  setActiveSpec(preset);
                  setNotice(null);
                }}
                className="h-7 text-xs"
              >
                {preset.title}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {notice && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5 text-xs text-amber-800">
          {notice}
        </div>
      )}

      {/* Rendered Dashboard Preview Area */}
      <div className="space-y-5 rounded-2xl border border-slate-200 bg-white/60 p-4 md:p-6">
        <div className="flex flex-col gap-2 border-b border-slate-200 pb-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <BarChart3 className="size-5 text-blue-600" />
              <h2 className="text-lg font-semibold text-slate-900">
                {activeSpec.title}
              </h2>
            </div>
            <p className="mt-0.5 text-xs text-slate-500">
              {activeSpec.description}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">
              {activeSpec.widgets.length} Widgets
            </Badge>
            {districtScope && (
              <Badge className="bg-blue-100 text-blue-700">
                {districtScope}
              </Badge>
            )}
          </div>
        </div>

        {kpiWidgets.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {kpiWidgets.map((widget, idx) => renderKpiWidget(widget, idx))}
          </div>
        )}

        {visualWidgets.length > 0 && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {visualWidgets.map((widget, idx) =>
              renderRichWidget(widget, idx, districtScope)
            )}
          </div>
        )}
      </div>
    </div>
  );
}
