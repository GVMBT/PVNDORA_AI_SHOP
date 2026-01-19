/**
 * Error Boundary Component
 *
 * Catches JavaScript errors in child component tree and displays a fallback UI.
 * Automatically handles chunk load errors by refreshing the page.
 */

import { AlertTriangle, RefreshCw } from "lucide-react";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { logger } from "../../utils/logger";
import { sessionStorage } from "../../utils/storage";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  isChunkError: boolean;
}

// Check if error is a chunk loading error (stale cache after deploy)
function isChunkLoadError(error: Error | null): boolean {
  if (!error) {
    return false;
  }
  const message = error.message.toLowerCase();
  return (
    message.includes("failed to fetch dynamically imported module") ||
    message.includes("loading chunk") ||
    message.includes("loading css chunk") ||
    message.includes("dynamically imported module")
  );
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, isChunkError: false };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const isChunk = isChunkLoadError(error);
    return { hasError: true, error, isChunkError: isChunk };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.componentError("ErrorBoundary", error, errorInfo);
    this.setState({ errorInfo });

    // Auto-reload on chunk errors (stale cache)
    if (isChunkLoadError(error)) {
      const reloadCount = Number.parseInt(sessionStorage.get("pvndora_chunk_reload") || "0", 10);
      if (reloadCount < 2) {
        sessionStorage.set("pvndora_chunk_reload", String(reloadCount + 1));
        globalThis.location.reload();
      }
    }
  }

  handleReload = () => {
    globalThis.location.reload();
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="flex min-h-screen items-center justify-center bg-black p-6 text-white">
          <div className="w-full max-w-md space-y-6 text-center">
            {/* Error Icon */}
            <div className="flex justify-center">
              <div className="flex h-20 w-20 items-center justify-center rounded-full border border-red-500/30 bg-red-500/10">
                <AlertTriangle className="text-red-500" size={40} />
              </div>
            </div>

            {/* Error Title */}
            <div className="space-y-2">
              <h1 className="font-bold font-display text-2xl text-white">SYSTEM_ERROR</h1>
              <p className="font-mono text-red-400 text-sm">CRITICAL_FAULT_DETECTED</p>
            </div>

            {/* Error Message */}
            <div className="rounded-lg border border-white/10 bg-white/5 p-4">
              <p className="font-mono text-gray-400 text-sm">
                {this.state.error?.message || "An unexpected error occurred"}
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col justify-center gap-3 sm:flex-row">
              <button
                className="flex items-center justify-center gap-2 bg-pandora-cyan px-6 py-3 font-bold text-black text-sm uppercase tracking-wider transition-colors hover:bg-white"
                onClick={this.handleReload}
                type="button"
              >
                <RefreshCw size={16} />
                Reload System
              </button>
              <button
                className="flex items-center justify-center gap-2 border border-white/10 bg-white/5 px-6 py-3 font-bold text-gray-400 text-sm uppercase tracking-wider transition-colors hover:bg-white/10"
                onClick={this.handleReset}
                type="button"
              >
                Try Again
              </button>
            </div>

            {/* Debug Info (Development Only) */}
            {process.env.NODE_ENV === "development" && this.state.errorInfo && (
              <details className="mt-6 rounded-lg border border-white/10 bg-black/50 p-4 text-left">
                <summary className="cursor-pointer font-mono text-gray-500 text-xs">
                  Stack Trace
                </summary>
                <pre className="mt-2 max-h-40 overflow-auto font-mono text-[10px] text-gray-600">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            {/* Footer */}
            <div className="border-white/5 border-t pt-6">
              <p className="font-mono text-[10px] text-gray-600">
                ERROR_CODE: {this.state.error?.name || "UNKNOWN"} | PVNDORA_V2.0
              </p>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
