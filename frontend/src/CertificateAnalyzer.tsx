import { useRef, useState } from 'react'
import {
  ShieldCheck, ShieldAlert, ShieldX, Upload, FileText,
  CheckCircle2, AlertTriangle, XCircle, RotateCcw, Info,
} from 'lucide-react'
import { parseError } from './api'

// ─── Types ────────────────────────────────────────────────────────────────────
type Verdict = 'AUTHENTIC' | 'SUSPICIOUS' | 'LIKELY_FAKE'
type CheckStatus = 'PASS' | 'WARN' | 'FAIL'

interface Finding {
  status: CheckStatus
  detail: string
}

interface Analysis {
  verdict: Verdict
  confidence: number
  summary: string
  authenticity_score: number
  findings: {
    visual_integrity:   Finding
    official_markers:   Finding
    typography_layout:  Finding
    signatures:         Finding
    date_reference:     Finding
    issuing_authority:  Finding
    overall_coherence:  Finding
  }
  red_flags: string[]
  positive_indicators: string[]
  recommendation: string
  document_type: string
}

interface AnalysisResult {
  filename: string
  analysis: Analysis
}

// ─── Constants ────────────────────────────────────────────────────────────────
const ACCEPTED = '.jpg,.jpeg,.png,.webp,.pdf'
const MAX_MB   = 15

