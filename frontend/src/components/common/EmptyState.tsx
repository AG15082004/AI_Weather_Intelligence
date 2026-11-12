import type { LucideIcon } from "lucide-react";
import { Database, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface EmptyStateProps {
  icon?: LucideIcon;
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon: Icon = Database,
  title = "No weather records available",
  message = "No observations matched your current filters or Fabric Lakehouse sync is pending.",
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <Card className="border-dashed border-slate-300 bg-white shadow-none">
      <CardContent className="flex flex-col items-center justify-center py-12 text-center">
        <div className="flex size-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
          <Icon className="size-6" />
        </div>
        <h3 className="mt-4 text-base font-semibold text-slate-900">{title}</h3>
        <p className="mt-1.5 max-w-md text-sm text-slate-500">{message}</p>
        {actionLabel && onAction && (
          <Button
            variant="outline"
            onClick={onAction}
            className="mt-5 gap-1.5"
          >
            <Sparkles className="size-4 text-blue-600" />
            {actionLabel}
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
