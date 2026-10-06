import { useState } from 'react'
import {
  Award, BookOpen, Briefcase, Check, ChevronRight, Globe,
  Mail, MapPin, Phone, TrendingUp, User, X, Zap,
} from 'lucide-react'
import { Analysis } from './api'
import { EmptyState } from './Shared'

type Tab = 'overview' | 'profile' | 'skills' | 'experience' | 'match'

interface AnalysisResultProps {
  result: Analysis
  jobTitle?: string
  jobCompany?: string
}


// ─── Helpers ──────────────────────────────────────────────────────────────────
const clamp = (v: number) => Math.min(100, Math.max(0, v))

function monthsToYears(months: number): string {
  const y = Math.floor(months / 12)
  const m = months % 12
  if (y === 0) return `${m}mo`
  if (m === 0) return `${y}yr`
  return `${y}yr ${m}mo`
}

function seniorityColor(level: string): string {
  const map: Record<string, string> = {
    Entry: '#a0b4f0', Junior: '#74c7b4', Mid: '#c8e46a',
    Senior: '#f0b864', Principal: '#e07090',
  }
  return map[level] ?? '#b0b8c0'
}

function ScoreBar({ label, value, color = 'var(--green)' }: { label: string; value: number; color?: string }) {
  const pct = clamp(Math.round(value))
  return (
    <div className="score-bar-row">
      <div className="score-bar-label"><span>{label}</span><strong>{pct}%</strong></div>
      <div className="score-bar-track">
        <div className="score-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

function MeetsBadge({ meets }: { meets: boolean }) {
  return (
    <span className={`meets-badge ${meets ? 'yes' : 'no'}`}>
      {meets ? <Check size={11} /> : <X size={11} />}
      {meets ? 'Meets requirement' : 'Below requirement'}
    </span>
  )
}

// ─── Tab: Overview ────────────────────────────────────────────────────────────
function TabOverview({
  result, jobTitle, jobCompany,
}: { result: Analysis; jobTitle?: string; jobCompany?: string }) {
  const { overall_score, recommendation, confidence, skill_match } = result.candidate_matching
  const score = clamp(Math.round(overall_score.overall_score))
  const recColor: Record<string, string> = {
    'Strong Match': '#2d6a57', 'Good Match': '#4a8c72',
    'Possible Match': '#b07e30', 'Weak Match': '#c05840', 'Not Recommended': '#8b2020',
  }
  return (
    <div className="tab-overview">

      {/* ── Recommended job title header ── */}
      {jobTitle && (
        <div className="analyzed-job-banner">
          <div className="analyzed-job-label">RECOMMENDED JOB MATCH</div>
          <div className="analyzed-job-title">{jobTitle}</div>
          {jobCompany && <div className="analyzed-job-company">at {jobCompany}</div>}
        </div>
      )}

      <div className="score-panel">
        <div>
          <p className="eyebrow">OVERALL MATCH</p>
          <h2>{score}<small>/100</small></h2>
          <span className="recommendation-badge" style={{ background: recColor[recommendation] ?? 'var(--green)' }}>
            {recommendation}
          </span>
        </div>
        <div className="score-ring" style={{ '--score': `${score * 3.6}deg` } as React.CSSProperties}>
          <span>{score}%</span>
        </div>
      </div>

      <div className="result-grid">
        <div className="mini-result">
          <span>Skills detected</span>
          <strong>{result.skill_intelligence.metrics.total_skills}</strong>
          <small>{result.skill_intelligence.metrics.technical_skill_count} technical</small>
        </div>
        <div className="mini-result">
          <span>Experience</span>
          <strong>{result.experience_intelligence.metrics.total_experience_years}y</strong>
          <small>{result.experience_intelligence.seniority_level} level</small>
        </div>
        <div className="mini-result">
          <span>Confidence</span>
          <strong>{clamp(Math.round(confidence))}%</strong>
          <small>Analysis confidence</small>
        </div>
      </div>
      <div className="panel score-breakdown">
        <p className="eyebrow" style={{ marginBottom: 18 }}>SCORE BREAKDOWN</p>
        <ScoreBar label="Skills"     value={overall_score.skill_score}      />
        <ScoreBar label="Experience" value={overall_score.experience_score} color="#4a8c72" />
        <ScoreBar label="Education"  value={overall_score.education_score}  color="#8abba5" />
      </div>
      <div className="panel result-detail">
        <div className="panel-heading">
          <h3>Skill snapshot</h3>
          <span className="pill green">{skill_match.matched_required_skills.length} required matched</span>
        </div>
        {skill_match.matched_required_skills.length > 0 ? (
          <div className="tag-list">
            {skill_match.matched_required_skills.map(s => <span key={s}><Check size={12} />{s}</span>)}
          </div>
        ) : <EmptyState message="No required skills matched." />}
        {skill_match.missing_required_skills.length > 0 && (
          <>
            <h4 style={{ marginTop: 20 }}>Worth developing</h4>
            <div className="tag-list warning">
              {skill_match.missing_required_skills.map(s => <span key={s}><X size={12} />{s}</span>)}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

// ─── Tab: Profile ─────────────────────────────────────────────────────────────
function TabProfile({ result }: { result: Analysis }) {
  const cp = result.candidate_profile
  const pi = cp.personal_info
  return (
    <div className="tab-profile">
      <div className="panel candidate-card">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PERSONAL INFO</p>
            <h3>{pi.full_name ?? 'Candidate'}</h3>
          </div>
          <div className="large-avatar" style={{ width: 52, height: 52, fontSize: 20 }}>
            {(pi.full_name ?? 'C').charAt(0)}
          </div>
        </div>
        <div className="info-grid">
          {pi.email    && <div className="info-row"><Mail  size={13}/><span>{pi.email}</span></div>}
          {pi.phone    && <div className="info-row"><Phone size={13}/><span>{pi.phone}</span></div>}
          {pi.location && <div className="info-row"><MapPin size={13}/><span>{pi.location}</span></div>}
          {pi.linkedin_url && <div className="info-row"><Globe size={13}/><a href={pi.linkedin_url} target="_blank" rel="noreferrer">LinkedIn</a></div>}
          {pi.github_url   && <div className="info-row"><Globe size={13}/><a href={pi.github_url}   target="_blank" rel="noreferrer">GitHub</a></div>}
        </div>
        {cp.languages.length > 0 ? (
          <div style={{ marginTop: 14 }}>
            <p className="eyebrow" style={{ marginBottom: 8 }}>LANGUAGES</p>
            <div className="tag-list">{cp.languages.map(l => <span key={l}>{l}</span>)}</div>
          </div>
        ) : <EmptyState message="No languages detected." />}
      </div>

      {/* Skills */}
      <div className="panel" style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 12 }}>EXTRACTED SKILLS</p>
        {cp.skills.technical_skills.length > 0 ? (
          <><h4 style={{ marginTop: 0 }}>Technical</h4>
          <div className="tag-list">{cp.skills.technical_skills.map(s => <span key={s}><Zap size={11}/>{s}</span>)}</div></>
        ) : <EmptyState message="No technical skills detected." />}
        {cp.skills.soft_skills.length > 0 && (
          <><h4>Soft Skills</h4>
          <div className="tag-list">{cp.skills.soft_skills.map(s => <span key={s}>{s}</span>)}</div></>
        )}
      </div>

      {/* Education */}
      <div className="panel" style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 12 }}>EDUCATION</p>
        {cp.education.length === 0 ? <EmptyState message="No education history detected." /> :
          cp.education.map((edu, i) => (
            <div className="edu-entry" key={i}>
              <div className="edu-icon"><BookOpen size={14}/></div>
              <div>
                <strong>{edu.degree ?? 'Degree'}</strong>
                <span>{edu.institution}</span>
                {edu.specialization && <span className="edu-spec">{edu.specialization}</span>}
                <div className="edu-meta">
                  {edu.graduation_year && <span>{edu.graduation_year}</span>}
                  {edu.gpa && <span>GPA: {edu.gpa}</span>}
                </div>
              </div>
            </div>
          ))}
      </div>

      {/* Experience */}
      <div className="panel" style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 12 }}>WORK EXPERIENCE</p>
        {cp.experience.length === 0 ? <EmptyState message="No work experience detected." /> :
          cp.experience.map((exp, i) => (
            <div className="exp-entry" key={i}>
              <div className="exp-icon"><Briefcase size={14}/></div>
              <div style={{ flex: 1 }}>
                <strong>{exp.position ?? 'Role'}</strong>
                <div className="exp-company">{exp.company}</div>
                <div className="exp-dates">{exp.start_date} – {exp.end_date ?? 'Present'}</div>
                {exp.responsibilities.length > 0 && (
                  <ul className="resp-list">
                    {exp.responsibilities.slice(0, 3).map((r, ri) => <li key={ri}>{r}</li>)}
                  </ul>
                )}
              </div>
            </div>
          ))}
      </div>

      {/* Projects */}
      <div className="panel" style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 12 }}>PROJECTS</p>
        {cp.projects.length === 0 ? <EmptyState message="No projects detected." /> :
          cp.projects.map((proj, i) => (
            <div className="project-entry" key={i}>
              <strong>{proj.name ?? 'Project'}</strong>
              {proj.description && <p>{proj.description}</p>}
              {proj.technologies.length > 0 && (
                <div className="tag-list" style={{ marginTop: 6 }}>
                  {proj.technologies.map(t => <span key={t}>{t}</span>)}
                </div>
              )}
            </div>
          ))}
      </div>

      {/* Certifications */}
      <div className="panel" style={{ marginTop: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 12 }}>CERTIFICATIONS</p>
        {cp.certifications.length === 0 ? <EmptyState message="No certifications detected." /> :
          cp.certifications.map((cert, i) => (
            <div className="cert-entry" key={i}>
              <Award size={14}/>
              <div>
                <strong>{cert.name}</strong>
                {cert.organization && <span>{cert.organization}</span>}
                {cert.completion_date && <span>{cert.completion_date}</span>}
              </div>
            </div>
          ))}
      </div>
    </div>
  )
}

