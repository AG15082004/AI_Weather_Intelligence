import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an unhandled error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-[350px] flex-col items-center justify-center rounded-xl border border-rose-200 bg-rose-50/50 p-6 text-center">
          <div className="mb-3 flex size-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
            <AlertTriangle className="size-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">
            Operational View Encountered an Error
          </h3>
          <p className="mt-1 max-w-md text-xs text-slate-600">
            {this.state.error?.message ||
              "An unexpected error occurred while rendering this weather component. Your state has been protected."}
          </p>
          <Button
            onClick={this.handleReset}
            variant="default"
            size="sm"
            className="mt-4 gap-1.5 bg-blue-600 hover:bg-blue-700"
          >
            <RefreshCw className="size-3.5" />
            Reload Component
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
