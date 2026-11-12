import { apiClient } from "./client";
import type {
  AirQuality,
  ApiResponse,
  ChatResponse,
  ChartSpec,
  CurrentWeather,
  DashboardSpec,
  DashboardWidget,
  DateRangeParams,
  DistrictWeather,
  PeriodComparisonData,
  RainfallData,
  RainfallQualityMetadata,
  TemperatureData,
  WeatherOverview,
} from "@/types";

type RawRecord = Record<string, unknown>;

function toNumber(val: unknown, fallback = 0): number {
  if (typeof val === "number" && !Number.isNaN(val)) return val;
  if (typeof val === "string" && val.trim() !== "") {
    const parsed = Number(val);
    if (!Number.isNaN(parsed)) return parsed;
  }
  return fallback;
}

function toNullableNumber(val: unknown): number | null {
  if (val === null || val === undefined || val === "") return null;
  if (typeof val === "number" && !Number.isNaN(val)) return val;
  const parsed = Number(val);
  return Number.isNaN(parsed) ? null : parsed;
}

function toStr(val: unknown, fallback = ""): string {
  return typeof val === "string" ? val : val != null ? String(val) : fallback;
}

function normalizeTemperatureRow(row: RawRecord): TemperatureData {
  return {
    date: toStr(row.date ?? row.date_key),
    district: row.district ? toStr(row.district) : undefined,
    max_temp: toNumber(row.max_temp ?? row.temperature_2m_max ?? row.max_c),
    min_temp: toNumber(row.min_temp ?? row.temperature_2m_min ?? row.min_c),
    avg_temp: toNumber(row.avg_temp ?? row.temperature_2m_mean ?? row.avg_c),
  };
}

function normalizeRainfallRow(row: RawRecord): RainfallData {
  const rainfall = toNumber(row.rainfall_mm ?? row.precipitation_sum);
  const category =
    row.category != null
      ? toStr(row.category)
      : rainfall >= 64.5
        ? "Heavy"
        : rainfall >= 15.6
          ? "Moderate"
          : rainfall > 0
            ? "Light"
            : "Dry";

  return {
    date: toStr(row.date ?? row.date_key),
    district: row.district ? toStr(row.district) : undefined,
    rainfall_mm: rainfall,
    cumulative_mm:
      row.cumulative_mm != null
        ? toNumber(row.cumulative_mm)
        : undefined,
    category,
  };
}

function normalizeDistrictRow(row: RawRecord): DistrictWeather {
  return {
    district: toStr(row.district ?? row.district_name ?? row.name),
    avg_temp: toNumber(
      row.avg_temp ?? row.avg_temperature ?? row.temperature_2m_mean
    ),
    max_temp: toNumber(
      row.max_temp ?? row.max_temperature ?? row.temperature_2m_max
    ),
    min_temp: toNumber(
      row.min_temp ?? row.min_temperature ?? row.temperature_2m_min
    ),
    total_rainfall: toNumber(
      row.total_rainfall ?? row.rainfall_mm ?? row.precipitation_sum
    ),
    avg_humidity: toNumber(
      row.avg_humidity ?? row.humidity_pct ?? row.relative_humidity_2m_mean
    ),
    wind_speed:
      row.wind_speed != null || row.wind_kph != null
        ? toNumber(row.wind_speed ?? row.wind_kph)
        : undefined,
    current_temp:
      row.current_temp != null || row.temperature_c != null
        ? toNumber(row.current_temp ?? row.temperature_c)
        : undefined,
    current_condition:
      row.current_condition != null || row.condition_text != null
        ? toStr(row.current_condition ?? row.condition_text)
        : undefined,
    latitude:
      row.latitude != null ? toNumber(row.latitude) : undefined,
    longitude:
      row.longitude != null ? toNumber(row.longitude) : undefined,
    elevation_m:
      row.elevation_m != null ? toNumber(row.elevation_m) : undefined,
    zone: row.zone ? toStr(row.zone) : undefined,
  };
}

