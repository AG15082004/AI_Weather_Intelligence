import { AlertCircle, RefreshCw, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  onUseSample?: () => void;
}

export function ErrorState({
  title = "Unable to load weather data",
  message,
  onRetry,
  onUseSample,
}: ErrorStateProps) {
  return (
    <Card className="border-rose-200 bg-white shadow-xs">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <div className="flex size-12 items-center justify-center rounded-full bg-rose-50 text-rose-600">
          <AlertCircle className="size-6" />
        </div>
        <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
        <p className="mt-1.5 max-w-md text-sm text-slate-500">{message}</p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          {onRetry && (
            <Button onClick={onRetry} className="gap-1.5">
              <RefreshCw className="size-4" />
              Retry Connection
            </Button>
          )}
          {onUseSample && (
            <Button
              variant="outline"
              onClick={onUseSample}
              className="gap-1.5"
            >
              <Sparkles className="size-4 text-blue-600" />
              Preview Sample TN Data
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
