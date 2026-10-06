import { useEffect, useState } from 'react'
import { ArrowUpRight, ChevronRight, Sparkles } from 'lucide-react'
import { api, Application, CandidateDashboard, parseError, RecruiterDashboard, Role } from './api'
import { EmptyState, ErrorState, Loading } from './Shared'
import type { View } from './App'

interface OverviewProps {
  role: Role
  onNavigate: (view: View) => void
}

function ApplicationRow({ app }: { app: Application }) {
  const [jobTitle, setJobTitle] = useState(app.jobTitle ?? '')
  const [company,  setCompany]  = useState(app.company ?? '')

  // Load real job title if not embedded in the application object
  useEffect(() => {
    if (!jobTitle && app.jobId) {
      api.job(app.jobId)
        .then(r => { setJobTitle(r.job.title); setCompany(r.job.company) })
        .catch(() => { setJobTitle(app.jobId); setCompany('') })
    }
  }, [app.jobId, jobTitle])

  const isInterview = app.status.toLowerCase().includes('interview')

  return (
    <div className="application-row">
      <div className="job-logo">{(jobTitle || app.jobId).charAt(0).toUpperCase()}</div>
      <div>
        <strong>{jobTitle || app.jobId}</strong>
        <span>{company}</span>
      </div>
      <div className="application-status">
        <span className={isInterview ? 'pill green' : 'pill'}>{app.status}</span>
        <small>{app.updatedAt}</small>
      </div>
    </div>
  )
}

export default function Overview({ role, onNavigate }: OverviewProps) {
  const [data,  setData]  = useState<CandidateDashboard | RecruiterDashboard | null>(null)
  const [error, setError] = useState('')

  const load = () => {
    setError('')
    setData(null)
    api.dashboard(role)
       .then(setData)
       .catch(err => setError(parseError(err)))
  }

  useEffect(() => { load() }, [role])

  if (error) return <ErrorState message={error} onRetry={load} />
  if (!data)  return <Loading />

  const recruiter = role === 'recruiter'
  const stats     = data.stats

  return (
    <>
      {/* Stat grid */}
      <div className="stat-grid">
        {stats.map((stat, i) => (
          <div className={i === 0 ? 'stat-card highlighted' : 'stat-card'} key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            <small>{i === 0 ? '↑ Updated now' : i === 1 ? 'Keep the momentum going' : 'Across your workspace'}</small>
          </div>
        ))}
      </div>

      {/* Content grid */}
      <div className="content-grid">
        <section className="panel focus-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">{recruiter ? 'TALENT PIPELINE' : 'YOUR MOMENTUM'}</p>
              <h3>{recruiter ? 'Candidates in motion' : 'Applications in motion'}</h3>
            </div>
            <button
              className="text-button"
              onClick={() => onNavigate(recruiter ? 'candidates' : 'opportunities')}
            >
              View all <ArrowUpRight size={15} />
            </button>
          </div>

          {recruiter ? (
            <div className="candidate-list">
              {(data as RecruiterDashboard).candidates.length === 0 ? (
                <EmptyState message="No candidates in the pipeline yet." />
              ) : (
                (data as RecruiterDashboard).candidates.map(c => (
                  <div className="candidate-row" key={c.name}>
                    <div className="avatar soft">
                      {c.name.split(' ').map(x => x[0]).join('')}
                    </div>
                    <div>
                      <strong>{c.name}</strong>
                      <span>{c.stage}</span>
                    </div>
                    <div className="match-score">
                      {c.skillMatch}% <small>match</small>
                    </div>
                  </div>
                ))
              )}
            </div>
          ) : (
            <div className="application-list">
              {(data as CandidateDashboard).applications.length === 0 ? (
                <EmptyState message="No applications yet. Browse opportunities to apply." />
              ) : (
                (data as CandidateDashboard).applications.map(app => (
                  <ApplicationRow key={app.id} app={app} />
                ))
              )}
            </div>
          )}
        </section>

        <section className="panel next-panel">
          <p className="eyebrow">NEXT BEST ACTION</p>
          <div className="action-icon">
            <Sparkles size={20} />
          </div>
          <h3>{recruiter ? 'Review your top matches' : 'Strengthen your profile'}</h3>
          <p>
            {recruiter
              ? 'Candidates are ready for your review based on current role requirements.'
              : 'Upload your resume or run a resume analysis to improve your profile match.'}
          </p>
          <button
            className="primary-button"
            onClick={() => onNavigate(recruiter ? 'candidates' : 'intelligence')}
          >
            {recruiter ? 'View candidates' : 'Analyze my resume'} <ArrowUpRight size={16} />
          </button>
        </section>
      </div>

      <section className="quote-strip">
        <div className="quote-mark">"</div>
        <p>
          Clarity is not a destination.
          <br />
          <strong>It is a competitive advantage.</strong>
        </p>
        <span>H.I.R.E. intelligence note</span>
      </section>
    </>
  )
}
