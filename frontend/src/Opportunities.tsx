import { useEffect, useState } from 'react'
import { ArrowUpRight, Check, MapPin, Search } from 'lucide-react'
import { api, Job, parseError } from './api'
import { EmptyState, ErrorState, Loading } from './Shared'

function JobCard({ job, onNotice }: { job: Job; onNotice: (m: string) => void }) {
  const [state, setState] = useState<'idle' | 'busy' | 'applied' | 'duplicate'>('idle')
  const [appId, setAppId] = useState('')

  const apply = async () => {
    setState('busy')
    try {
      const result = await api.apply(job.id)
      setAppId(result.applicationId)
      setState('applied')
    } catch (err) {
      const msg = parseError(err)
      // 409 duplicate — treat as success-like state
      if (msg.toLowerCase().includes('already applied')) {
        setState('duplicate')
      } else {
        setState('idle')
        onNotice(msg)
      }
    }
  }

  return (
    <article className="job-card">
      <div className="job-card-top">
        <div className="company-logo">{job.company.charAt(0)}</div>
        <span className="pill">{job.type}</span>
      </div>
      <h3>{job.title}</h3>
      <p className="company-name">
        {job.company}
        <span>·</span>
        <MapPin size={11} style={{ display: 'inline', marginLeft: 4, marginRight: 2 }} />
        {job.location}
      </p>
      <p className="job-description">{job.description}</p>
      {state === 'applied' && appId && (
        <p style={{ fontSize: 11, color: 'var(--green)', marginBottom: 6 }}>
          Application ID: {appId}
        </p>
      )}
      <div className="job-footer">
        <strong>{job.salary}</strong>
        {state === 'applied' ? (
          <button className="success-button" disabled>
            <Check size={15} /> Applied
          </button>
        ) : state === 'duplicate' ? (
          <button className="success-button" disabled>
            <Check size={15} /> Already applied
          </button>
        ) : (
          <button className="primary-button" onClick={apply} disabled={state === 'busy'}>
            {state === 'busy' ? 'Applying…' : <><ArrowUpRight size={15} /> Apply now</>}
          </button>
        )}
      </div>
    </article>
  )
}

export default function Opportunities() {
  const [jobs,     setJobs]     = useState<Job[]>([])
  const [filtered, setFiltered] = useState<Job[]>([])
  const [query,    setQuery]    = useState('')
  const [notice,   setNotice]   = useState('')
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState('')

  const load = () => {
    setLoading(true)
    setError('')
    api.jobs()
       .then(r => { setJobs(r.jobs); setFiltered(r.jobs) })
       .catch(err => setError(parseError(err)))
       .finally(() => setLoading(false))
  }

  useEffect(load, [])

  const search = (q: string) => {
    setQuery(q)
    const lower = q.toLowerCase()
    setFiltered(
      jobs.filter(j =>
        j.title.toLowerCase().includes(lower) ||
        j.company.toLowerCase().includes(lower) ||
        j.location.toLowerCase().includes(lower) ||
        j.description.toLowerCase().includes(lower),
      ),
    )
  }

  return (
    <div className="opportunities">
      <div className="toolbar">
        <div className="search-box">
          <Search size={17} />
          <input
            placeholder="Search roles, companies, skills…"
            value={query}
            onChange={e => search(e.target.value)}
            aria-label="Search jobs"
          />
        </div>
      </div>

      {notice && <ErrorState message={notice} onRetry={() => setNotice('')} />}

      {loading ? (
        <Loading message="Fetching open roles…" />
      ) : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : filtered.length === 0 ? (
        <EmptyState message={query ? `No roles match "${query}".` : 'No open roles at the moment.'} />
      ) : (
        <div className="job-grid">
          {filtered.map(job => (
            <JobCard job={job} key={job.id} onNotice={setNotice} />
          ))}
        </div>
      )}
    </div>
  )
}