function normalizeCurrentWeatherRow(row: RawRecord): CurrentWeather {
  const temp = toNumber(row.temperature ?? row.temperature_c);
  return {
    district: toStr(row.district ?? row.district_name),
    temperature: temp,
    feels_like: toNumber(row.feels_like ?? row.feels_like_c, temp),
    humidity: toNumber(row.humidity ?? row.humidity_percentage),
    wind_speed: toNumber(row.wind_speed ?? row.wind_kph),
    wind_direction: toStr(row.wind_direction ?? row.wind_dir, "NE"),
    pressure: toNumber(row.pressure ?? row.pressure_mb, 1012),
    condition: toStr(row.condition ?? row.condition_text, "Clear"),
    last_updated: toStr(
      row.last_updated ?? row.last_updated_epoch,
      new Date().toISOString()
    ),
    precipitation_mm: toNumber(row.precipitation_mm),
    uv_index: row.uv_index != null ? toNumber(row.uv_index) : undefined,
    cloud_cover: row.cloud_cover != null ? toNumber(row.cloud_cover) : undefined,
    visibility_km: row.visibility_km != null ? toNumber(row.visibility_km) : undefined,
  };
}

function normalizeAirQualityRow(row: RawRecord): AirQuality {
  const aqi = toNumber(row.aqi ?? row.us_epa_index, 1);
  const category = toStr(
    row.category ?? row.us_epa_category,
    aqi <= 50 ? "Good" : aqi <= 100 ? "Moderate" : "Unhealthy"
  );

  return {
    district: toStr(row.district ?? row.district_name),
    aqi,
    category,
    dominant_pollutant: row.dominant_pollutant
      ? toStr(row.dominant_pollutant)
      : undefined,
    pm25: toNumber(row.pm25 ?? row.pm2_5),
    pm10: toNumber(row.pm10),
    co: toNumber(row.co ?? row.carbon_monoxide),
    no2: toNumber(row.no2 ?? row.nitrogen_dioxide),
    so2: toNumber(row.so2 ?? row.sulphur_dioxide),
    o3: toNumber(row.o3 ?? row.ozone),
    us_epa_index: row.us_epa_index != null ? toNumber(row.us_epa_index) : undefined,
    us_epa_category: row.us_epa_category ? toStr(row.us_epa_category) : undefined,
    gb_defra_index: row.gb_defra_index != null ? toNumber(row.gb_defra_index) : undefined,
    gb_defra_category: row.gb_defra_category ? toStr(row.gb_defra_category) : undefined,
    last_updated: toStr(
      row.last_updated ?? row.last_updated_epoch,
      new Date().toISOString()
    ),
  };
}

function normalizeWidget(raw: RawRecord): DashboardWidget {
  const typeStr = toStr(raw.type, "kpi");
  const validTypes = [
    "kpi",
    "stat_card",
    "chart",
    "line_chart",
    "bar_chart",
    "pie_chart",
    "table",
    "map",
    "heatmap",
    "gauge",
  ] as const;
  const widgetType = (
    validTypes.includes(typeStr as (typeof validTypes)[number])
      ? typeStr
      : "kpi"
  ) as DashboardWidget["type"];

  return {
    type: widgetType,
    title: toStr(raw.title ?? raw.label ?? raw.metric, "Metric"),
    metric: raw.metric ? toStr(raw.metric) : undefined,
    config:
      raw.config && typeof raw.config === "object"
        ? (raw.config as Record<string, unknown>)
        : { metric: raw.metric },
    data: raw.data,
  };
}

