import { Link, useLocation } from "react-router-dom";
import { ChevronRight, CloudSun, Menu } from "lucide-react";
import { NAV_ITEMS } from "@/lib/navigation";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  onOpenMobileMenu: () => void;
}

export function Header({ onOpenMobileMenu }: HeaderProps) {
  const location = useLocation();
  const currentRoute =
    NAV_ITEMS.find((item) => item.path === location.pathname) || NAV_ITEMS[0];

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur-xs md:px-6">
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="icon-sm"
          onClick={onOpenMobileMenu}
          aria-label="Open navigation menu"
          className="lg:hidden"
        >
          <Menu className="size-4" />
        </Button>

        <div className="flex flex-col">
          {/* Breadcrumbs */}
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <Link
              to="/"
              className="flex items-center gap-1 font-medium hover:text-blue-600"
            >
              <CloudSun className="size-3.5 text-blue-600" />
              <span>TN Weather Intelligence</span>
            </Link>
            <ChevronRight className="size-3 text-slate-400" />
            <span className="font-medium text-slate-700">
              {currentRoute.shortLabel}
            </span>
          </div>

          {/* Dynamic page title */}
          <h1 className="text-base font-semibold tracking-tight text-slate-900 md:text-lg">
            {currentRoute.label}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        <p className="hidden text-xs text-slate-500 md:block">
          {currentRoute.description}
        </p>
        <Badge
          variant="secondary"
          className="border border-blue-100 bg-blue-50 text-blue-700"
        >
          Tamil Nadu · 38 Districts
        </Badge>
      </div>
    </header>
  );
}
