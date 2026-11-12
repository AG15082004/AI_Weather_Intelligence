import { useMemo } from "react";
import { MapPin } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TAMIL_NADU_DISTRICTS } from "@/lib/districts";
import { cn } from "@/lib/utils";

export { TAMIL_NADU_DISTRICTS };

export interface DistrictFilterProps {
  value: string;
  onChange: (district: string) => void;
  includeAll?: boolean;
  allLabel?: string;
  placeholder?: string;
  className?: string;
}

export function DistrictFilter({
  value,
  onChange,
  includeAll = true,
  allLabel = "All Districts (38)",
  placeholder = "Select district",
  className,
}: DistrictFilterProps) {
  const items = useMemo(() => {
    const map: Record<string, string> = {};
    if (includeAll) {
      map.all = allLabel;
    }
    for (const district of TAMIL_NADU_DISTRICTS) {
      map[district] = district;
    }
    return map;
  }, [includeAll, allLabel]);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Select
        value={value}
        onValueChange={(next) => {
          if (next != null) onChange(next);
        }}
        items={items}
      >
        <SelectTrigger className="h-9 w-full min-w-[200px] bg-white sm:w-56">
          <MapPin className="size-4 shrink-0 text-blue-600" />
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent className="max-h-72">
          {includeAll && <SelectItem value="all">{allLabel}</SelectItem>}
          {TAMIL_NADU_DISTRICTS.map((district) => (
            <SelectItem key={district} value={district}>
              {district}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
