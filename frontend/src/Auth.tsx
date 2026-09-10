import { FormEvent, useState } from 'react'
import { ArrowUpRight, ArrowLeft } from 'lucide-react'
import { api, authStore, parseError, Role, User } from './api'

interface AuthScreenProps {
  onAuth: (user: User) => void
}

type AuthStep = 'login' | 'register' | 'forgot-email' | 'forgot-reset' | 'forgot-done'

export default function AuthScreen({ onAuth }: AuthScreenProps) {
  const [step, setStep]           = useState<AuthStep>('login')
  const [role, setRole]           = useState<Role>('candidate')
  const [name, setName]           = useState('')
  const [email, setEmail]         = useState('')
  const [password, setPassword]   = useState('')
  const [newPassword, setNew]     = useState('')
  const [confirmPw, setConfirm]   = useState('')
  const [error, setError]         = useState('')
  const [busy, setBusy]           = useState(false)

  const reset = (next: AuthStep) => {
    setError('')
    setPassword('')
    setNew('')
    setConfirm('')
    setStep(next)
  }

  // ── Login / Register ───────────────────────────────────────────────────────
  const submitAuth = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = step === 'register'
        ? await api.register({ name, email, password, role })
        : await api.login({ email, password })
      authStore.setToken(result.token)
      authStore.setUser(result.user)
      onAuth(result.user)
    } catch (err) {
      setError(parseError(err))
    } finally {
      setBusy(false)
    }
  }

  // ── Forgot — step 1: collect email ────────────────────────────────────────
  const submitForgotEmail = (e: FormEvent) => {
    e.preventDefault()
    if (!email.trim()) { setError('Please enter your email address.'); return }
    setError('')
    setStep('forgot-reset')
  }

  // ── Forgot — step 2: set new password ─────────────────────────────────────
  const submitForgotReset = async (e: FormEvent) => {
    e.preventDefault()
    if (newPassword !== confirmPw) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    setError('')
    try {
      await api.resetPassword({ email, new_password: newPassword })
      setStep('forgot-done')
    } catch (err) {
      setError(parseError(err))
    } finally {
      setBusy(false)
    }
  }

  // ── Panel content by step ─────────────────────────────────────────────────
  const panel = () => {
    // ── Forgot done ──────────────────────────────────────────────────────────
    if (step === 'forgot-done') return (
      <div className="auth-form">
        <p className="eyebrow">PASSWORD RESET</p>
        <h2>All set!</h2>
        <p className="muted">
          If an account exists for <strong>{email}</strong>, your password has been updated.
          You can now sign in with your new password.
        </p>
        <button
          className="primary-button full"
          style={{ marginTop: 24 }}
          onClick={() => reset('login')}
        >
          Back to sign in <ArrowUpRight size={17} />
        </button>
      </div>
    )

    // ── Forgot reset: enter new password ────────────────────────────────────
    if (step === 'forgot-reset') return (
      <div className="auth-form">
        <button
          type="button"
          className="back-link"
          onClick={() => reset('forgot-email')}
        >
          <ArrowLeft size={15} /> Back
        </button>
        <p className="eyebrow">PASSWORD RESET</p>
        <h2>Set a new password</h2>
        <p className="muted">Choose a new password for <strong>{email}</strong>.</p>

        <form onSubmit={submitForgotReset}>
          <label>
            New password
            <input
              type="password"
              value={newPassword}
              onChange={e => setNew(e.target.value)}
              placeholder="At least 8 characters"
              minLength={8}
              required
            />
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              value={confirmPw}
              onChange={e => setConfirm(e.target.value)}
              placeholder="••••••••"
              required
            />
          </label>

          {error && <p className="error-text" role="alert">{error}</p>}

          <button className="primary-button full" disabled={busy} type="submit">
            {busy ? 'Saving…' : 'Reset password'}
            {!busy && <ArrowUpRight size={17} />}
          </button>
        </form>
      </div>
    )

    // ── Forgot email: enter email ────────────────────────────────────────────
    if (step === 'forgot-email') return (
      <div className="auth-form">
        <button
          type="button"
          className="back-link"
          onClick={() => reset('login')}
        >
          <ArrowLeft size={15} /> Back to sign in
        </button>
        <p className="eyebrow">PASSWORD RESET</p>
        <h2>Forgot your password?</h2>
        <p className="muted">
          Enter the email address linked to your account and we'll walk you through resetting it.
        </p>

        <form onSubmit={submitForgotEmail}>
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

          {error && <p className="error-text" role="alert">{error}</p>}

          <button className="primary-button full" type="submit">
            Continue <ArrowUpRight size={17} />
          </button>
        </form>
      </div>
    )

    // ── Login / Register ─────────────────────────────────────────────────────
    const isRegister = step === 'register'
    return (
      <div className="auth-form">
        <p className="eyebrow">WELCOME</p>
        <h2>{isRegister ? 'Create your workspace' : 'Pick up where you left off'}</h2>
        <p className="muted">
          {isRegister
            ? 'Start building a clearer picture of your career.'
            : 'Sign in to continue your career intelligence journey.'}
        </p>

        <form onSubmit={submitAuth}>
          {isRegister && (
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

          {/* Forgot password link — only on login */}
          {!isRegister && (
            <div className="forgot-row">
              <button
                type="button"
                className="forgot-link"
                onClick={() => { setError(''); setStep('forgot-email') }}
              >
                Forgot password?
              </button>
            </div>
          )}

          {isRegister && (
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
            {busy ? 'Connecting…' : isRegister ? 'Create account' : 'Enter workspace'}
            {!busy && <ArrowUpRight size={17} />}
          </button>
        </form>

        <p className="switch-auth">
          {isRegister ? 'Already have an account?' : 'New to H.I.R.E.?'}{' '}
          <button type="button" onClick={() => reset(isRegister ? 'login' : 'register')}>
            {isRegister ? 'Sign in' : 'Create an account'}
          </button>
        </p>
      </div>
    )
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
        {panel()}
      </div>
    </div>
  )
}
