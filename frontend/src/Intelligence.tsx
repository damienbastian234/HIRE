import { ChangeEvent, DragEvent, useRef, useState } from 'react'
import { FileText, Plus, Sparkles, Trash2, Wand2, X } from 'lucide-react'
import { api, EmploymentType, JobRequirement, parseError, SkillRequirement, WorkMode } from './api'
import AnalysisResult from './AnalysisResult'
import type { Analysis } from './api'

// ─── Demo data ────────────────────────────────────────────────────────────────
const DEMO_RESUME = `Alex Morgan
Product Designer
alex@example.com | +1 415 555 0192 | San Francisco, CA
LinkedIn: linkedin.com/in/alexmorgan | GitHub: github.com/alexmorgan

EXPERIENCE
Northstar Labs — Product Designer — Jan 2022 to Present
- Designed AI-powered recruiting workflows that improved applicant conversion by 32%.
- Led end-to-end design for 3 major product launches.
- Collaborated with engineering teams using Figma + React prototypes.

Pixel & Co — Junior Designer — Jun 2020 to Dec 2021
- Created UI components for a SaaS dashboard used by 50k+ users.
- Conducted 20+ usability interviews and synthesized findings into design iterations.

SKILLS
Technical: Figma, React, TypeScript, HTML, CSS, Framer, Storybook, user research, prototyping, accessibility
Soft: Communication, leadership, problem-solving, stakeholder management

EDUCATION
B.A. Design — California College of the Arts, 2020 — GPA: 3.8

PROJECTS
HIRE Design System: Built a component library with 60+ components in Figma and React.
Technologies: Figma, React, TypeScript, Storybook

CERTIFICATIONS
Google UX Design Certificate — Google, 2021

LANGUAGES
English, Spanish`

// ─── Form types ───────────────────────────────────────────────────────────────
type SkillRow = { name: string; required: boolean; minimum_proficiency: string; minimum_years: string }

function defaultForm() {
  return {
    title: '',
    department: '',
    company: '',
    location: '',
    work_mode: '' as WorkMode | '',
    employment_type: '' as EmploymentType | '',
    description: '',
    responsibilities: [''],
    required_skills:  [{ name: '', required: true, minimum_proficiency: '', minimum_years: '' }] as SkillRow[],
    preferred_skills: [{ name: '', required: false, minimum_proficiency: '', minimum_years: '' }] as SkillRow[],
    exp_minimum_years:  '',
    exp_preferred_years:'',
    edu_degrees:  [''],
    edu_fields:   [''],
    edu_min_percentage: '',
    edu_min_cgpa: '',
    salary_min: '',
    salary_max: '',
    salary_currency: 'INR',
    keywords: [''],
  }
}

function demoJobForm() {
  return {
    title: 'Product Designer',
    department: 'Design',
    company: 'Northstar Labs',
    location: 'San Francisco, CA',
    work_mode: 'HYBRID' as WorkMode,
    employment_type: 'FULL_TIME' as EmploymentType,
    description: 'Design and ship AI-powered recruiting workflows.',
    responsibilities: ['Lead end-to-end product design', 'Conduct user research', 'Maintain the design system'],
    required_skills: [
      { name: 'Figma',         required: true, minimum_proficiency: 'Advanced',     minimum_years: '2' },
      { name: 'React',         required: true, minimum_proficiency: 'Intermediate', minimum_years: '1' },
      { name: 'User Research', required: true, minimum_proficiency: 'Intermediate', minimum_years: '' },
    ] as SkillRow[],
    preferred_skills: [
      { name: 'TypeScript',   required: false, minimum_proficiency: '', minimum_years: '' },
      { name: 'Accessibility',required: false, minimum_proficiency: '', minimum_years: '' },
    ] as SkillRow[],
    exp_minimum_years:  '2',
    exp_preferred_years:'4',
    edu_degrees:  ['B.A.', 'B.Des'],
    edu_fields:   ['Design', 'Human-Computer Interaction'],
    edu_min_percentage: '',
    edu_min_cgpa: '',
    salary_min: '120000',
    salary_max: '150000',
    salary_currency: 'USD',
    keywords: ['UX', 'product design', 'figma', 'AI'],
  }
}

