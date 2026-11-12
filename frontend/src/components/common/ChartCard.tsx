import type { ReactNode } from "react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";

export interface ChartCardProps {
  title: string;
  subtitle?: string;
  filters?: ReactNode;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
}

export function ChartCard({
  title,
  subtitle,
  filters,
  children,
  className,
  contentClassName,
}: ChartCardProps) {
  return (
    <Card className={cn("bg-white shadow-xs", className)}>
      <CardHeader className="border-b border-slate-100 pb-4">
        <div>
          <CardTitle className="text-base font-semibold text-slate-900">
            {title}
          </CardTitle>
          {subtitle && (
            <CardDescription className="mt-0.5 text-xs text-slate-500">
              {subtitle}
            </CardDescription>
          )}
        </div>
        {filters && (
          <CardAction className="flex flex-wrap items-center gap-2">
            {filters}
          </CardAction>
        )}
      </CardHeader>
      <CardContent className={cn("pt-2", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  );
}
