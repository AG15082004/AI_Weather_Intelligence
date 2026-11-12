export interface ApiResponse<T> {
  data: T;
  status: string;
  message?: string;
  timestamp?: string;
  source?: string;
  filters?: Record<string, string | null>;
  monthly_averages?: unknown[];
  distribution?: Record<string, unknown>;
  monthly_trend?: unknown[];
  district_summary?: unknown[];
  kpis?: Record<string, unknown>;
}

export interface TemperatureData {
  date: string;
  district?: string;
  max_temp: number;
  min_temp: number;
  avg_temp: number;
}

export interface RainfallData {
  date: string;
  district?: string;
  rainfall_mm: number;
  cumulative_mm?: number;
  category?: string;
}

export interface HumidityData {
  date: string;
  district?: string;
  humidity_pct: number;
}

export interface DistrictWeather {
  district: string;
  avg_temp: number;
  max_temp: number;
  min_temp: number;
  total_rainfall: number;
  avg_humidity: number;
  wind_speed?: number;
  current_temp?: number;
  current_condition?: string;
  latitude?: number;
  longitude?: number;
  elevation_m?: number;
  zone?: string;
}

export interface RainfallQualityMetadata {
  completeness_pct: number;
  measured_days: number;
  missing_days: number;
  measured_zero_days: number;
  positive_rainfall_days: number;
  total_records: number;
  status: "complete" | "partial" | "sparse" | "unmeasured";
  message: string;
}

export interface MetricDelta {
  current_val: number | null;
  previous_val: number | null;
  absolute_change: number | null;
  percentage_change: number | null;
  direction: "up" | "down" | "neutral";
  unit: string;
}

export interface PeriodComparisonData {
  period_a_label: string;
  period_b_label: string;
  period_a_range: { start?: string; end?: string };
  period_b_range: { start?: string; end?: string };
  district: string;
  temperature: MetricDelta;
  rainfall: MetricDelta;
  humidity: MetricDelta;
}

export interface WeatherOverview {
  districts_covered: number;
  avg_temperature: number | null;
  max_temperature: number | null;
  min_temperature: number | null;
  total_rainfall: number | null;
  avg_humidity: number | null;
  active_alerts?: number;
  latest_observation?: string;
  temperature_trend: TemperatureData[];
  rainfall_trend: RainfallData[];
  humidity_trend?: HumidityData[];
  district_comparison: DistrictWeather[];
  rainfall_quality?: RainfallQualityMetadata;
}

export interface CurrentWeather {
  district: string;
  temperature: number;
  feels_like: number;
  humidity: number;
  wind_speed: number;
  wind_direction: string;
  pressure: number;
  condition: string;
  last_updated: string;
  precipitation_mm?: number;
  uv_index?: number;
  cloud_cover?: number;
  visibility_km?: number;
}

export interface AirQuality {
  district: string;
  aqi: number;
  category: string;
  dominant_pollutant?: string;
  pm25: number;
  pm10: number;
  co: number;
  no2: number;
  so2: number;
  o3: number;
  us_epa_index?: number;
  us_epa_category?: string;
  gb_defra_index?: number;
  gb_defra_category?: string;
  last_updated: string;
}

export interface ChartSeriesSpec {
  name: string;
  key: string;
  color?: string;
}

export interface ChartSpec {
  type: "line" | "bar" | "grouped_bar" | "area" | "pie" | "table";
  title: string;
  subtitle?: string;
  x_axis: string;
  y_axis: string;
  series: ChartSeriesSpec[];
  data: Record<string, unknown>[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  intent?: string | null;
  district?: string | null;
  districts?: string[];
  confidence?: number | null;
  sources?: string[];
  applied_filters?: Record<string, unknown>;
  observation_timestamp?: string | null;
  chart?: ChartSpec | null;
  follow_up_suggestions?: string[];
  isError?: boolean;
  retryQuery?: string;
}

export interface ChatResponse {
  conversation_id?: string;
  answer?: string;
  response: string;
  intent?: string | null;
  district?: string | null;
  districts?: string[];
  confidence?: number | null;
  sources?: string[];
  applied_filters?: Record<string, unknown>;
  observation_timestamp?: string | null;
  data_summary?: Record<string, unknown>;
  chart?: ChartSpec | null;
  follow_up_suggestions?: string[];
  isError?: boolean;
  retryQuery?: string;
}

export interface DashboardWidget {
  type:
    | "kpi"
    | "stat_card"
    | "chart"
    | "line_chart"
    | "bar_chart"
    | "pie_chart"
    | "table"
    | "map"
    | "heatmap"
    | "gauge";
  title: string;
  metric?: string;
  config: Record<string, unknown>;
  data?: unknown;
}

export interface DashboardSpec {
  id?: string;
  title: string;
  description: string;
  districts?: string[];
  widgets: DashboardWidget[];
  generated?: boolean;
  fallback?: boolean;
  error?: string | null;
}

export interface DateRangeParams {
  start_date?: string;
  end_date?: string;
  district?: string;
}
