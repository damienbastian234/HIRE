import { FormEvent, useEffect, useState } from 'react'
import { Check } from 'lucide-react'
import { api, parseError, Profile, User } from './api'
import { ErrorState, Loading } from './Shared'

interface ProfileViewProps {
  user: User
  onUpdate: (user: User) => void
}

export default function ProfileView({ user, onUpdate }: ProfileViewProps) {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [saved,   setSaved]   = useState(false)
  const [error,   setError]   = useState('')
  const [loadErr, setLoadErr] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.profile()
       .then(p => { setProfile(p); setLoading(false) })
       .catch(err => { setLoadErr(parseError(err)); setLoading(false) })
  }, [])

  const save = async (e: FormEvent) => {
    e.preventDefault()
    if (!profile) return
    setError('')
    try {
      const response = await api.updateProfile(profile)
      setProfile(response.profile)
      onUpdate({ ...user, ...response.profile })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(parseError(err))
    }
  }

  if (loading)  return <Loading message="Loading your profile…" />
  if (loadErr)  return <ErrorState message={loadErr} />
  if (!profile) return <ErrorState message="Profile data is unavailable." />

  return (
    <div className="profile-layout">
      {/* Left sidebar */}
      <section className="profile-intro">
        <div className="large-avatar">{profile.name.charAt(0)}</div>
        <h3>{profile.name}</h3>
        <p>{profile.title}</p>
        <span><span className="status-dot" /> Profile active</span>
        <div className="profile-role-badge">
          {profile.role === 'recruiter' ? 'Recruiter' : 'Candidate'}
        </div>
      </section>

      {/* Edit form */}
      <form className="panel profile-form" onSubmit={save}>
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PUBLIC PROFILE</p>
            <h3>Make it unmistakably you</h3>
          </div>
          {saved && (
            <span className="saved"><Check size={15} /> Saved</span>
          )}
        </div>

        <div className="form-grid">
          <label>
            Full name
            <input value={profile.name} onChange={e => setProfile({ ...profile, name: e.target.value })} />
          </label>
          <label>
            Professional title
            <input value={profile.title} onChange={e => setProfile({ ...profile, title: e.target.value })} />
          </label>
          <label>
            Email address
            <input type="email" value={profile.email} onChange={e => setProfile({ ...profile, email: e.target.value })} />
          </label>
          <label>
            Location
            <input value={profile.location} onChange={e => setProfile({ ...profile, location: e.target.value })} />
          </label>
        </div>

        <div style={{ marginTop: 22 }}>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 8 }}>Account type</p>
          <div className="role-toggle" style={{ maxWidth: 280 }}>
            {(['candidate', 'recruiter'] as const).map(r => (
              <button
                key={r}
                type="button"
                className={profile.role === r ? 'selected' : ''}
                onClick={() => setProfile({ ...profile, role: r })}
              >
                {r.charAt(0).toUpperCase() + r.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="error-text" style={{ marginTop: 16 }}>{error}</p>}

        <div className="form-footer">
          <span style={{ fontSize: 11, color: 'var(--muted)' }}>Changes sync with your H.I.R.E. profile</span>
          <button className="primary-button" type="submit">
            Save changes <Check size={16} />
          </button>
        </div>
      </form>
    </div>
  )
}
