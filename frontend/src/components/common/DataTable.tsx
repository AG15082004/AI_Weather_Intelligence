import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface DataTableColumn<T> {
  key: keyof T & string;
  header: string;
  sortable?: boolean;
  align?: "left" | "right" | "center";
  render?: (value: T[keyof T], row: T) => ReactNode;
  className?: string;
}

export interface DataTableProps<T extends object> {
  data: T[];
  columns: DataTableColumn<T>[];
  searchable?: boolean;
  searchPlaceholder?: string;
  searchKeys?: Array<keyof T & string>;
  emptyMessage?: string;
  maxHeightClassName?: string;
  onRowClick?: (row: T) => void;
}

export function DataTable<T extends object>({
  data,
  columns,
  searchable = true,
  searchPlaceholder = "Filter rows...",
  searchKeys,
  emptyMessage = "No matching records found.",
  maxHeightClassName = "max-h-[420px]",
  onRowClick,
}: DataTableProps<T>) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<(keyof T & string) | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

  const handleSort = (key: keyof T & string) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const processedRows = useMemo(() => {
    const trimmed = query.trim().toLowerCase();
    const keysToSearch =
      searchKeys ?? columns.map((c) => c.key);

    let filtered = data;
    if (trimmed) {
      filtered = data.filter((row) =>
        keysToSearch.some((key) => {
          const val = row[key];
          return val != null && String(val).toLowerCase().includes(trimmed);
        })
      );
    }

    if (!sortKey) return filtered;

    return [...filtered].sort((a, b) => {
      const valA = a[sortKey];
      const valB = b[sortKey];

      if (valA == null && valB == null) return 0;
      if (valA == null) return 1;
      if (valB == null) return -1;

      if (typeof valA === "number" && typeof valB === "number") {
        return sortDir === "asc" ? valA - valB : valB - valA;
      }

      const strA = String(valA).toLowerCase();
      const strB = String(valB).toLowerCase();
      const cmp = strA.localeCompare(strB);
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [data, query, searchKeys, columns, sortKey, sortDir]);

  return (
    <div className="space-y-3">
      {searchable && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-xs">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-slate-400" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={searchPlaceholder}
              className="bg-white pl-8"
            />
          </div>
          <p className="text-xs text-slate-500">
            Showing {processedRows.length} of {data.length} records
          </p>
        </div>
      )}

      <div
        className={cn(
          "overflow-auto rounded-lg border border-slate-200 bg-white",
          maxHeightClassName
        )}
      >
        <table className="w-full border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 border-b border-slate-200 bg-slate-50/95 text-xs font-semibold tracking-wide text-slate-600 uppercase backdrop-blur-xs">
            <tr>
              {columns.map((col) => {
                const isSorted = sortKey === col.key;
                const sortable = col.sortable !== false;
                return (
                  <th
                    key={col.key}
                    className={cn(
                      "px-4 py-3 whitespace-nowrap select-none",
                      col.align === "right" && "text-right",
                      col.align === "center" && "text-center",
                      sortable && "cursor-pointer hover:text-slate-900",
                      col.className
                    )}
                    onClick={sortable ? () => handleSort(col.key) : undefined}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.header}
                      {sortable &&
                        (isSorted ? (
                          sortDir === "asc" ? (
                            <ArrowUp className="size-3.5 text-blue-600" />
                          ) : (
                            <ArrowDown className="size-3.5 text-blue-600" />
                          )
                        ) : (
                          <ArrowUpDown className="size-3 text-slate-400" />
                        ))}
                    </span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {processedRows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-sm text-slate-500"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              processedRows.map((row, rowIndex) => (
                <tr
                  key={rowIndex}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                  className={cn(
                    "transition-colors hover:bg-slate-50",
                    onRowClick && "cursor-pointer"
                  )}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={cn(
                        "px-4 py-2.5 text-slate-700",
                        col.align === "right" && "text-right tabular-nums",
                        col.align === "center" && "text-center",
                        col.className
                      )}
                    >
                      {col.render
                        ? col.render(row[col.key], row)
                        : row[col.key] != null
                          ? String(row[col.key])
                          : "—"}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