// ─── Tab: Skills ──────────────────────────────────────────────────────────────
function TabSkills({ result }: { result: Analysis }) {
  const si = result.skill_intelligence
  return (
    <div className="tab-skills">
      <div className="result-grid" style={{ marginBottom: 14 }}>
        <div className="mini-result"><span>Total skills</span><strong>{si.metrics.total_skills}</strong><small>Unique normalized</small></div>
        <div className="mini-result"><span>Categorized</span><strong>{si.metrics.categorized_skills}</strong><small>{si.metrics.uncategorized_skills} uncategorized</small></div>
        <div className="mini-result"><span>Technical / Soft</span><strong>{si.metrics.technical_skill_count}/{si.metrics.soft_skill_count}</strong><small>Skill split</small></div>
      </div>
      {si.categories.length === 0 ? <EmptyState message="No skill categories detected." /> : (
        <div className="panel" style={{ marginBottom: 14 }}>
          <p className="eyebrow" style={{ marginBottom: 16 }}>SKILL CATEGORIES</p>
          {si.categories.map(cat => (
            <div className="skill-category-row" key={cat.name}>
              <div className="skill-cat-header">
                <strong>{cat.name}</strong>
                <span>{clamp(Math.round(cat.confidence * 100))}% coverage</span>
              </div>
              <div className="score-bar-track" style={{ marginBottom: 6 }}>
                <div className="score-bar-fill" style={{ width: `${clamp(cat.confidence * 100)}%` }} />
              </div>
              <div className="tag-list" style={{ marginBottom: 10 }}>
                {cat.skills.map(s => <span key={s}>{s}</span>)}
              </div>
            </div>
          ))}
        </div>
      )}
      {si.normalized_skills.length > 0 && (
        <div className="panel" style={{ marginBottom: 14 }}>
          <p className="eyebrow" style={{ marginBottom: 12 }}>ALL NORMALIZED SKILLS</p>
          <div className="tag-list">{si.normalized_skills.map(s => <span key={s}><Check size={12}/>{s}</span>)}</div>
        </div>
      )}
      {si.duplicate_skills.length > 0 && (
        <div className="panel" style={{ marginBottom: 14 }}>
          <p className="eyebrow" style={{ marginBottom: 12 }}>DUPLICATE ALIASES DETECTED</p>
          <div className="tag-list warning">{si.duplicate_skills.map(s => <span key={s}>{s}</span>)}</div>
          <p style={{ fontSize: 12, color: 'var(--muted)', marginTop: 10 }}>Deduplicated in the analysis.</p>
        </div>
      )}
      {si.gaps.missing_categories.length > 0 && (
        <div className="panel gap-panel">
          <p className="eyebrow" style={{ marginBottom: 12 }}>SKILL GAPS</p>
          {si.gaps.missing_categories.map((cat, i) => (
            <div className="gap-item" key={cat}>
              <div className="gap-item-label"><X size={13}/><strong>{cat}</strong></div>
              {si.gaps.recommendations[i] && <p>{si.gaps.recommendations[i]}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Tab: Experience ──────────────────────────────────────────────────────────
function TabExperience({ result }: { result: Analysis }) {
  const ei = result.experience_intelligence
  const m  = ei.metrics
  return (
    <div className="tab-experience">
      <div className="seniority-hero">
        <div>
          <p className="eyebrow">SENIORITY LEVEL</p>
          <span className="seniority-badge" style={{ background: seniorityColor(ei.seniority_level) }}>
            {ei.seniority_level}
          </span>
        </div>
        <div className="exp-metrics-inline">
          <div><strong>{m.total_experience_years}y</strong><span>Total</span></div>
          <div><strong>{m.company_count}</strong><span>Companies</span></div>
          {m.average_tenure_months != null && <div><strong>{monthsToYears(Math.round(m.average_tenure_months))}</strong><span>Avg. tenure</span></div>}
          <div><strong>{m.is_currently_employed ? 'Yes' : 'No'}</strong><span>Employed</span></div>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 14 }}>
        <div className="panel-heading">
          <div><p className="eyebrow">CAREER PROGRESSION</p><h3>{ei.progression.overall_trend}</h3></div>
        </div>
        {ei.progression.moves.length === 0 ? (
          <EmptyState message="Not enough dated roles to compute progression." />
        ) : (
          <div className="career-moves">
            {ei.progression.moves.map((move, i) => (
              <div className="career-move-row" key={i}>
                <div className="move-from"><span>{move.from_position ?? '—'}</span><small>{move.from_company}</small></div>
                <div className="move-arrow"><ChevronRight size={16}/><span className={`move-type ${move.move_type}`}>{move.move_type.replace('_',' ')}</span></div>
                <div className="move-to"><span>{move.to_position ?? '—'}</span><small>{move.to_company}</small></div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="panel" style={{ marginBottom: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 16 }}>CAREER TIMELINE</p>
        {ei.timeline.entries.length === 0 ? <EmptyState message="No timeline entries found." /> : (
          <div className="timeline-list">
            {ei.timeline.entries.map((entry, i) => (
              <div className="timeline-entry" key={i}>
                <div className="timeline-dot" style={{ background: entry.is_current ? 'var(--lime)' : 'var(--green)' }} />
                <div className="timeline-content">
                  <strong>{entry.position ?? 'Role'}</strong>
                  <span>{entry.company}</span>
                  <div className="timeline-meta">
                    {entry.start_year && <span>{entry.start_year}{entry.start_month ? `/${entry.start_month}` : ''} – {entry.is_current ? 'Present' : entry.end_year ?? '?'}</span>}
                    {entry.duration_months != null && <span className="pill" style={{ fontSize: 10 }}>{monthsToYears(entry.duration_months)}</span>}
                    {entry.is_current && <span className="pill green">Current</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stability */}
      <div className="panel" style={{ marginBottom: 14 }}>
        <p className="eyebrow" style={{ marginBottom: 14 }}>JOB STABILITY</p>
        <ScoreBar
          label="Stability score"
          value={clamp(ei.stability.stability_score * 100)}
          color={ei.stability.stability_score > 0.7 ? 'var(--green)' : ei.stability.stability_score > 0.4 ? '#c8a050' : '#c05840'}
        />
        <div className="info-grid" style={{ marginTop: 14 }}>
          <div className="info-row"><TrendingUp size={13}/><span>Job changes: {ei.stability.job_change_count}</span></div>
          {ei.stability.longest_tenure_months != null && (
            <div className="info-row"><Check size={13}/><span>Longest role: {monthsToYears(ei.stability.longest_tenure_months)}</span></div>
          )}
        </div>
      </div>

      {/* Gaps */}
      {ei.gap_analysis.gap_count > 0 ? (
        <div className="panel gap-panel">
          <p className="eyebrow" style={{ marginBottom: 12 }}>EMPLOYMENT GAPS</p>
          <p style={{ fontSize: 13, color: 'var(--muted)', marginBottom: 14 }}>
            {ei.gap_analysis.gap_count} gap(s) totaling {monthsToYears(ei.gap_analysis.total_gap_months)}
          </p>
          {ei.gap_analysis.gaps.map((gap, i) => (
            <div className="gap-item" key={i}>
              <div className="gap-item-label">
                <span>{gap.after_company ?? '—'}</span>
                <ChevronRight size={13}/>
                <span>{monthsToYears(gap.gap_months)} gap</span>
                <ChevronRight size={13}/>
                <span>{gap.before_company ?? '—'}</span>
              </div>
            </div>
          ))}
        </div>
      ) : <EmptyState message="No employment gaps detected." />}
    </div>
  )
}

// ─── Tab: Match ───────────────────────────────────────────────────────────────
function TabMatch({ result }: { result: Analysis }) {
  const cm = result.candidate_matching
  return (
    <div className="tab-match">
      <div className="panel" style={{ marginBottom: 14 }}>
        <div className="panel-heading"><div><p className="eyebrow">SKILL MATCH</p><h3>Required skill coverage</h3></div></div>
        <ScoreBar label="Required skills matched"  value={cm.skill_match.required_match_percentage} />
        <ScoreBar label="Preferred skills matched" value={cm.skill_match.preferred_match_percentage} color="#8abba5" />
        {cm.skill_match.matched_required_skills.length > 0 && (
          <><h4 style={{ marginTop: 20 }}>Matched required</h4>
          <div className="tag-list">{cm.skill_match.matched_required_skills.map(s => <span key={s}><Check size={12}/>{s}</span>)}</div></>
        )}
        {cm.skill_match.matched_preferred_skills.length > 0 && (
          <><h4>Matched preferred</h4>
          <div className="tag-list">{cm.skill_match.matched_preferred_skills.map(s => <span key={s}><Check size={12}/>{s}</span>)}</div></>
        )}
        {cm.skill_match.missing_required_skills.length > 0 ? (
          <><h4>Missing required</h4>
          <div className="tag-list warning">{cm.skill_match.missing_required_skills.map(s => <span key={s}><X size={12}/>{s}</span>)}</div></>
        ) : <EmptyState message="All required skills matched!" />}
      </div>
      <div className="panel" style={{ marginBottom: 14 }}>
        <div className="panel-heading"><div><p className="eyebrow">EXPERIENCE MATCH</p><h3>Years of experience</h3></div><MeetsBadge meets={cm.experience_match.meets_requirement} /></div>
        <div className="match-compare">
          <div className="match-side"><span>Required</span><strong>{cm.experience_match.required_years}y</strong></div>
          <div className="match-vs">vs</div>
          <div className="match-side candidate"><span>Candidate</span><strong>{cm.experience_match.candidate_years}y</strong></div>
        </div>
        <ScoreBar label="Experience match" value={cm.experience_match.experience_match_percentage} color={cm.experience_match.meets_requirement ? 'var(--green)' : '#c05840'} />
      </div>
      <div className="panel">
        <div className="panel-heading"><div><p className="eyebrow">EDUCATION MATCH</p><h3>Degree comparison</h3></div><MeetsBadge meets={cm.education_match.meets_requirement} /></div>
        <div className="match-compare">
          <div className="match-side"><span>Required</span><strong>{cm.education_match.required_degree ?? 'Not specified'}</strong></div>
          <div className="match-vs">vs</div>
          <div className="match-side candidate"><span>Candidate</span><strong>{cm.education_match.candidate_degree ?? 'Not found'}</strong></div>
        </div>
      </div>
    </div>
  )
}

// ─── Main ─────────────────────────────────────────────────────────────────────
export default function AnalysisResult({ result, jobTitle, jobCompany }: AnalysisResultProps) {
  const [tab, setTab] = useState<Tab>('overview')
  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview',    label: 'Overview',    icon: <Zap      size={14}/> },
    { id: 'profile',     label: 'Profile',     icon: <User     size={14}/> },
    { id: 'skills',      label: 'Skills',      icon: <Check    size={14}/> },
    { id: 'experience',  label: 'Experience',  icon: <Briefcase size={14}/> },
    { id: 'match',       label: 'Job Match',   icon: <TrendingUp size={14}/> },
  ]
  return (
    <section className="analysis-results">
      {/* Sticky "matched against" header — always visible when scrolling through tabs */}
      {jobTitle && (
        <div className="result-job-header">
          <span className="result-job-label">Matched against</span>
          <span className="result-job-title">{jobTitle}</span>
          {jobCompany && <span className="result-job-company">· {jobCompany}</span>}
        </div>
      )}

      <div className="result-tabs">
        {tabs.map(t => (
          <button key={t.id} id={`tab-${t.id}`} className={`tab-btn${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>
      <div className="tab-content">
        {tab === 'overview'   && <TabOverview   result={result} jobTitle={jobTitle} jobCompany={jobCompany} />}
        {tab === 'profile'    && <TabProfile    result={result} />}
        {tab === 'skills'     && <TabSkills     result={result} />}
        {tab === 'experience' && <TabExperience result={result} />}
        {tab === 'match'      && <TabMatch      result={result} />}
      </div>
    </section>
  )
}
