import { useEffect, useState } from 'react'
import {
  Activity, BriefcaseBusiness, ChevronRight, LayoutDashboard,
  LogOut, Menu, Settings2, Sparkles, UserRound, Users,
} from 'lucide-react'
import { api, authStore, parseError, Role, User } from './api'
import AuthScreen from './Auth'
import Overview from './Overview'
import Opportunities from './Opportunities'
import Intelligence from './Intelligence'
import ProfileView from './Profile'
import SettingsView from './Settings'
import Candidates from './Candidates'
import { HealthBadge, Loading } from './Shared'

export type View = 'overview' | 'opportunities' | 'intelligence' | 'profile' | 'settings' | 'candidates'

const CANDIDATE_NAV = [
  { id: 'overview'      as View, icon: LayoutDashboard,  label: 'Overview' },
  { id: 'opportunities' as View, icon: BriefcaseBusiness, label: 'Opportunities' },
  { id: 'intelligence'  as View, icon: Sparkles,          label: 'Resume intelligence' },
  { id: 'profile'       as View, icon: UserRound,         label: 'Profile' },
]

const RECRUITER_NAV = [
  { id: 'overview'    as View, icon: LayoutDashboard, label: 'Overview' },
  { id: 'candidates'  as View, icon: Users,           label: 'Candidates' },
  { id: 'intelligence'as View, icon: Sparkles,        label: 'Resume intelligence' },
  { id: 'profile'     as View, icon: UserRound,       label: 'Profile' },
]

const VIEW_TITLE: Record<View, string> = {
  overview:      'Overview',
  opportunities: 'Opportunities',
  intelligence:  'Resume intelligence',
  profile:       'Profile',
  settings:      'Settings',
  candidates:    'Candidates',
}

const VIEW_HEADING: Record<View, (name: string) => React.ReactNode> = {
  overview:      name => <><em>{name.split(' ')[0]}</em>, good morning.</>,
  opportunities: ()   => 'Find your next move',
  intelligence:  ()   => 'See what your resume says',
  profile:       ()   => 'Your professional profile',
  settings:      ()   => 'Workspace settings',
  candidates:    ()   => 'Candidate pipeline',
}

const VIEW_SUB: Record<View, string> = {
  overview:      'A clear view of your momentum, applications, and next best actions.',
  opportunities: 'Roles chosen to match your strengths and trajectory.',
  intelligence:  'Turn your experience into an advantage with structured career insight.',
  profile:       'Keep your details current so the right opportunities can find you.',
  settings:      'Control how H.I.R.E. feels and keeps you informed.',
  candidates:    'Review and advance candidates through your hiring pipeline.',
}

// ─── App component ────────────────────────────────────────────────────────────
export default function App() {
  // 'checking' = validating saved token via /auth/me
  // 'authed'   = logged in
  // 'anon'     = not logged in
  const [authState, setAuthState] = useState<'checking' | 'authed' | 'anon'>('checking')
  const [user, setUser]           = useState<User | null>(null)
  const [view, setView]           = useState<View>('overview')
  const [mobileOpen, setMobileOpen] = useState(false)

  // ── Session restoration ────────────────────────────────────────────────────
  useEffect(() => {
    if (!authStore.isLoggedIn()) {
      setAuthState('anon')
      return
    }
    api.me()
      .then(me => {
        authStore.setUser(me)
        setUser(me)
        setAuthState('authed')
      })
      .catch(() => {
        // Token invalid / expired — clear and redirect to login
        authStore.clearAuth()
        setAuthState('anon')
      })
  }, [])

  // ── Compact mode ───────────────────────────────────────────────────────────
  useEffect(() => {
    const compact = localStorage.getItem('hire-compact-mode') === 'true'
    document.body.setAttribute('data-compact', String(compact))
  }, [])

  const login = (next: User) => {
    setUser(next)
    setAuthState('authed')
  }

  const logout = () => {
    authStore.clearAuth()
    setUser(null)
    setAuthState('anon')
    setView('overview')
  }

  const nav = (next: View) => {
    setView(next)
    setMobileOpen(false)
  }

  // ── Render states ──────────────────────────────────────────────────────────
  if (authState === 'checking') {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <Loading message="Restoring your session…" />
      </div>
    )
  }
  if (authState === 'anon' || !user) return <AuthScreen onAuth={login} />

  const role: Role = user.role
  const navItems   = role === 'recruiter' ? RECRUITER_NAV : CANDIDATE_NAV
  const today      = new Date().toLocaleDateString('en-US', { month: 'long', day: '2-digit', year: 'numeric' })

  return (
    <div className="app-shell" id="app-shell">
      {/* Mobile overlay */}
      {mobileOpen && <div className="sidebar-overlay" onClick={() => setMobileOpen(false)} />}

      {/* Sidebar */}
      <aside className={mobileOpen ? 'sidebar open' : 'sidebar'}>
        <div className="brand">
          <span className="brand-mark">H</span>
          <span>H.I.R.E.</span>
        </div>
        <div className="workspace-label">
          {role === 'recruiter' ? 'RECRUITER WORKSPACE' : 'CANDIDATE WORKSPACE'}
        </div>

        <nav>
          {navItems.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              id={`nav-${id}`}
              className={view === id ? 'nav-item active' : 'nav-item'}
              onClick={() => nav(id)}
            >
              <Icon size={17} />
              {label}
              <ChevronRight size={14} className="nav-arrow" />
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button
            id="nav-settings"
            className={view === 'settings' ? 'nav-item active' : 'nav-item'}
            onClick={() => nav('settings')}
          >
            <Settings2 size={17} /> Settings
            <ChevronRight size={14} className="nav-arrow" />
          </button>
          <button className="nav-item" onClick={logout} id="nav-logout">
            <LogOut size={17} /> Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="main-content">
        {/* Topbar */}
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setMobileOpen(!mobileOpen)} id="menu-toggle">
            <Menu size={20} />
          </button>
          <div className="breadcrumb">
            Workspace <span>/</span> {VIEW_TITLE[view]}
          </div>
          <div className="topbar-actions">
            <HealthBadge />
            <div className="avatar" title={user.name}>{user.name.charAt(0)}</div>
          </div>
        </header>

        {/* Page content */}
        <div className="page">
          <div className="page-heading">
            <div>
              <p className="eyebrow">{role === 'recruiter' ? 'RECRUITER' : 'CANDIDATE'} WORKSPACE</p>
              <h1>{VIEW_HEADING[view](user.name)}</h1>
              <p className="subheading">{VIEW_SUB[view]}</p>
            </div>
            <div className="date-chip">
              <Activity size={15} /> {today}
            </div>
          </div>

          {view === 'overview'      && <Overview role={role} onNavigate={nav} />}
          {view === 'opportunities' && <Opportunities />}
          {view === 'intelligence'  && <Intelligence />}
          {view === 'candidates'    && <Candidates />}
          {view === 'profile'       && (
            <ProfileView
              user={user}
              onUpdate={next => {
                setUser(next)
                authStore.setUser(next)
              }}
            />
          )}
          {view === 'settings' && <SettingsView />}
        </div>
      </main>
    </div>
  )
}