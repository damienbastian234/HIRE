import { useEffect, useRef, useState } from 'react'
import { RefreshCw, X } from 'lucide-react'
import { api } from './api'

// ─── Loading ──────────────────────────────────────────────────────────────────
export function Loading({ message = 'Loading…' }: { message?: string }) {
  return (
    <div className="loading">
      <span className="spinner" aria-hidden="true" />
      {message}
    </div>
  )
}

// ─── ErrorState ───────────────────────────────────────────────────────────────
export function ErrorState({
  message,
  onRetry,
}: {
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="error-state" role="alert">
      <X size={19} />
      <div>
        <strong>Something went wrong</strong>
        <p>{message}</p>
        {onRetry && (
          <button className="retry-btn" onClick={onRetry}>
            <RefreshCw size={13} /> Try again
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Pill ─────────────────────────────────────────────────────────────────────
export function Pill({
  children,
  variant = 'default',
}: {
  children: React.ReactNode
  variant?: 'default' | 'green' | 'amber' | 'red'
}) {
  return (
    <span className={`pill${variant !== 'default' ? ` ${variant}` : ''}`}>
      {children}
    </span>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
export function EmptyState({ message }: { message: string }) {
  return <p className="empty-state">{message}</p>
}

// ─── HealthBadge ──────────────────────────────────────────────────────────────
type HealthStatus = 'checking' | 'connected' | 'unavailable'

export function HealthBadge() {
  const [status, setStatus] = useState<HealthStatus>('checking')
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const check = () => {
    setStatus('checking')
    api
      .health()
      .then(() => setStatus('connected'))
      .catch(() => {
        setStatus('unavailable')
        // auto-retry in 10 s
        retryRef.current = setTimeout(check, 10_000)
      })
  }

  useEffect(() => {
    check()
    return () => {
      if (retryRef.current) clearTimeout(retryRef.current)
    }
  }, [])

  const labels: Record<HealthStatus, string> = {
    checking:    'Checking API…',
    connected:   'API connected',
    unavailable: 'API unavailable',
  }
  const dotClass: Record<HealthStatus, string> = {
    checking:    'status-dot checking',
    connected:   'status-dot',
    unavailable: 'status-dot red',
  }

  return (
    <span
      className={`health-badge ${status}`}
      title={status === 'unavailable' ? 'Click to retry' : undefined}
      onClick={status === 'unavailable' ? check : undefined}
      style={status === 'unavailable' ? { cursor: 'pointer' } : undefined}
    >
      <span className={dotClass[status]} />
      {labels[status]}
    </span>
  )
}
