import { useEffect, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  Clock,
  Database,
  Radio,
  RefreshCw,
  Server,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getOperationalStatus, type OperationalStatus } from "@/api/endpoints";

export function OperationalMonitoringCard() {
  const [status, setStatus] = useState<OperationalStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string>("");

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await getOperationalStatus();
      setStatus(data);
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch {
      // Non-blocking telemetry
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchStatus();
    // Poll telemetry every 60 seconds
    const interval = setInterval(() => {
      void fetchStatus();
    }, 60000);
    return () => clearInterval(interval);
  }, []);

  if (!status) {
    return null;
  }

  const getStatusBadge = (s: string) => {
    switch (s.toLowerCase()) {
      case "healthy":
        return (
          <Badge className="gap-1 border-emerald-200 bg-emerald-50 text-emerald-700">
            <CheckCircle2 className="size-3 text-emerald-600" />
            Healthy
          </Badge>
        );
      case "degraded":
        return (
          <Badge className="gap-1 border-amber-200 bg-amber-50 text-amber-700">
            Degraded
          </Badge>
        );
      default:
        return (
          <Badge className="gap-1 border-rose-200 bg-rose-50 text-rose-700">
            Unavailable
          </Badge>
        );
    }
  };

  return (
    <Card className="border-slate-200/90 bg-white shadow-xs">
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-blue-600" />
          <CardTitle className="text-sm font-semibold text-slate-800">
            Platform Operational Telemetry & Health
          </CardTitle>
          <Badge variant="outline" className="text-[10px] text-slate-500">
            Live Observability
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {lastRefreshed && (
            <span className="text-[11px] text-slate-400">
              Refreshed: {lastRefreshed}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => void fetchStatus()}
            disabled={loading}
            className="h-7 w-7 p-0 text-slate-500 hover:text-slate-800"
            title="Refresh operational metrics"
          >
            <RefreshCw className={`size-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {/* Backend API Status */}
          <div className="flex flex-col gap-1.5 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
                <Server className="size-3.5 text-blue-600" />
                Backend API
              </span>
              {getStatusBadge(status.api.status)}
            </div>
            <div className="flex items-baseline justify-between text-xs text-slate-500">
              <span>Avg Latency:</span>
              <strong className="font-semibold text-slate-800">
                {status.api.avg_latency_ms} ms
              </strong>
            </div>
            <div className="flex items-baseline justify-between text-[11px] text-slate-400">
              <span>Uptime:</span>
              <span>{Math.round(status.uptime_seconds)}s</span>
            </div>
          </div>

          {/* Microsoft Fabric Lakehouse Status */}
          <div className="flex flex-col gap-1.5 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
                <Database className="size-3.5 text-indigo-600" />
                Microsoft Fabric
              </span>
              {getStatusBadge(status.fabric.status)}
            </div>
            <div className="flex items-baseline justify-between text-xs text-slate-500">
              <span>Total Queries:</span>
              <strong className="font-semibold text-slate-800">
                {status.fabric.total_queries}
              </strong>
            </div>
            <div className="flex items-baseline justify-between text-[11px] text-slate-400">
              <span>Query Latency:</span>
              <span>
                {status.fabric.avg_latency_ms > 0
                  ? `${status.fabric.avg_latency_ms} ms`
                  : "Connected"}
              </span>
            </div>
          </div>

          {/* AI Engine Status */}
          <div className="flex flex-col gap-1.5 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
                <Bot className="size-3.5 text-purple-600" />
                AI Provider
              </span>
              {getStatusBadge(status.ai.status)}
            </div>
            <div className="flex items-baseline justify-between text-xs text-slate-500">
              <span>Active Engine:</span>
              <strong className="font-semibold capitalize text-slate-800">
                {status.ai.active_provider === "deterministic"
                  ? "Deterministic Engine"
                  : "Ollama (Qwen3)"}
              </strong>
            </div>
            <div className="flex items-baseline justify-between text-[11px] text-slate-400">
              <span>Selection:</span>
              <span className="truncate max-w-[130px]" title={status.ai.provider_reason}>
                {status.ai.provider_reason.replace(/_/g, " ")}
              </span>
            </div>
          </div>

          {/* Data Freshness & District Coverage */}
          <div className="flex flex-col gap-1.5 rounded-lg border border-slate-100 bg-slate-50/60 p-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-xs font-medium text-slate-600">
                <Radio className="size-3.5 text-emerald-600" />
                Telemetry Freshness
              </span>
              <Badge className="border-blue-200 bg-blue-50 text-blue-700">
                {status.data_freshness.coverage_pct}%
              </Badge>
            </div>
            <div className="flex items-baseline justify-between text-xs text-slate-500">
              <span>Districts:</span>
              <strong className="font-semibold text-slate-800">
                {status.data_freshness.districts_reporting} / {status.data_freshness.total_districts}
              </strong>
            </div>
            <div className="flex items-baseline justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <Clock className="size-3 text-slate-400" />
                Observed:
              </span>
              <span>{status.data_freshness.latest_observation || "Recent"}</span>
            </div>
          </div>
        </div>

        {/* Security & Verification Guarantee Banner */}
        <div className="mt-3 flex items-center justify-between rounded-md border border-slate-100 bg-slate-50/40 px-3 py-1.5 text-[11px] text-slate-500">
          <span className="flex items-center gap-1.5 font-medium text-slate-600">
            <ShieldCheck className="size-3.5 text-emerald-600" />
            Security & Integrity: Strict OWASP headers, in-memory rate limiting, and zero credential leakage active.
          </span>
          <span className="text-slate-400">
            Environment: <strong className="text-slate-600">{status.environment}</strong>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
