/**
 * Error Boundary Component
 * 
 * Catches JavaScript errors in child component tree and displays a fallback UI.
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { logger } from '../../utils/logger';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.componentError('ErrorBoundary', error, errorInfo);
    this.setState({ errorInfo });
  }

  handleReload = () => {
    window.location.reload();
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
        <div className="min-h-screen bg-black text-white flex items-center justify-center p-6">
          <div className="max-w-md w-full text-center space-y-6">
            {/* Error Icon */}
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                <AlertTriangle size={40} className="text-red-500" />
              </div>
            </div>

            {/* Error Title */}
            <div className="space-y-2">
              <h1 className="text-2xl font-display font-bold text-white">
                SYSTEM_ERROR
              </h1>
              <p className="text-sm font-mono text-red-400">
                CRITICAL_FAULT_DETECTED
              </p>
            </div>

            {/* Error Message */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <p className="text-sm text-gray-400 font-mono">
                {this.state.error?.message || 'An unexpected error occurred'}
              </p>
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <button
                onClick={this.handleReload}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-pandora-cyan text-black font-bold text-sm uppercase tracking-wider hover:bg-white transition-colors"
              >
                <RefreshCw size={16} />
                Reload System
              </button>
              <button
                onClick={this.handleReset}
                className="flex items-center justify-center gap-2 px-6 py-3 bg-white/5 border border-white/10 text-gray-400 font-bold text-sm uppercase tracking-wider hover:bg-white/10 transition-colors"
              >
                Try Again
              </button>
            </div>

            {/* Debug Info (Development Only) */}
            {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
              <details className="text-left bg-black/50 border border-white/10 rounded-lg p-4 mt-6">
                <summary className="text-xs font-mono text-gray-500 cursor-pointer">
                  Stack Trace
                </summary>
                <pre className="mt-2 text-[10px] font-mono text-gray-600 overflow-auto max-h-40">
                  {this.state.errorInfo.componentStack}
                </pre>
              </details>
            )}

            {/* Footer */}
            <div className="pt-6 border-t border-white/5">
              <p className="text-[10px] font-mono text-gray-600">
                ERROR_CODE: {this.state.error?.name || 'UNKNOWN'} | PVNDORA_V2.0
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
