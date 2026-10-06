import { useEffect, useState } from 'react'
import { Info } from 'lucide-react'
import { api, parseError } from './api'
import { ErrorState, Loading } from './Shared'

export default function Candidates() {
  const [candidates, setCandidates] = useState<
    { name: string; stage: string; skillMatch: number; email: string }[]
  >([])
  const [note,    setNote]    = useState('')
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    api.recruiterCandidates()
       .then(r => { setCandidates(r.candidates); setNote(r.note) })
       .catch(err => setError(parseError(err)))
       .finally(() => setLoading(false))
  }

  useEffect(load, [])

  if (loading) return <Loading message="Loading candidates…" />
  if (error)   return <ErrorState message={error} onRetry={load} />

  const stageColor: Record<string, string> = {
    Interview:  'pill green',
    Screening:  'pill amber',
    Applied:    'pill',
  }

  return (
    <div className="candidates-layout">
      {/* Phase 2 banner */}
      {note && (
        <div className="recruiter-preview-banner">
          <Info size={15} />
          <span>{note}</span>
        </div>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">CANDIDATE PIPELINE</p>
            <h3>Active candidates</h3>
          </div>
          <span className="pill green">{candidates.length} candidates</span>
        </div>

        <div className="candidate-table">
          <div className="candidate-table-header">
            <span>Candidate</span>
            <span>Stage</span>
            <span>Skill match</span>
            <span>Contact</span>
          </div>
          {candidates.map(c => (
            <div className="candidate-table-row" key={c.email}>
              <div className="candidate-name-cell">
                <div className="avatar soft">
                  {c.name.split(' ').map(x => x[0]).join('')}
                </div>
                <strong>{c.name}</strong>
              </div>
              <span>
                <span className={stageColor[c.stage] ?? 'pill'}>{c.stage}</span>
              </span>
              <div className="match-bar-cell">
                <div className="score-bar-track">
                  <div
                    className="score-bar-fill"
                    style={{ width: `${Math.min(100, Math.max(0, c.skillMatch))}%` }}
                  />
                </div>
                <span>{c.skillMatch}%</span>
              </div>
              <a href={`mailto:${c.email}`} className="email-link">{c.email}</a>
            </div>
          ))}
        </div>
      </section>

      <section className="panel roadmap-panel">
        <p className="eyebrow">ROADMAP — PHASE 2</p>
        <h3>Full recruiter portal is coming</h3>
        <p>
          The following features are planned for Phase 2 and are not yet available:
        </p>
        <ul className="roadmap-list">
          <li>Candidate search and filtering</li>
          <li>Stage advancement and pipeline management</li>
          <li>Resume and analysis review per candidate</li>
          <li>Interview scheduling and feedback</li>
          <li>Company and role management</li>
          <li>University analytics dashboard</li>
        </ul>
      </section>
    </div>
  )
}