const FINDING_LABELS: Record<string, string> = {
  visual_integrity:  'Visual Integrity',
  official_markers:  'Official Markers',
  typography_layout: 'Typography & Layout',
  signatures:        'Signatures',
  date_reference:    'Dates & References',
  issuing_authority: 'Issuing Authority',
  overall_coherence: 'Overall Coherence',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function VerdictIcon({ verdict, size = 40 }: { verdict: Verdict; size?: number }) {
  if (verdict === 'AUTHENTIC')    return <ShieldCheck  size={size} />
  if (verdict === 'SUSPICIOUS')   return <ShieldAlert  size={size} />
  return <ShieldX size={size} />
}

function verdictColor(v: Verdict) {
  return v === 'AUTHENTIC' ? '#2d6a57' : v === 'SUSPICIOUS' ? '#c07830' : '#c05840'
}
function verdictBg(v: Verdict) {
  return v === 'AUTHENTIC' ? '#eafaf3' : v === 'SUSPICIOUS' ? '#fff8f2' : '#fff2f0'
}
function verdictBorder(v: Verdict) {
  return v === 'AUTHENTIC' ? '#b0dcc8' : v === 'SUSPICIOUS' ? '#f0c0b4' : '#f5b8b0'
}
function verdictLabel(v: Verdict) {
  return v === 'AUTHENTIC' ? 'Likely Authentic' : v === 'SUSPICIOUS' ? 'Suspicious' : 'Likely Fake / Tampered'
}

function StatusIcon({ status }: { status: CheckStatus }) {
  if (status === 'PASS') return <CheckCircle2 size={15} color="#2d6a57" />
  if (status === 'WARN') return <AlertTriangle size={15} color="#c07830" />
  return <XCircle size={15} color="#c05840" />
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70 ? '#2d6a57' : score >= 40 ? '#c07830' : '#c05840'
  return (
    <div className="cert-score-bar-track">
      <div className="cert-score-bar-fill" style={{ width: `${score}%`, background: color }} />
    </div>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function CertificateAnalyzer() {
  const [file, setFile]         = useState<File | null>(null)
  const [preview, setPreview]   = useState<string | null>(null)
  const [result, setResult]     = useState<AnalysisResult | null>(null)
  const [busy, setBusy]         = useState(false)
  const [error, setError]       = useState('')
  const [drag, setDrag]         = useState(false)
  const inputRef                = useRef<HTMLInputElement>(null)

  // ── File pick ────────────────────────────────────────────────────────────
  const pickFile = (f: File) => {
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File is too large. Maximum allowed size is ${MAX_MB} MB.`); return
    }
    const ext = f.name.split('.').pop()?.toLowerCase() || ''
    if (!['jpg','jpeg','png','webp','pdf'].includes(ext)) {
      setError('Unsupported file type. Please upload JPG, PNG, WEBP, or PDF.'); return
    }
    setError('')
    setResult(null)
    setFile(f)

    // Image preview
    if (ext !== 'pdf') {
      const reader = new FileReader()
      reader.onload = e => setPreview(e.target?.result as string)
      reader.readAsDataURL(f)
    } else {
      setPreview(null)
    }
  }

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) pickFile(e.target.files[0])
  }
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDrag(false)
    if (e.dataTransfer.files?.[0]) pickFile(e.dataTransfer.files[0])
  }

  // ── Analyze ──────────────────────────────────────────────────────────────
  const analyze = async () => {
    if (!file) return
    setBusy(true); setError('')
    try {
      const API_BASE = import.meta.env.VITE_API_TARGET || 'http://127.0.0.1:8000'
      const token    = localStorage.getItem('hire-token') || ''
      const form     = new FormData()
      form.append('file', file)

      const res = await fetch(`${API_BASE}/api/v1/certificate/analyze`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Analysis failed.')
      setResult(data as AnalysisResult)
    } catch (err) {
      setError(parseError(err))
    } finally {
      setBusy(false)
    }
  }

  const reset = () => {
    setFile(null); setPreview(null); setResult(null); setError('')
    if (inputRef.current) inputRef.current.value = ''
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="cert-root">

      {/* ── Upload panel ──────────────────────────────────────────────────── */}
      <div className="cert-upload-panel">

        {/* Drop zone */}
        <div
          className={`cert-dropzone ${drag ? 'cert-drag' : ''} ${file ? 'cert-has-file' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true) }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED}
            style={{ display: 'none' }}
            onChange={onInputChange}
          />

          {file ? (
            <div className="cert-file-info">
              {preview
                ? <img src={preview} className="cert-preview-img" alt="Certificate preview" />
                : <div className="cert-pdf-icon"><FileText size={48} /></div>
              }
              <p className="cert-file-name">{file.name}</p>
              <p className="cert-file-size">{(file.size / 1024).toFixed(0)} KB</p>
            </div>
          ) : (
            <div className="cert-drop-idle">
              <div className="cert-drop-icon"><Upload size={28} /></div>
              <p className="cert-drop-title">Drop your certificate here</p>
              <p className="cert-drop-sub">or click to browse</p>
              <p className="cert-drop-formats">JPG · PNG · WEBP · PDF — up to {MAX_MB} MB</p>
            </div>
          )}
        </div>

        {error && <p className="error-text cert-error" role="alert">{error}</p>}

        {/* Actions */}
        <div className="cert-actions">
          {file && (
            <button className="secondary-button" onClick={reset}>
              <RotateCcw size={14} /> Clear
            </button>
          )}
          <button
            className="primary-button"
            onClick={analyze}
            disabled={!file || busy}
            style={{ flex: 1 }}
          >
            {busy
              ? <><div className="cert-spinner" /> Analyzing…</>
              : <><ShieldCheck size={16} /> Analyze Certificate</>
            }
          </button>
        </div>

        {/* Info box */}
        <div className="cert-info-box">
          <Info size={14} />
          <p>
            Upload any certificate, degree, ID card, or official document.
            Our AI forensics engine examines 7 authenticity dimensions and returns
            a verdict with confidence score and detailed findings.
          </p>
        </div>
      </div>

      {/* ── Results panel ─────────────────────────────────────────────────── */}
      {result && (() => {
        const a = result.analysis
        const vc = verdictColor(a.verdict)
        return (
          <div className="cert-results">

            {/* Verdict hero */}
            <div
              className="cert-verdict-hero"
              style={{ background: verdictBg(a.verdict), borderColor: verdictBorder(a.verdict) }}
            >
              <div style={{ color: vc }}><VerdictIcon verdict={a.verdict} size={44} /></div>
              <div className="cert-verdict-text">
                <p className="cert-doc-type">{a.document_type}</p>
                <h2 style={{ color: vc }}>{verdictLabel(a.verdict)}</h2>
                <p className="cert-summary">{a.summary}</p>
              </div>
              <div className="cert-score-ring-wrap">
                <svg width={80} height={80} viewBox="0 0 80 80">
                  <circle cx={40} cy={40} r={34} fill="none" stroke="#e4e1d8" strokeWidth={7} />
                  <circle
                    cx={40} cy={40} r={34} fill="none"
                    stroke={vc} strokeWidth={7}
                    strokeDasharray={2 * Math.PI * 34}
                    strokeDashoffset={2 * Math.PI * 34 * (1 - a.authenticity_score / 100)}
                    strokeLinecap="round"
                    transform="rotate(-90 40 40)"
                    style={{ transition: 'stroke-dashoffset 1.2s ease' }}
                  />
                  <text x={40} y={45} textAnchor="middle" fill={vc} fontSize={19} fontWeight={700}>
                    {a.authenticity_score}
                  </text>
                </svg>
                <p className="cert-score-label">Authenticity</p>
              </div>
            </div>

            {/* Recommendation */}
            <div className="cert-recommendation">
              <p className="cert-rec-label">📋 Recommendation</p>
              <p className="cert-rec-text">{a.recommendation}</p>
              <p className="cert-confidence">AI confidence: <strong>{a.confidence}%</strong></p>
            </div>

            {/* 7-dimension findings */}
            <div className="cert-findings">
              <h3 className="cert-section-title">Dimension Analysis</h3>
              <div className="cert-findings-grid">
                {(Object.entries(a.findings) as [string, Finding][]).map(([key, f]) => (
                  <div key={key} className={`cert-finding-card cert-finding-${f.status.toLowerCase()}`}>
                    <div className="cert-finding-header">
                      <StatusIcon status={f.status} />
                      <span className="cert-finding-name">{FINDING_LABELS[key]}</span>
                      <span className={`cert-finding-badge cert-badge-${f.status.toLowerCase()}`}>
                        {f.status}
                      </span>
                    </div>
                    <p className="cert-finding-detail">{f.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Authenticity score bar */}
            <div className="cert-score-section">
              <div className="cert-score-row">
                <span className="cert-score-label2">Overall Authenticity Score</span>
                <span style={{ fontWeight: 700, color: vc }}>{a.authenticity_score}/100</span>
              </div>
              <ScoreBar score={a.authenticity_score} />
            </div>

            {/* Red flags & positive indicators */}
            <div className="cert-flags-grid">
              {a.red_flags.length > 0 && (
                <div className="cert-flags-box cert-red-flags">
                  <p className="cert-flags-title"><XCircle size={15} /> Red Flags</p>
                  <ul>
                    {a.red_flags.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}
              {a.positive_indicators.length > 0 && (
                <div className="cert-flags-box cert-positive">
                  <p className="cert-flags-title"><CheckCircle2 size={15} /> Positive Indicators</p>
                  <ul>
                    {a.positive_indicators.map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>
              )}
            </div>

            {/* Analyze another */}
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: 4 }}>
              <button className="secondary-button" onClick={reset}>
                <RotateCcw size={14} /> Analyze Another Document
              </button>
            </div>
          </div>
        )
      })()}
    </div>
  )
}
