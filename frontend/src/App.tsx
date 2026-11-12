import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLayout } from "@/components/layout/AppLayout";
import { LoadingSkeleton } from "@/components/common/LoadingSkeleton";
import { ErrorBoundary } from "@/components/common/ErrorBoundary";

// Route-level lazy loading for performance and bundle splitting
const WeatherOverview = lazy(() =>
  import("@/pages/WeatherOverview").then((m) => ({ default: m.WeatherOverview }))
);
const TemperatureAnalytics = lazy(() =>
  import("@/pages/TemperatureAnalytics").then((m) => ({
    default: m.TemperatureAnalytics,
  }))
);
const RainfallAnalytics = lazy(() =>
  import("@/pages/RainfallAnalytics").then((m) => ({
    default: m.RainfallAnalytics,
  }))
);
const DistrictIntelligence = lazy(() =>
  import("@/pages/DistrictIntelligence").then((m) => ({
    default: m.DistrictIntelligence,
  }))
);
const CurrentWeather = lazy(() =>
  import("@/pages/CurrentWeather").then((m) => ({
    default: m.CurrentWeather,
  }))
);
const AirQuality = lazy(() =>
  import("@/pages/AirQuality").then((m) => ({ default: m.AirQuality }))
);
const HistoricalAnalytics = lazy(() =>
  import("@/pages/HistoricalAnalytics").then((m) => ({
    default: m.HistoricalAnalytics,
  }))
);
const AIAssistant = lazy(() =>
  import("@/pages/AIAssistant").then((m) => ({ default: m.AIAssistant }))
);
const DashboardBuilder = lazy(() =>
  import("@/pages/DashboardBuilder").then((m) => ({
    default: m.DashboardBuilder,
  }))
);

export function App() {
  return (
    <TooltipProvider>
      <ErrorBoundary>
        <AppLayout>
          <Suspense fallback={<LoadingSkeleton variant="page" count={6} />}>
            <Routes>
              <Route path="/" element={<WeatherOverview />} />
              <Route path="/temperature" element={<TemperatureAnalytics />} />
              <Route path="/rainfall" element={<RainfallAnalytics />} />
              <Route path="/districts" element={<DistrictIntelligence />} />
              <Route path="/current-weather" element={<CurrentWeather />} />
              <Route path="/air-quality" element={<AirQuality />} />
              <Route path="/historical" element={<HistoricalAnalytics />} />
              <Route path="/ai-assistant" element={<AIAssistant />} />
              <Route path="/dashboard-builder" element={<DashboardBuilder />} />
            </Routes>
          </Suspense>
        </AppLayout>
      </ErrorBoundary>
    </TooltipProvider>
  );
}

export default App;
