import { Database, RefreshCw, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface FabricStatusBannerProps {
  status?: string;
  isPreviewMode: boolean;
  onTogglePreview: () => void;
  onRefresh?: () => void;
}

export function FabricStatusBanner({
  status,
  isPreviewMode,
  onTogglePreview,
  onRefresh,
}: FabricStatusBannerProps) {
  const isPending =
    !status || status.toLowerCase().includes("pending");

  if (!isPending && !isPreviewMode) {
    return null;
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-blue-200/80 bg-blue-50/70 px-4 py-3 text-sm sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-2.5 sm:items-center">
        <Database className="mt-0.5 size-4 shrink-0 text-blue-600 sm:mt-0" />
        <div className="flex flex-wrap items-center gap-2">
          <Badge
            variant="secondary"
            className={
              isPreviewMode
                ? "bg-amber-100 text-amber-800"
                : "bg-blue-100 text-blue-800"
            }
          >
            {isPreviewMode ? "Sample Preview Active" : status || "Pending Fabric Connection"}
          </Badge>
          <span className="text-xs text-slate-600">
            {isPreviewMode
              ? "Displaying representative Tamil Nadu meteorological baseline across 38 districts."
              : "Backend API connected; awaiting live Microsoft Fabric Lakehouse queries."}
          </span>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {onRefresh && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="h-8 gap-1.5 bg-white text-xs"
          >
            <RefreshCw className="size-3.5" />
            Refresh
          </Button>
        )}
        <Button
          variant={isPreviewMode ? "outline" : "default"}
          size="sm"
          onClick={onTogglePreview}
          className="h-8 gap-1.5 text-xs"
        >
          <Sparkles className="size-3.5" />
          {isPreviewMode ? "Use Live API" : "Preview Sample Data"}
        </Button>
      </div>
    </div>
  );
}
