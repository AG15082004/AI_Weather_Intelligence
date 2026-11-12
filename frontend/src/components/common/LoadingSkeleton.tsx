import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export interface LoadingSkeletonProps {
  variant?: "cards" | "chart" | "table" | "page";
  count?: number;
}

export function LoadingSkeleton({
  variant = "page",
  count = 4,
}: LoadingSkeletonProps) {
  if (variant === "cards") {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: count }).map((_, idx) => (
          <Card key={idx} className="bg-white">
            <CardContent className="space-y-3 pt-1">
              <div className="flex items-center justify-between">
                <Skeleton className="h-3.5 w-24" />
                <Skeleton className="size-10 rounded-lg" />
              </div>
              <Skeleton className="h-7 w-20" />
              <Skeleton className="h-3 w-32" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (variant === "chart") {
    return (
      <Card className="bg-white">
        <CardHeader className="border-b border-slate-100 pb-4">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-3.5 w-72" />
        </CardHeader>
        <CardContent className="pt-4">
          <Skeleton className="h-72 w-full rounded-lg" />
        </CardContent>
      </Card>
    );
  }

  if (variant === "table") {
    return (
      <Card className="bg-white">
        <CardHeader className="border-b border-slate-100 pb-4">
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent className="space-y-2.5 pt-4">
          <Skeleton className="h-9 w-64" />
          {Array.from({ length: 6 }).map((_, idx) => (
            <Skeleton key={idx} className="h-10 w-full" />
          ))}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <LoadingSkeleton variant="cards" count={count} />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <LoadingSkeleton variant="chart" />
        <LoadingSkeleton variant="chart" />
      </div>
    </div>
  );
}
