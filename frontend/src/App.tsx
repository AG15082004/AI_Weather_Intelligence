import { Route, Routes } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppLayout } from "@/components/layout/AppLayout";
import { WeatherOverview } from "@/pages/WeatherOverview";
import { TemperatureAnalytics } from "@/pages/TemperatureAnalytics";
import { RainfallAnalytics } from "@/pages/RainfallAnalytics";
import { DistrictIntelligence } from "@/pages/DistrictIntelligence";
import { CurrentWeather } from "@/pages/CurrentWeather";
import { AirQuality } from "@/pages/AirQuality";
import { HistoricalAnalytics } from "@/pages/HistoricalAnalytics";
import { AIAssistant } from "@/pages/AIAssistant";
import { DashboardBuilder } from "@/pages/DashboardBuilder";

export function App() {
  return (
    <TooltipProvider>
      <AppLayout>
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
      </AppLayout>
    </TooltipProvider>
  );
}

export default App;
