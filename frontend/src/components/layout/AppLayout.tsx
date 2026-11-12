import { useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-slate-50 text-slate-900">
      {/* Desktop sidebar */}
      <div className="hidden h-full lg:block">
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed((prev) => !prev)}
        />
      </div>

      {/* Mobile sidebar drawer */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <SheetTitle className="sr-only">
            TN Weather Intelligence Navigation
          </SheetTitle>
          <Sidebar
            collapsed={false}
            onToggleCollapse={() => {}}
            onNavigate={() => setMobileMenuOpen(false)}
            className="w-full border-r-0 shadow-none"
          />
        </SheetContent>
      </Sheet>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Header onOpenMobileMenu={() => setMobileMenuOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl space-y-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
