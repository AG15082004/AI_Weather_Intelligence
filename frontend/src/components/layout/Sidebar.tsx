import { NavLink } from "react-router-dom";
import {
  CloudSun,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { NAV_ITEMS } from "@/lib/navigation";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface SidebarProps {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onNavigate?: () => void;
  className?: string;
}

export function Sidebar({
  collapsed,
  onToggleCollapse,
  onNavigate,
  className,
}: SidebarProps) {
  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r border-slate-200 bg-white shadow-sm transition-all duration-200",
        collapsed ? "w-[72px]" : "w-64",
        className
      )}
    >
      {/* Brand header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-200 px-3">
        <div
          className={cn(
            "flex items-center gap-2.5 overflow-hidden",
            collapsed && "justify-center"
          )}
        >
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white shadow-xs">
            <CloudSun className="size-5" />
          </div>
          {!collapsed && (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold tracking-tight text-slate-900">
                TN Weather
              </p>
              <p className="truncate text-[11px] font-medium text-blue-600">
                Intelligence
              </p>
            </div>
          )}
        </div>

        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onToggleCollapse}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="hidden shrink-0 text-slate-500 hover:text-slate-900 lg:inline-flex"
        >
          {collapsed ? (
            <PanelLeftOpen className="size-4" />
          ) : (
            <PanelLeftClose className="size-4" />
          )}
        </Button>
      </div>

      {/* Navigation links */}
      <nav
        aria-label="Primary Navigation"
        className="flex-1 space-y-1 overflow-y-auto px-2.5 py-4"
      >
        {!collapsed && (
          <p className="mb-2 px-2.5 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Analytics & Tools
          </p>
        )}

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const linkEl = (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group flex items-center gap-3 rounded-lg px-2.5 py-2.5 text-sm font-medium transition-colors",
                  collapsed && "justify-center px-2",
                  isActive
                    ? "bg-blue-50 text-blue-600 shadow-2xs ring-1 ring-blue-100"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                )
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    className={cn(
                      "size-4.5 shrink-0 transition-colors",
                      isActive
                        ? "text-blue-600"
                        : "text-slate-400 group-hover:text-slate-700"
                    )}
                  />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </>
              )}
            </NavLink>
          );

          if (collapsed) {
            return (
              <Tooltip key={item.path}>
                <TooltipTrigger
                  render={<div className="w-full" />}
                >
                  {linkEl}
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p className="font-medium">{item.label}</p>
                </TooltipContent>
              </Tooltip>
            );
          }

          return linkEl;
        })}
      </nav>

      {/* Footer status */}
      <div className="border-t border-slate-200 p-3">
        {collapsed ? (
          <div
            className="mx-auto flex size-8 items-center justify-center rounded-md bg-slate-100 text-[11px] font-semibold text-slate-600"
            title="38 Tamil Nadu Districts"
          >
            38
          </div>
        ) : (
          <div className="rounded-lg bg-slate-50 px-3 py-2.5 ring-1 ring-slate-200/80">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-700">
                Tamil Nadu Grid
              </span>
              <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                38 Districts
              </span>
            </div>
            <p className="mt-0.5 text-[11px] text-slate-500">
              Fabric + Qwen3 Analytics
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
