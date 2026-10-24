import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="p-8 text-center">
            <h2 className="text-lg font-semibold text-destructive">Something went wrong</h2>
            <p className="text-sm text-muted-foreground mt-2">{this.state.error?.message}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-4 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm"
            >
              Reload page
            </button>
          </div>
        )
      )
    }
    return this.props.children
  }
}
