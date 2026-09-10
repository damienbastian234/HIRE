import { FormEvent, useState } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { api, authStore, parseError, Role, User } from './api'

interface AuthScreenProps {
  onAuth: (user: User) => void
}

export default function AuthScreen({ onAuth }: AuthScreenProps) {
  const [register, setRegister] = useState(false)
  const [role, setRole]         = useState<Role>('candidate')
  const [name, setName]         = useState('')
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [busy, setBusy]         = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = register
        ? await api.register({ name, email, password, role })
        : await api.login({ email, password })
      // Persist token and user — single source of truth
      authStore.setToken(result.token)
      authStore.setUser(result.user)
      onAuth(result.user)
    } catch (err) {
      setError(parseError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-art">
        <div className="brand light">
          <span className="brand-mark">H</span>
          <span>H.I.R.E.</span>
        </div>
        <div className="art-copy">
          <p className="eyebrow">CAREER INTELLIGENCE, HUMANIZED</p>
          <h1>Your next chapter is closer than you think.</h1>
          <p>Make your potential legible. H.I.R.E. turns the signal in your experience into a path forward.</p>
        </div>
        <div className="art-footer">
          01 <span /> Built for people with somewhere to go
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-form">
          <p className="eyebrow">WELCOME</p>
          <h2>{register ? 'Create your workspace' : 'Pick up where you left off'}</h2>
          <p className="muted">
            {register
              ? 'Start building a clearer picture of your career.'
              : 'Sign in to continue your career intelligence journey.'}
          </p>

          <form onSubmit={submit}>
            {register && (
              <label>
                Full name
                <input
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="e.g. Alex Morgan"
                  required
                />
              </label>
            )}
            <label>
              Email address
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </label>

            {register && (
              <div>
                <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>I am joining as a</p>
                <div className="role-toggle">
                  <button type="button" className={role === 'candidate' ? 'selected' : ''} onClick={() => setRole('candidate')}>
                    Candidate
                  </button>
                  <button type="button" className={role === 'recruiter' ? 'selected' : ''} onClick={() => setRole('recruiter')}>
                    Recruiter
                  </button>
                </div>
              </div>
            )}

            {error && <p className="error-text" role="alert">{error}</p>}

            <button className="primary-button full" disabled={busy} type="submit">
              {busy ? 'Connecting…' : register ? 'Create account' : 'Enter workspace'}
              {!busy && <ArrowUpRight size={17} />}
            </button>
          </form>

          <p className="switch-auth">
            {register ? 'Already have an account?' : 'New to H.I.R.E.?'}{' '}
            <button type="button" onClick={() => { setRegister(!register); setError('') }}>
              {register ? 'Sign in' : 'Create an account'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
