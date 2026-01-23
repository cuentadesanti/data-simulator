import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
    children: ReactNode;
    /** Optional: Custom fallback UI to display when an error occurs */
    fallback?: ReactNode;
    /** Optional: Name of the boundary for logging purposes */
    name?: string;
    /** Optional: Callback when an error is caught */
    onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorId: string | null;
}

/**
 * ErrorBoundary - Catches JavaScript errors in child component tree
 * and displays a fallback UI instead of crashing the entire application.
 * 
 * Usage:
 * <ErrorBoundary name="ComponentName">
 *   <YourComponent />
 * </ErrorBoundary>
 */
class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorId: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        // Generate a unique error ID for tracking
        const errorId = `err_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        return {
            hasError: true,
            error,
            errorId,
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        const { name = 'Unknown', onError } = this.props;

        // Log error details for debugging
        console.error(`[ErrorBoundary:${name}] Caught error:`, error);
        console.error(`[ErrorBoundary:${name}] Component stack:`, errorInfo.componentStack);

        // Call optional error callback (useful for error reporting services)
        if (onError) {
            onError(error, errorInfo);
        }

        // TODO: Send to error reporting service (e.g., Sentry, LogRocket)
        // reportError({ error, errorInfo, boundaryName: name, errorId: this.state.errorId });
    }

    handleRetry = (): void => {
        this.setState({
            hasError: false,
            error: null,
            errorId: null,
        });
    };

    handleReload = (): void => {
        window.location.reload();
    };

    render(): ReactNode {
        const { hasError, error, errorId } = this.state;
        const { children, fallback, name } = this.props;

        if (hasError) {
            // If custom fallback is provided, use it
            if (fallback) {
                return fallback;
            }

            // Default fallback UI
            return (
                <div className="flex items-center justify-center min-h-[200px] p-6 bg-red-50 rounded-lg border border-red-200">
                    <div className="text-center max-w-md">
                        <div className="mb-4">
                            <svg
                                className="mx-auto h-12 w-12 text-red-500"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                aria-hidden="true"
                            >
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                                />
                            </svg>
                        </div>
                        <h3 className="text-lg font-semibold text-red-800 mb-2">
                            Something went wrong
                        </h3>
                        <p className="text-sm text-red-600 mb-4">
                            {name
                                ? `An error occurred in the ${name} component.`
                                : 'An unexpected error occurred.'
                            }
                        </p>
                        {import.meta.env.DEV && error && (
                            <details className="text-left mb-4 p-3 bg-red-100 rounded text-xs">
                                <summary className="cursor-pointer font-medium text-red-700 mb-2">
                                    Error Details
                                </summary>
                                <pre className="whitespace-pre-wrap break-words text-red-600 overflow-auto max-h-32">
                                    {error.message}
                                    {error.stack && `\n\n${error.stack}`}
                                </pre>
                            </details>
                        )}
                        {errorId && (
                            <p className="text-xs text-red-400 mb-4">
                                Error ID: {errorId}
                            </p>
                        )}
                        <div className="flex gap-3 justify-center">
                            <button
                                onClick={this.handleRetry}
                                className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={this.handleReload}
                                className="px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-300 rounded-md hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors"
                            >
                                Reload Page
                            </button>
                        </div>
                    </div>
                </div>
            );
        }

        return children;
    }
}

/**
 * AppErrorBoundary - Top-level error boundary for the entire application.
 * Shows a full-page error message when the app crashes.
 */
class AppErrorBoundary extends Component<
    { children: ReactNode; onError?: (error: Error, errorInfo: ErrorInfo) => void },
    State
> {
    constructor(props: { children: ReactNode; onError?: (error: Error, errorInfo: ErrorInfo) => void }) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorId: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        const errorId = `app_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        return {
            hasError: true,
            error,
            errorId,
        };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
        console.error('[AppErrorBoundary] Critical error:', error);
        console.error('[AppErrorBoundary] Component stack:', errorInfo.componentStack);

        if (this.props.onError) {
            this.props.onError(error, errorInfo);
        }
    }

    handleReload = (): void => {
        window.location.reload();
    };

    handleGoHome = (): void => {
        window.location.href = '/';
    };

    render(): ReactNode {
        const { hasError, error, errorId } = this.state;
        const { children } = this.props;

        if (hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-gray-800 p-4">
                    <div className="max-w-lg w-full bg-white rounded-xl shadow-2xl p-8">
                        <div className="text-center">
                            <div className="mb-6">
                                <svg
                                    className="mx-auto h-16 w-16 text-red-500"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    aria-hidden="true"
                                >
                                    <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        strokeWidth={1.5}
                                        d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                                    />
                                </svg>
                            </div>
                            <h1 className="text-2xl font-bold text-gray-900 mb-2">
                                Application Error
                            </h1>
                            <p className="text-gray-600 mb-6">
                                We're sorry, but something went wrong. Please try reloading the page or contact support if the problem persists.
                            </p>

                            {import.meta.env.DEV && error && (
                                <details className="text-left mb-6 p-4 bg-gray-100 rounded-lg text-sm">
                                    <summary className="cursor-pointer font-medium text-gray-700 mb-2">
                                        Developer Details
                                    </summary>
                                    <pre className="whitespace-pre-wrap break-words text-red-600 overflow-auto max-h-48 text-xs font-mono">
                                        {error.message}
                                        {error.stack && `\n\n${error.stack}`}
                                    </pre>
                                </details>
                            )}

                            {errorId && (
                                <p className="text-xs text-gray-400 mb-6">
                                    Reference: {errorId}
                                </p>
                            )}

                            <div className="flex flex-col sm:flex-row gap-3 justify-center">
                                <button
                                    onClick={this.handleReload}
                                    className="px-6 py-3 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
                                >
                                    Reload Application
                                </button>
                                <button
                                    onClick={this.handleGoHome}
                                    className="px-6 py-3 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors"
                                >
                                    Go to Home
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            );
        }

        return children;
    }
}

export { ErrorBoundary, AppErrorBoundary };
export default ErrorBoundary;
