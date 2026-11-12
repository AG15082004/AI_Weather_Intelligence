import { TAMIL_NADU_DISTRICTS } from "./districts";
import type {
  AirQuality,
  CurrentWeather,
  DistrictWeather,
  HumidityData,
  RainfallData,
  TemperatureData,
  WeatherOverview,
} from "@/types";

function seededMetric(name: string, salt: number): number {
  let hash = salt;
  for (let i = 0; i < name.length; i += 1) {
    hash = (hash * 31 + name.charCodeAt(i)) % 10000;
  }
  return hash / 10000;
}

const DISTRICT_ZONES: Record<string, string> = {
  Chennai: "North Eastern",
  Tiruvallur: "North Eastern",
  Chengalpattu: "North Eastern",
  Kanchipuram: "North Eastern",
  Vellore: "North Western",
  Ranipet: "North Eastern",
  Tirupathur: "North Western",
  Tiruvannamalai: "North Eastern",
  Viluppuram: "North Eastern",
  Kallakurichi: "North Eastern",
  Cuddalore: "Cauvery Delta",
  Nilgiris: "Hilly",
  Coimbatore: "Western",
  Tiruppur: "Western",
  Erode: "Western",
  Salem: "North Western",
  Namakkal: "North Western",
  Dharmapuri: "North Western",
  Krishnagiri: "North Western",
  Tiruchirappalli: "Cauvery Delta",
  Karur: "Western",
  Perambalur: "Cauvery Delta",
  Ariyalur: "Cauvery Delta",
  Thanjavur: "Cauvery Delta",
  Tiruvarur: "Cauvery Delta",
  Nagapattinam: "Cauvery Delta",
  Mayiladuthurai: "Cauvery Delta",
  Pudukkottai: "Cauvery Delta",
  Madurai: "Southern",
  Theni: "Western",
  Dindigul: "Southern",
  Sivaganga: "Southern",
  Ramanathapuram: "Southern",
  Virudhunagar: "Southern",
  Thoothukudi: "Southern",
  Tirunelveli: "Southern",
  Tenkasi: "High Rainfall",
  Kanyakumari: "High Rainfall",
};

const CONDITIONS = [
  "Sunny",
  "Partly Cloudy",
  "Humid & Breezy",
  "Light Showers",
  "Clear Sky",
  "Scattered Clouds",
];

const DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];

export function getSampleDistrictWeather(): DistrictWeather[] {
  return TAMIL_NADU_DISTRICTS.map((district) => {
    const r = seededMetric(district, 17);
    const r2 = seededMetric(district, 43);
    const isHilly = district === "Nilgiris";
    const isCoastal = [
      "Chennai",
      "Cuddalore",
      "Nagapattinam",
      "Thoothukudi",
      "Kanyakumari",
      "Ramanathapuram",
      "Mayiladuthurai",
      "Tiruvarur",
      "Chengalpattu",
    ].includes(district);

    const avgTemp = isHilly
      ? Number((17.5 + r * 3.5).toFixed(1))
      : Number((28.5 + r * 6.2).toFixed(1));
    const maxTemp = Number((avgTemp + 4.2 + r2 * 2.3).toFixed(1));
    const minTemp = Number((avgTemp - 4.5 - r * 1.8).toFixed(1));
    const totalRainfall = isHilly || district === "Kanyakumari" || district === "Tenkasi"
      ? Number((145 + r2 * 130).toFixed(1))
      : isCoastal
        ? Number((85 + r2 * 110).toFixed(1))
        : Number((35 + r2 * 75).toFixed(1));
    const avgHumidity = isCoastal || isHilly
      ? Number((70 + r * 18).toFixed(1))
      : Number((52 + r * 20).toFixed(1));

    return {
      district,
      avg_temp: avgTemp,
      max_temp: maxTemp,
      min_temp: minTemp,
      total_rainfall: totalRainfall,
      avg_humidity: avgHumidity,
      wind_speed: Number((9 + r2 * 14).toFixed(1)),
      zone: DISTRICT_ZONES[district] || "State Interior",
    };
  });
}

export function getSampleTemperatureTrend(district?: string): TemperatureData[] {
  const offset = district ? seededMetric(district, 11) * 4 - 2 : 0;
  const isNilgiris = district === "Nilgiris";
  const base = isNilgiris ? 18.5 : 30.2 + offset;
  const dates = [
    "2025-01-01",
    "2025-02-01",
    "2025-03-01",
    "2025-04-01",
    "2025-05-01",
    "2025-06-01",
    "2025-07-01",
    "2025-08-01",
    "2025-09-01",
    "2025-10-01",
    "2025-11-01",
    "2025-12-01",
  ];
  const seasonalCurve = [-3.2, -2.1, 0.4, 2.8, 4.1, 2.5, 1.4, 1.1, 0.5, -1.0, -2.4, -3.4];

  return dates.map((date, idx) => {
    const avg = Number((base + seasonalCurve[idx]).toFixed(1));
    return {
      date,
      district: district || "Tamil Nadu Avg",
      avg_temp: avg,
      max_temp: Number((avg + 5.1).toFixed(1)),
      min_temp: Number((avg - 4.8).toFixed(1)),
    };
  });
}