export async function getOverview(
  params?: DateRangeParams
): Promise<ApiResponse<WeatherOverview>> {
  const res = await apiClient.get<RawRecord>("/api/overview", { params });
  const raw = res.data || {};
  const payload = (raw.data as RawRecord) || raw;

  const overview: WeatherOverview = {
    districts_covered:
      toNumber(payload.districts_covered ?? payload.districts_reporting, 38) || 38,
    avg_temperature: toNullableNumber(
      payload.avg_temperature ?? payload.avg_temperature_c
    ),
    max_temperature: toNullableNumber(
      payload.max_temperature ?? payload.max_temperature_c
    ),
    min_temperature: toNullableNumber(
      payload.min_temperature ?? payload.min_temperature_c
    ),
    total_rainfall: toNullableNumber(
      payload.total_rainfall ?? payload.total_rainfall_mm
    ),
    avg_humidity: toNullableNumber(
      payload.avg_humidity ?? payload.avg_humidity_pct
    ),
    active_alerts: toNumber(payload.active_alerts, 0),
    latest_observation: payload.latest_observation
      ? toStr(payload.latest_observation)
      : undefined,
    temperature_trend: Array.isArray(payload.temperature_trend)
      ? (payload.temperature_trend as RawRecord[]).map(normalizeTemperatureRow)
      : [],
    rainfall_trend: Array.isArray(payload.rainfall_trend)
      ? (payload.rainfall_trend as RawRecord[]).map(normalizeRainfallRow)
      : [],
    district_comparison: Array.isArray(payload.district_comparison)
      ? (payload.district_comparison as RawRecord[]).map(normalizeDistrictRow)
      : [],
    rainfall_quality: payload.rainfall_quality as RainfallQualityMetadata | undefined,
  };

  return {
    status: toStr(raw.status, "success"),
    data: overview,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getTemperature(
  params?: DateRangeParams
): Promise<ApiResponse<TemperatureData[]>> {
  const res = await apiClient.get<RawRecord>("/api/temperature", { params });
  const raw = res.data || {};
  const rows = Array.isArray(raw.data)
    ? (raw.data as RawRecord[]).map(normalizeTemperatureRow)
    : [];

  return {
    status: toStr(raw.status, "success"),
    data: rows,
    monthly_averages: Array.isArray(raw.monthly_averages)
      ? (raw.monthly_averages as unknown[])
      : undefined,
    distribution:
      raw.distribution && typeof raw.distribution === "object"
        ? (raw.distribution as Record<string, unknown>)
        : undefined,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getRainfall(
  params?: DateRangeParams
): Promise<ApiResponse<RainfallData[]>> {
  const res = await apiClient.get<RawRecord>("/api/rainfall", { params });
  const raw = res.data || {};
  const rows = Array.isArray(raw.data)
    ? (raw.data as RawRecord[]).map(normalizeRainfallRow)
    : [];

  return {
    status: toStr(raw.status, "success"),
    data: rows,
    monthly_trend: Array.isArray(raw.monthly_trend)
      ? (raw.monthly_trend as unknown[])
      : undefined,
    district_summary: Array.isArray(raw.district_summary)
      ? (raw.district_summary as unknown[])
      : undefined,
    kpis:
      raw.kpis && typeof raw.kpis === "object"
        ? (raw.kpis as Record<string, unknown>)
        : undefined,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getDistricts(
  params?: DateRangeParams
): Promise<ApiResponse<DistrictWeather[]>> {
  const res = await apiClient.get<RawRecord>("/api/districts", { params });
  const raw = res.data || {};
  const rows = Array.isArray(raw.data)
    ? (raw.data as RawRecord[]).map(normalizeDistrictRow)
    : [];

  return {
    status: toStr(raw.status, "success"),
    data: rows,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getDistrictByName(
  name: string,
  params?: Omit<DateRangeParams, "district">
): Promise<ApiResponse<DistrictWeather[]>> {
  const res = await apiClient.get<RawRecord>(
    `/api/districts/${encodeURIComponent(name)}`,
    { params }
  );
  const raw = res.data || {};
  const payload = raw.data;
  const rows = Array.isArray(payload)
    ? (payload as RawRecord[]).map(normalizeDistrictRow)
    : payload && typeof payload === "object"
      ? [normalizeDistrictRow(payload as RawRecord)]
      : [];

  return {
    status: toStr(raw.status, "success"),
    data: rows,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getCurrentWeather(params?: {
  district?: string;
  date?: string;
}): Promise<ApiResponse<CurrentWeather[]>> {
  const res = await apiClient.get<RawRecord>("/api/current-weather", { params });
  const raw = res.data || {};
  const rows = Array.isArray(raw.data)
    ? (raw.data as RawRecord[]).map(normalizeCurrentWeatherRow)
    : [];

  return {
    status: toStr(raw.status, "success"),
    data: rows,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getComparison(params: {
  period_a_start: string;
  period_a_end: string;
  period_b_start: string;
  period_b_end: string;
  district?: string;
}): Promise<ApiResponse<PeriodComparisonData>> {
  const res = await apiClient.get<RawRecord>("/api/overview/comparison", { params });
  const raw = res.data || {};
  return {
    status: toStr(raw.status, "success"),
    data: raw.data as PeriodComparisonData,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
  };
}

export async function getHistorical(
  params?: DateRangeParams
): Promise<ApiResponse<RawRecord[]>> {
  const res = await apiClient.get<RawRecord>("/api/historical", { params });
  const raw = res.data || {};
  const rows = Array.isArray(raw.data) ? (raw.data as RawRecord[]) : [];
  return {
    status: toStr(raw.status, "success"),
    data: rows,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function getAirQuality(
  params?: DateRangeParams
): Promise<ApiResponse<AirQuality[]>> {
  const res = await apiClient.get<RawRecord>("/api/air-quality", { params });
  const raw = res.data || {};
  const rows = Array.isArray(raw.data)
    ? (raw.data as RawRecord[]).map(normalizeAirQualityRow)
    : [];

  return {
    status: toStr(raw.status, "success"),
    data: rows,
    message: raw.message ? toStr(raw.message) : undefined,
    source: raw.source ? toStr(raw.source) : undefined,
    filters: raw.filters as Record<string, string | null> | undefined,
  };
}

export async function chatWithAI(
  message: string,
  context?: string,
  conversationId?: string,
  district?: string
): Promise<ChatResponse> {
  const res = await apiClient.post<RawRecord>(
    "/api/ai/chat",
    {
      message,
      query: message,
      context,
      conversation_id: conversationId,
      district,
    },
    { timeout: 60000 } // 60s timeout to allow Microsoft Fabric + local Ollama inference
  );
  const raw = res.data || {};
  return {
    conversation_id: raw.conversation_id ? toStr(raw.conversation_id) : undefined,
    answer: raw.answer ? toStr(raw.answer) : undefined,
    response: toStr(raw.response ?? raw.answer, "No response generated."),
    intent: raw.intent ? toStr(raw.intent) : null,
    district: raw.district ? toStr(raw.district) : null,
    districts: Array.isArray(raw.districts) ? (raw.districts as string[]) : undefined,
    confidence:
      typeof raw.confidence === "number" ? raw.confidence : null,
    sources: Array.isArray(raw.sources)
      ? (raw.sources as string[])
      : undefined,
    applied_filters: raw.applied_filters as Record<string, unknown> | undefined,
    observation_timestamp: raw.observation_timestamp ? toStr(raw.observation_timestamp) : null,
    data_summary: raw.data_summary as Record<string, unknown> | undefined,
    chart: (raw.chart as ChartSpec) || null,
    follow_up_suggestions: Array.isArray(raw.follow_up_suggestions)
      ? (raw.follow_up_suggestions as string[])
      : [],
  };
}

export async function clearChatSession(conversationId: string): Promise<void> {
  try {
    await apiClient.delete(`/api/ai/session/${encodeURIComponent(conversationId)}`);
  } catch {
    // Graceful ignore
  }
}

export async function generateDashboard(
  request: string | { prompt: string; districts?: string[] }
): Promise<DashboardSpec> {
  const body =
    typeof request === "string" ? { prompt: request } : request;
  const res = await apiClient.post<RawRecord>("/api/dashboard/generate", body);
  const raw = res.data || {};
  return {
    id: raw.id ? toStr(raw.id) : undefined,
    title: toStr(raw.title ?? raw.name, "Custom Weather Dashboard"),
    description: toStr(raw.description, body.prompt),
    districts: Array.isArray(raw.districts)
      ? (raw.districts as string[])
      : [],
    widgets: Array.isArray(raw.widgets)
      ? (raw.widgets as RawRecord[]).map(normalizeWidget)
      : [],
    generated: Boolean(raw.generated),
    fallback: Boolean(raw.fallback),
    error: raw.error ? toStr(raw.error) : null,
  };
}

export async function getDashboardPresets(): Promise<DashboardSpec[]> {
  const res = await apiClient.get<RawRecord[]>("/api/dashboard/presets");
  const list = Array.isArray(res.data) ? res.data : [];
  return list.map((raw) => ({
    id: raw.id ? toStr(raw.id) : undefined,
    title: toStr(raw.title ?? raw.name, "Preset Dashboard"),
    description: toStr(raw.description),
    districts: Array.isArray(raw.districts)
      ? (raw.districts as string[])
      : [],
    widgets: Array.isArray(raw.widgets)
      ? (raw.widgets as RawRecord[]).map(normalizeWidget)
      : [],
  }));
}

export interface OperationalStatus {
  status: string;
  service: string;
  environment: string;
  uptime_seconds: number;
  api: {
    status: string;
    version: string;
    avg_latency_ms: number;
  };
  fabric: {
    status: string;
    total_queries: number;
    avg_latency_ms: number;
    last_query_timestamp: string | null;
  };
  ai: {
    status: string;
    active_provider: string;
    provider_reason: string;
    ollama_available: boolean;
    avg_latency_ms: number;
  };
  data_freshness: {
    status: string;
    latest_observation: string;
    districts_reporting: number;
    total_districts: number;
    coverage_pct: number;
  };
}

export async function getOperationalStatus(): Promise<OperationalStatus> {
  const res = await apiClient.get<OperationalStatus>("/api/monitoring/operational-status");
  return res.data;
}