function buildJobRequirement(form: ReturnType<typeof defaultForm>): JobRequirement {
  const req: JobRequirement = { title: form.title.trim() }
  if (form.department.trim())     req.department     = form.department.trim()
  if (form.company.trim())        req.company        = form.company.trim()
  if (form.location.trim())       req.location       = form.location.trim()
  if (form.work_mode)             req.work_mode      = form.work_mode as WorkMode
  if (form.employment_type)       req.employment_type= form.employment_type as EmploymentType
  if (form.description.trim())    req.description    = form.description.trim()

  const resp = form.responsibilities.filter(r => r.trim())
  if (resp.length) req.responsibilities = resp

  const toSkill = (s: SkillRow): SkillRequirement => ({
    name: s.name.trim(),
    required: s.required,
    ...(s.minimum_proficiency.trim() ? { minimum_proficiency: s.minimum_proficiency.trim() } : {}),
    ...(s.minimum_years.trim() && !isNaN(+s.minimum_years) ? { minimum_years: +s.minimum_years } : {}),
  })

  const reqSkills = form.required_skills.filter(s => s.name.trim()).map(toSkill)
  if (reqSkills.length) req.required_skills = reqSkills

  const prefSkills = form.preferred_skills.filter(s => s.name.trim()).map(toSkill)
  if (prefSkills.length) req.preferred_skills = prefSkills

  const minYrs = parseFloat(form.exp_minimum_years)
  if (!isNaN(minYrs)) {
    const prefYrs = parseFloat(form.exp_preferred_years)
    req.experience = { minimum_years: minYrs, ...(!isNaN(prefYrs) ? { preferred_years: prefYrs } : {}) }
  }

  const hasDeg = form.edu_degrees.some(d => d.trim())
  const hasFld = form.edu_fields.some(f => f.trim())
  const pct    = parseFloat(form.edu_min_percentage)
  const cgpa   = parseFloat(form.edu_min_cgpa)
  if (hasDeg || hasFld || !isNaN(pct) || !isNaN(cgpa)) {
    req.education = {
      ...(hasDeg ? { degrees:         form.edu_degrees.filter(d => d.trim()) } : {}),
      ...(hasFld ? { fields_of_study: form.edu_fields.filter(f => f.trim())  } : {}),
      ...(!isNaN(pct)  ? { minimum_percentage: pct  } : {}),
      ...(!isNaN(cgpa) ? { minimum_cgpa:       cgpa } : {}),
    }
  }

  const salMin = parseFloat(form.salary_min)
  const salMax = parseFloat(form.salary_max)
  if (!isNaN(salMin) || !isNaN(salMax) || form.salary_currency.trim()) {
    req.salary = {
      ...(!isNaN(salMin) ? { minimum: salMin } : {}),
      ...(!isNaN(salMax) ? { maximum: salMax } : {}),
      ...(form.salary_currency.trim() ? { currency: form.salary_currency.trim() } : {}),
    }
  }

  const kws = form.keywords.filter(k => k.trim())
  if (kws.length) req.keywords = kws
  return req
}

// ─── Sub-components ───────────────────────────────────────────────────────────
function Section({
  title, defaultOpen = false, badge, children,
}: { title: string; defaultOpen?: boolean; badge?: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="job-req-section">
      <button type="button" className="job-req-header" onClick={() => setOpen(!open)}>
        <span>{title}</span>
        {badge && <span className="req-badge">{badge}</span>}
        <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 18 }}>{open ? '−' : '+'}</span>
      </button>
      {open && <div className="job-req-body">{children}</div>}
    </div>
  )
}

function DynList({ items, onChange, placeholder, label }: {
  items: string[]; onChange: (v: string[]) => void; placeholder?: string; label?: string
}) {
  const update = (i: number, v: string) => { const n=[...items]; n[i]=v; onChange(n) }
  const add    = () => onChange([...items, ''])
  const remove = (i: number) => onChange(items.filter((_,j)=>j!==i).length ? items.filter((_,j)=>j!==i) : [''])
  return (
    <div className="dynamic-list">
      {label && <p className="eyebrow" style={{ marginBottom: 8 }}>{label}</p>}
      {items.map((item, i) => (
        <div className="dynamic-list-row" key={i}>
          <input value={item} placeholder={placeholder ?? 'Enter value'} onChange={e => update(i, e.target.value)} />
          <button type="button" className="icon-button remove-btn" onClick={() => remove(i)}><X size={14} /></button>
        </div>
      ))}
      <button type="button" className="add-btn" onClick={add}><Plus size={13} /> Add</button>
    </div>
  )
}