export function getSampleRainfallTrend(district?: string): RainfallData[] {
  const factor = district ? 0.65 + seededMetric(district, 29) * 0.8 : 1;
  const months = [
    { date: "2025-01-01", mm: 18 },
    { date: "2025-02-01", mm: 14 },
    { date: "2025-03-01", mm: 22 },
    { date: "2025-04-01", mm: 42 },
    { date: "2025-05-01", mm: 68 },
    { date: "2025-06-01", mm: 54 },
    { date: "2025-07-01", mm: 76 },
    { date: "2025-08-01", mm: 94 },
    { date: "2025-09-01", mm: 112 },
    { date: "2025-10-01", mm: 196 },
    { date: "2025-11-01", mm: 228 },
    { date: "2025-12-01", mm: 98 },
  ];

  let cumulative = 0;
  return months.map((m) => {
    const rainfall_mm = Number((m.mm * factor).toFixed(1));
    cumulative = Number((cumulative + rainfall_mm).toFixed(1));
    const category =
      rainfall_mm >= 150
        ? "Heavy"
        : rainfall_mm >= 65
          ? "Moderate"
          : "Light";
    return {
      date: m.date,
      district: district || "Tamil Nadu Avg",
      rainfall_mm,
      cumulative_mm: cumulative,
      category,
    };
  });
}

export function getSampleHumidityTrend(): HumidityData[] {
  const dates = [
    "2025-01-01",
    "2025-02-01",
    "2025-03-01",
    "2025-04-01",
    "2025-05-01",
    "2025-06-01",
    "2025-07-01",
    "2025-08-01",
    "2025-09-01",
    "2025-10-01",
    "2025-11-01",
    "2025-12-01",
  ];
  const values = [72, 66, 61, 58, 55, 62, 67, 70, 74, 81, 84, 78];
  return dates.map((date, idx) => ({
    date,
    humidity_pct: values[idx],
  }));
}

export function getSampleOverview(): WeatherOverview {
  const districts = getSampleDistrictWeather();
  const avgTemp = Number(
    (
      districts.reduce((acc, d) => acc + d.avg_temp, 0) / districts.length
    ).toFixed(1)
  );
  const maxTemp = Math.max(...districts.map((d) => d.max_temp));
  const minTemp = Math.min(...districts.map((d) => d.min_temp));
  const totalRainfall = Number(
    districts.reduce((acc, d) => acc + d.total_rainfall, 0).toFixed(1)
  );
  const avgHumidity = Number(
    (
      districts.reduce((acc, d) => acc + d.avg_humidity, 0) / districts.length
    ).toFixed(1)
  );

  return {
    districts_covered: 38,
    avg_temperature: avgTemp,
    max_temperature: maxTemp,
    min_temperature: minTemp,
    total_rainfall: totalRainfall,
    avg_humidity: avgHumidity,
    active_alerts: 2,
    temperature_trend: getSampleTemperatureTrend(),
    rainfall_trend: getSampleRainfallTrend(),
    humidity_trend: getSampleHumidityTrend(),
    district_comparison: districts.slice(0, 10),
  };
}

export function getSampleCurrentWeather(): CurrentWeather[] {
  const now = new Date().toISOString();
  return TAMIL_NADU_DISTRICTS.map((district, index) => {
    const r = seededMetric(district, 53);
    const r2 = seededMetric(district, 79);
    const isHilly = district === "Nilgiris";
    const temp = isHilly
      ? Number((16.5 + r * 4.5).toFixed(1))
      : Number((27.0 + r * 8.5).toFixed(1));
    return {
      district,
      temperature: temp,
      feels_like: Number((temp + 1.8 + r2 * 1.4).toFixed(1)),
      humidity: Math.round(isHilly ? 78 + r * 14 : 55 + r * 30),
      wind_speed: Number((8 + r2 * 16).toFixed(1)),
      wind_direction: DIRECTIONS[index % DIRECTIONS.length],
      pressure: Math.round(1008 + r * 9),
      condition: CONDITIONS[Math.floor(r2 * CONDITIONS.length) % CONDITIONS.length],
      last_updated: now,
    };
  });
}

export function getSampleAirQuality(): AirQuality[] {
  const now = new Date().toISOString();
  return TAMIL_NADU_DISTRICTS.map((district) => {
    const r = seededMetric(district, 91);
    const r2 = seededMetric(district, 103);
    const isMetro = ["Chennai", "Coimbatore", "Tiruchirappalli", "Madurai", "Salem", "Tiruppur"].includes(
      district
    );
    const aqi = Math.round(isMetro ? 65 + r * 75 : 28 + r * 58);
    const category =
      aqi <= 50
        ? "Good"
        : aqi <= 100
          ? "Satisfactory"
          : aqi <= 200
            ? "Moderate"
            : "Poor";

    return {
      district,
      aqi,
      category,
      dominant_pollutant: aqi > 80 ? "PM2.5" : "PM10",
      pm25: Number((aqi * 0.42 + r2 * 5).toFixed(1)),
      pm10: Number((aqi * 0.78 + r * 9).toFixed(1)),
      co: Number((0.4 + r2 * 0.9).toFixed(2)),
      no2: Number((12 + r * 28).toFixed(1)),
      so2: Number((6 + r2 * 14).toFixed(1)),
      o3: Number((22 + r * 35).toFixed(1)),
      last_updated: now,
    };
  });
}
