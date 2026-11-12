import {
  Bot,
  CalendarDays,
  CloudRain,
  LayoutDashboard,
  MapPin,
  Sun,
  Thermometer,
  Wand2,
  Wind,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  path: string;
  label: string;
  shortLabel: string;
  icon: LucideIcon;
  description: string;
}

export const NAV_ITEMS: NavItem[] = [
  {
    path: "/",
    label: "Weather Overview",
    shortLabel: "Overview",
    icon: LayoutDashboard,
    description: "State-wide summary across 38 districts",
  },
  {
    path: "/temperature",
    label: "Temperature Analytics",
    shortLabel: "Temperature",
    icon: Thermometer,
    description: "Daily trends, monthly averages & distribution",
  },
  {
    path: "/rainfall",
    label: "Rainfall Analytics",
    shortLabel: "Rainfall",
    icon: CloudRain,
    description: "Precipitation levels & monsoon indicators",
  },
  {
    path: "/districts",
    label: "District Intelligence",
    shortLabel: "Districts",
    icon: MapPin,
    description: "Explore all 38 Tamil Nadu districts",
  },
  {
    path: "/current-weather",
    label: "Current Weather",
    shortLabel: "Live Weather",
    icon: Sun,
    description: "Latest conditions, wind & pressure",
  },
  {
    path: "/air-quality",
    label: "Air Quality",
    shortLabel: "Air Quality",
    icon: Wind,
    description: "AQI, PM2.5, PM10 & pollutant index",
  },
  {
    path: "/historical",
    label: "Historical Analytics",
    shortLabel: "Historical",
    icon: CalendarDays,
    description: "Multi-month Open-Meteo & historical trends",
  },
  {
    path: "/ai-assistant",
    label: "AI Assistant",
    shortLabel: "AI Chat",
    icon: Bot,
    description: "Natural-language weather insights",
  },
  {
    path: "/dashboard-builder",
    label: "Dashboard Builder",
    shortLabel: "Builder",
    icon: Wand2,
    description: "Generate custom weather dashboards",
  },
];