function SkillList({ items, onChange, showRequired }: {
  items: SkillRow[]; onChange: (v: SkillRow[]) => void; showRequired?: boolean
}) {
  const update = <K extends keyof SkillRow>(i: number, k: K, v: SkillRow[K]) => {
    const n=[...items]; n[i]={...n[i],[k]:v}; onChange(n)
  }
  const add    = () => onChange([...items, { name:'', required:true, minimum_proficiency:'', minimum_years:'' }])
  const remove = (i: number) => {
    const n = items.filter((_,j)=>j!==i)
    onChange(n.length ? n : [{ name:'', required:true, minimum_proficiency:'', minimum_years:'' }])
  }
  return (
    <div className="dynamic-list">
      {items.map((item, i) => (
        <div className="skill-req-item" key={i}>
          <input className="skill-name-input" value={item.name} placeholder="Skill name *" onChange={e => update(i,'name',e.target.value)} />
          <input value={item.minimum_proficiency} placeholder="Proficiency level" onChange={e => update(i,'minimum_proficiency',e.target.value)} />
          <input type="number" min="0" step="0.5" value={item.minimum_years} placeholder="Min yrs" onChange={e => update(i,'minimum_years',e.target.value)} />
          {showRequired && (
            <label className="req-toggle">
              <input type="checkbox" checked={item.required} onChange={e => update(i,'required',e.target.checked)} />
              Required
            </label>
          )}
          <button type="button" className="icon-button remove-btn" onClick={() => remove(i)}><X size={14} /></button>
        </div>
      ))}
      <button type="button" className="add-btn" onClick={add}><Plus size={13} /> Add skill</button>
    </div>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function Intelligence() {
  const [resume,    setResume]    = useState(DEMO_RESUME)
  const [filename,  setFilename]  = useState('Demo resume (editable)')
  const [form,      setForm]      = useState(defaultForm())
  const [result,    setResult]    = useState<Analysis | null>(null)
  const [busy,      setBusy]      = useState(false)
  const [extracting,setExtracting]= useState(false)
  const [dragging,  setDragging]  = useState(false)
  const [error,     setError]     = useState('')
  const [titleError,setTitleError]= useState('')

  // Abort controller ref to cancel stale requests
  const abortRef = useRef<AbortController | null>(null)

  const setF = <K extends keyof ReturnType<typeof defaultForm>>(k: K, v: ReturnType<typeof defaultForm>[K]) =>
    setForm(f => ({ ...f, [k]: v }))

  const resetAll = () => {
    abortRef.current?.abort()
    setResume(DEMO_RESUME)
    setFilename('Demo resume (editable)')
    setForm(defaultForm())
    setResult(null)
    setError('')
    setTitleError('')
    setBusy(false)
    setExtracting(false)
  }

  const loadFile = async (file: File) => {
    if (busy || extracting) return  // prevent overlapping requests
    const ext = file.name.toLowerCase().split('.').pop() ?? ''
    if (!['pdf', 'docx'].includes(ext)) {
      setError('Only PDF and DOCX files are supported. Please convert .doc files to .docx or PDF.')
      return
    }
    abortRef.current?.abort()
    abortRef.current = new AbortController()
    setExtracting(true)
    setError('')
    try {
      const r = await api.extractResume(file, abortRef.current.signal)
      setResume(r.text)
      setFilename(r.filename ?? file.name)
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        setError(parseError(err))
      }
      // AbortError: user cancelled — silently ignore, don't clear existing state
    } finally {
      setExtracting(false)
    }
  }

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) void loadFile(file)
  }

  const onChoose = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) void loadFile(file)
    e.target.value = ''  // allow re-selecting same file
  }

  const analyze = async () => {
    if (busy || extracting) return  // prevent overlapping requests
    setTitleError('')
    if (!form.title.trim()) { setTitleError('Job title is required to run analysis.'); return }
    if (!resume.trim())     { setError('Please provide resume text.'); return }

    abortRef.current?.abort()
    abortRef.current = new AbortController()
    const signal = abortRef.current.signal

    setBusy(true)
    setError('')
    try {
      const jobReq = buildJobRequirement(form)
      // Pass the signal so the fetch is cancelled if the user resets or navigates away.
      const r = await api.analyze(resume, jobReq, signal)
      // Guard against stale response after an abort — don't overwrite newer state.
      if (!signal.aborted) {
        setResult(r.data)
      }
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        setError(parseError(err))
      }
      // AbortError: user cancelled — silently ignore
    } finally {
      setBusy(false)
    }
  }


  const reqCount  = form.required_skills.filter(s => s.name.trim()).length
  const prefCount = form.preferred_skills.filter(s => s.name.trim()).length

  return (
    <div className="intelligence-layout">
      {/* ── Left: resume + job form ── */}
      <div className="intelligence-left">

        {/* Resume upload */}
        <section className="panel resume-input">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">RESUME ANALYSIS</p>
              <h3>Give your experience a sharper signal</h3>
            </div>
            <FileText size={21} />
          </div>

          <div
            className={dragging ? 'drop-zone dragging' : 'drop-zone'}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input id="resume-file" type="file" accept=".pdf,.doc,.docx" onChange={onChoose} />
            <FileText size={25} />
            <strong>{extracting ? 'Reading your resume…' : filename}</strong>
            <span>Drag &amp; drop a PDF, DOC, or DOCX here</span>
            <label htmlFor="resume-file" className="file-button" style={{ pointerEvents: extracting ? 'none' : 'auto' }}>
              {extracting ? 'Extracting…' : 'Choose file'}
            </label>
          </div>

          <textarea
            value={resume}
            onChange={e => { setResume(e.target.value); setFilename('Edited resume text') }}
            disabled={extracting}
            aria-label="Resume text"
          />
          <div className="input-footer"><span>{resume.length} characters</span></div>
        </section>

        {/* Job Requirement form */}
        <section className="panel job-req-panel" style={{ marginTop: 14 }}>
          <div className="panel-heading">
            <div>
              <p className="eyebrow">JOB REQUIREMENT</p>
              <h3>Define the role to match against</h3>
            </div>
            <button type="button" className="text-button" onClick={() => setForm(demoJobForm())} title="Fill demo job">
              <Wand2 size={14} /> Use demo job
            </button>
          </div>

          <Section title="Role details" defaultOpen badge="required">
            <div className="form-grid">
              <label className="full-span">
                Job title *
                <input
                  value={form.title}
                  placeholder="e.g. Product Designer"
                  onChange={e => setF('title', e.target.value)}
                  style={titleError ? { borderColor: '#c05840' } : {}}
                />
                {titleError && <span className="field-error">{titleError}</span>}
              </label>
              <label>Company<input value={form.company} placeholder="e.g. Northstar Labs" onChange={e => setF('company', e.target.value)} /></label>
              <label>Department<input value={form.department} placeholder="e.g. Design" onChange={e => setF('department', e.target.value)} /></label>
              <label>Location<input value={form.location} placeholder="e.g. San Francisco, CA" onChange={e => setF('location', e.target.value)} /></label>
              <label>
                Work mode
                <select value={form.work_mode} onChange={e => setF('work_mode', e.target.value as WorkMode | '')}>
                  <option value="">— Select —</option>
                  <option value="ONSITE">Onsite</option>
                  <option value="REMOTE">Remote</option>
                  <option value="HYBRID">Hybrid</option>
                </select>
              </label>
              <label>
                Employment type
                <select value={form.employment_type} onChange={e => setF('employment_type', e.target.value as EmploymentType | '')}>
                  <option value="">— Select —</option>
                  <option value="FULL_TIME">Full-time</option>
                  <option value="PART_TIME">Part-time</option>
                  <option value="CONTRACT">Contract</option>
                  <option value="INTERN">Internship</option>
                  <option value="FREELANCE">Freelance</option>
                  <option value="TEMPORARY">Temporary</option>
                </select>
              </label>
            </div>
          </Section>

          <Section title="Description &amp; responsibilities">
            <label style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
              Job description
              <textarea className="job-desc-textarea" value={form.description} placeholder="What does this role involve?" onChange={e => setF('description', e.target.value)} />
            </label>
            <DynList label="RESPONSIBILITIES" items={form.responsibilities} onChange={v => setF('responsibilities', v)} placeholder="e.g. Lead end-to-end design" />
          </Section>

          <Section title="Required skills" badge={reqCount > 0 ? `${reqCount} added` : undefined}>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>Mandatory skills — scored directly in the analysis.</p>
            <SkillList items={form.required_skills} onChange={v => setF('required_skills', v)} showRequired />
          </Section>

          <Section title="Preferred skills" badge={prefCount > 0 ? `${prefCount} added` : undefined}>
            <p style={{ fontSize: 12, color: 'var(--muted)', marginBottom: 12 }}>Nice-to-have skills that give candidates an edge.</p>
            <SkillList items={form.preferred_skills} onChange={v => setF('preferred_skills', v)} />
          </Section>

          <Section title="Experience &amp; education">
            <div className="form-grid" style={{ marginBottom: 18 }}>
              <label>Min. experience (years)<input type="number" min="0" step="0.5" value={form.exp_minimum_years} placeholder="e.g. 2" onChange={e => setF('exp_minimum_years', e.target.value)} /></label>
              <label>Preferred experience (years)<input type="number" min="0" step="0.5" value={form.exp_preferred_years} placeholder="e.g. 4" onChange={e => setF('exp_preferred_years', e.target.value)} /></label>
            </div>
            <DynList label="ACCEPTED DEGREES" items={form.edu_degrees} onChange={v => setF('edu_degrees', v)} placeholder="e.g. B.Tech, M.Sc" />
            <div style={{ marginTop: 14 }}>
              <DynList label="FIELDS OF STUDY" items={form.edu_fields} onChange={v => setF('edu_fields', v)} placeholder="e.g. Computer Science" />
            </div>
            <div className="form-grid" style={{ marginTop: 16 }}>
              <label>Min. percentage (0–100)<input type="number" min="0" max="100" value={form.edu_min_percentage} placeholder="e.g. 60" onChange={e => setF('edu_min_percentage', e.target.value)} /></label>
              <label>Min. CGPA (0–10)<input type="number" min="0" max="10" step="0.1" value={form.edu_min_cgpa} placeholder="e.g. 7.0" onChange={e => setF('edu_min_cgpa', e.target.value)} /></label>
            </div>
          </Section>

          <Section title="Compensation &amp; keywords">
            <div className="form-grid" style={{ marginBottom: 18 }}>
              <label>Min. salary<input type="number" min="0" value={form.salary_min} placeholder="e.g. 120000" onChange={e => setF('salary_min', e.target.value)} /></label>
              <label>Max. salary<input type="number" min="0" value={form.salary_max} placeholder="e.g. 150000" onChange={e => setF('salary_max', e.target.value)} /></label>
              <label>Currency<input value={form.salary_currency} placeholder="INR / USD" onChange={e => setF('salary_currency', e.target.value)} /></label>
            </div>
            <DynList label="KEYWORDS" items={form.keywords} onChange={v => setF('keywords', v)} placeholder="e.g. product design, AI" />
          </Section>

          {/* Analyze footer */}
          <div className="analyze-footer">
            {error && <p className="error-text" role="alert" style={{ margin: 0 }}>{error}</p>}
            <div style={{ display: 'flex', gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
              <button type="button" className="text-button" onClick={resetAll} disabled={busy || extracting}>
                <Trash2 size={13} /> Reset
              </button>
              <button
                className="primary-button"
                onClick={analyze}
                disabled={busy || extracting || !resume.trim()}
                id="run-analysis-btn"
                type="button"
              >
                {busy ? 'Analyzing…' : <><Sparkles size={16} /> Run analysis</>}
              </button>
            </div>
          </div>
        </section>
      </div>

      {/* ── Right: results ── */}
      <div className="intelligence-right">
        {result ? (
          <AnalysisResult
            result={result}
            jobTitle={form.title.trim() || undefined}
            jobCompany={form.company.trim() || undefined}
          />
        ) : (
          <section className="analysis-placeholder">
            <Sparkles size={28} />
            <h3>Your intelligence report will appear here</h3>
            <p>
              Fill in the job details and click <strong>Run analysis</strong> to see the full match report.
            </p>
          </section>
        )}
      </div>
    </div>
  )
}
