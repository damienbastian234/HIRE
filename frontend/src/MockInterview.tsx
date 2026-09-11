import { useState, useRef } from 'react'
import {
  Mic, ChevronRight, RotateCcw, Trophy, AlertCircle,
  CheckCircle2, Lightbulb, BookOpen, Star, Clock, Target,
} from 'lucide-react'
import { api, parseError, InterviewQuestion, InterviewEvaluation } from './api'

// ─── Types ────────────────────────────────────────────────────────────────────
type Phase = 'setup' | 'loading' | 'interview' | 'feedback' | 'results'

interface AnsweredQuestion {
  question: InterviewQuestion
  answer: string
  evaluation: InterviewEvaluation
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const TYPE_LABEL: Record<string, string> = {
  behavioural: 'Behavioural',
  situational:  'Situational',
  technical:    'Technical',
  motivation:   'Motivation',
}
const TYPE_COLOR: Record<string, string> = {
  behavioural: '#7c5cbf',
  situational:  '#2d6a57',
  technical:    '#2060a8',
  motivation:   '#c07830',
}

function ScoreRing({ score }: { score: number }) {
  const pct = score / 10
  const r = 36, c = 2 * Math.PI * r
  const color = score >= 8 ? '#2d6a57' : score >= 6 ? '#c07830' : '#c05840'
  return (
    <svg width={88} height={88} viewBox="0 0 88 88">
      <circle cx={44} cy={44} r={r} fill="none" stroke="#e4e1d8" strokeWidth={8} />
      <circle
        cx={44} cy={44} r={r} fill="none"
        stroke={color} strokeWidth={8}
        strokeDasharray={c}
        strokeDashoffset={c * (1 - pct)}
        strokeLinecap="round"
        transform="rotate(-90 44 44)"
        style={{ transition: 'stroke-dashoffset 1s ease' }}
      />
      <text x={44} y={49} textAnchor="middle" fill={color} fontSize={22} fontWeight={700}>
        {score}
      </text>
    </svg>
  )
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function MockInterview() {
  // Setup state
  const [jobRole, setJobRole]         = useState('')
  const [difficulty, setDifficulty]   = useState('intermediate')
  const [numQ, setNumQ]               = useState(5)

  // Interview state
  const [phase, setPhase]             = useState<Phase>('setup')
  const [questions, setQuestions]     = useState<InterviewQuestion[]>([])
  const [current, setCurrent]         = useState(0)
  const [answer, setAnswer]           = useState('')
  const [answered, setAnswered]       = useState<AnsweredQuestion[]>([])
  const [evaluation, setEvaluation]   = useState<InterviewEvaluation | null>(null)
  const [error, setError]             = useState('')
  const [busy, setBusy]               = useState(false)
  const [showHint, setShowHint]       = useState(false)
  const [elapsed, setElapsed]         = useState(0)
  const timerRef                      = useRef<ReturnType<typeof setInterval> | null>(null)
  const textRef                       = useRef<HTMLTextAreaElement>(null)

  const startTimer = () => {
    setElapsed(0)
    timerRef.current = setInterval(() => setElapsed(s => s + 1), 1000)
  }
  const stopTimer = () => {
    if (timerRef.current) { clearInterval(timerRef.current); timerRef.current = null }
  }
  const fmtTime = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

  // ── Start interview ────────────────────────────────────────────────────────
  const startInterview = async () => {
    if (!jobRole.trim()) { setError('Please enter a job role.'); return }
    setError('')
    setPhase('loading')
    try {
      const res = await api.generateInterviewQuestions({
        job_role: jobRole.trim(),
        difficulty,
        num_questions: numQ,
      })
      setQuestions(res.questions)
      setCurrent(0)
      setAnswered([])
      setAnswer('')
      setShowHint(false)
      setPhase('interview')
      startTimer()
      setTimeout(() => textRef.current?.focus(), 100)
    } catch (err) {
      setError(parseError(err))
      setPhase('setup')
    }
  }

  // ── Submit answer ──────────────────────────────────────────────────────────
  const submitAnswer = async () => {
    if (!answer.trim()) { setError('Please type your answer before submitting.'); return }
    setError('')
    setBusy(true)
    stopTimer()
    try {
      const q = questions[current]
      const res = await api.evaluateAnswer({
        job_role: jobRole,
        question_id: q.id,
        question_text: q.question,
        question_type: q.type,
        answer: answer.trim(),
      })
      setEvaluation(res.evaluation)
      setAnswered(prev => [...prev, { question: q, answer: answer.trim(), evaluation: res.evaluation }])
      setPhase('feedback')
    } catch (err) {
      setError(parseError(err))
    } finally {
      setBusy(false)
    }
  }

  // ── Next question ──────────────────────────────────────────────────────────
  const nextQuestion = () => {
    const next = current + 1
    if (next >= questions.length) {
      setPhase('results')
    } else {
      setCurrent(next)
      setAnswer('')
      setEvaluation(null)
      setShowHint(false)
      setError('')
      setPhase('interview')
      startTimer()
      setTimeout(() => textRef.current?.focus(), 100)
    }
  }

  // ── Restart ────────────────────────────────────────────────────────────────
  const restart = () => {
    stopTimer()
    setPhase('setup')
    setQuestions([])
    setCurrent(0)
    setAnswered([])
    setAnswer('')
    setEvaluation(null)
    setError('')
    setShowHint(false)
  }

  // ── Average score ──────────────────────────────────────────────────────────
  const avgScore = answered.length
    ? Math.round(answered.reduce((s, a) => s + a.evaluation.score, 0) / answered.length * 10) / 10
    : 0

  const overallVerdict = avgScore >= 8
    ? { text: 'Outstanding performance!', icon: '🏆', color: '#2d6a57' }
    : avgScore >= 6
    ? { text: 'Good performance — some areas to sharpen.', icon: '👍', color: '#c07830' }
    : { text: 'Keep practising — you\'re on the right track.', icon: '💪', color: '#c05840' }

  // ═══════════════════════════════════════════════════════════════════════════
  // ── SETUP ──────────────────────────────────────────────────────────────────
  if (phase === 'setup') return (
    <div className="mi-setup">
      <div className="mi-setup-card">
        <div className="mi-setup-icon"><Mic size={28} /></div>
        <h2 className="mi-setup-title">AI Mock Interview</h2>
        <p className="mi-setup-sub">
          Practice with AI-generated questions tailored to your target role.
          Get instant feedback, scores, and model answers after each response.
        </p>

        <div className="mi-setup-form">
          <label className="mi-label">
            Target job role
            <input
              className="mi-input"
              placeholder="e.g. Software Engineer, Product Manager, Data Analyst…"
              value={jobRole}
              onChange={e => setJobRole(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && startInterview()}
            />
          </label>

          <label className="mi-label">
            Difficulty
            <div className="mi-pill-group">
              {['beginner', 'intermediate', 'advanced'].map(d => (
                <button
                  key={d}
                  className={`mi-pill ${difficulty === d ? 'active' : ''}`}
                  onClick={() => setDifficulty(d)}
                >
                  {d.charAt(0).toUpperCase() + d.slice(1)}
                </button>
              ))}
            </div>
          </label>

          <label className="mi-label">
            Number of questions
            <div className="mi-pill-group">
              {[3, 5, 7, 10].map(n => (
                <button
                  key={n}
                  className={`mi-pill ${numQ === n ? 'active' : ''}`}
                  onClick={() => setNumQ(n)}
                >
                  {n}
                </button>
              ))}
            </div>
          </label>

          {error && <p className="error-text" role="alert">{error}</p>}

          <button className="primary-button mi-start-btn" onClick={startInterview}>
            Start Interview <ChevronRight size={17} />
          </button>
        </div>

        <div className="mi-features">
          <div className="mi-feature"><Target size={15} /> Role-specific questions</div>
          <div className="mi-feature"><Star size={15} /> Instant AI scoring 1–10</div>
          <div className="mi-feature"><BookOpen size={15} /> Model answers</div>
          <div className="mi-feature"><Lightbulb size={15} /> Coaching tips</div>
        </div>
      </div>
    </div>
  )

  // ── LOADING ────────────────────────────────────────────────────────────────
  if (phase === 'loading') return (
    <div className="mi-loading">
      <div className="mi-loading-spinner" />
      <p className="mi-loading-text">Generating your personalised interview…</p>
      <p className="mi-loading-sub">Crafting {numQ} questions for <strong>{jobRole}</strong></p>
    </div>
  )

  const q = questions[current]

  // ── INTERVIEW ──────────────────────────────────────────────────────────────
  if (phase === 'interview') return (
    <div className="mi-interview">
      {/* Progress bar */}
      <div className="mi-progress-row">
        <span className="mi-progress-label">Question {current + 1} of {questions.length}</span>
        <div className="mi-timer"><Clock size={13} /> {fmtTime(elapsed)}</div>
      </div>
      <div className="mi-progress-track">
        <div
          className="mi-progress-fill"
          style={{ width: `${((current) / questions.length) * 100}%` }}
        />
      </div>

      {/* Question card */}
      <div className="mi-question-card">
        <div className="mi-q-meta">
          <span
            className="mi-q-type-badge"
            style={{ background: TYPE_COLOR[q.type] + '18', color: TYPE_COLOR[q.type] }}
          >
            {TYPE_LABEL[q.type]}
          </span>
          <span className="mi-q-role">{jobRole}</span>
        </div>
        <p className="mi-question-text">{q.question}</p>

        {showHint && (
          <div className="mi-hint-box">
            <Lightbulb size={14} /> {q.hint}
          </div>
        )}
        {!showHint && (
          <button className="mi-hint-btn" onClick={() => setShowHint(true)}>
            <Lightbulb size={13} /> Show hint
          </button>
        )}
      </div>

      {/* Answer area */}
      <div className="mi-answer-area">
        <label className="mi-label">Your answer</label>
        <textarea
          ref={textRef}
          className="mi-textarea"
          placeholder="Type your answer here. Take your time — there's no rush. Use the STAR method for behavioural questions (Situation, Task, Action, Result)."
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          rows={6}
        />
        <div className="mi-answer-footer">
          <span className="mi-word-count">{answer.trim().split(/\s+/).filter(Boolean).length} words</span>
          {error && <p className="error-text" role="alert" style={{ margin: 0 }}>{error}</p>}
          <button
            className="primary-button"
            onClick={submitAnswer}
            disabled={busy || !answer.trim()}
          >
            {busy ? 'Evaluating…' : 'Submit Answer'} <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  )

  // ── FEEDBACK ───────────────────────────────────────────────────────────────
  if (phase === 'feedback' && evaluation) return (
    <div className="mi-feedback">
      <div className="mi-fb-header">
        <div>
          <p className="mi-fb-q-label">Question {current + 1} of {questions.length}</p>
          <p className="mi-fb-q-text">{q.question}</p>
        </div>
        <ScoreRing score={evaluation.score} />
      </div>

      <p className="mi-fb-verdict">{evaluation.verdict}</p>

      <div className="mi-fb-grid">
        {/* Strengths */}
        <div className="mi-fb-box mi-fb-strengths">
          <p className="mi-fb-box-title"><CheckCircle2 size={15} /> What you did well</p>
          <ul>
            {evaluation.strengths.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>

        {/* Improvements */}
        <div className="mi-fb-box mi-fb-improve">
          <p className="mi-fb-box-title"><AlertCircle size={15} /> Areas to improve</p>
          <ul>
            {evaluation.improvements.map((s, i) => <li key={i}>{s}</li>)}
          </ul>
        </div>
      </div>

      {/* Model answer */}
      <div className="mi-fb-model">
        <p className="mi-fb-box-title"><Star size={15} /> Model answer</p>
        <p>{evaluation.model_answer}</p>
      </div>

      {/* Coaching tip */}
      <div className="mi-fb-tip">
        <Lightbulb size={15} />
        <p><strong>Coach tip:</strong> {evaluation.tip}</p>
      </div>

      {/* Your answer */}
      <details className="mi-fb-your-answer">
        <summary>View your answer</summary>
        <p>{answered[answered.length - 1]?.answer}</p>
      </details>

      <div className="mi-fb-actions">
        <button className="secondary-button" onClick={restart}>
          <RotateCcw size={14} /> Restart
        </button>
        <button className="primary-button" onClick={nextQuestion}>
          {current + 1 >= questions.length ? 'See Results' : 'Next Question'}
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )

  // ── RESULTS ────────────────────────────────────────────────────────────────
  if (phase === 'results') return (
    <div className="mi-results">
      <div className="mi-results-hero">
        <Trophy size={36} className="mi-results-trophy" />
        <h2>Interview Complete!</h2>
        <p className="mi-results-role">{jobRole} · {difficulty}</p>
        <ScoreRing score={avgScore} />
        <p className="mi-results-avg">Average score: <strong>{avgScore} / 10</strong></p>
        <p style={{ color: overallVerdict.color, fontWeight: 600 }}>
          {overallVerdict.icon} {overallVerdict.text}
        </p>
      </div>

      {/* Per-question breakdown */}
      <div className="mi-results-breakdown">
        <h3>Question Breakdown</h3>
        {answered.map((item, i) => (
          <details key={i} className="mi-result-item">
            <summary>
              <span className="mi-ri-num">Q{i + 1}</span>
              <span className="mi-ri-q">{item.question.question}</span>
              <span
                className="mi-ri-score"
                style={{ color: item.evaluation.score >= 7 ? '#2d6a57' : item.evaluation.score >= 5 ? '#c07830' : '#c05840' }}
              >
                {item.evaluation.score}/10
              </span>
            </summary>
            <div className="mi-ri-detail">
              <p><strong>Your answer:</strong> {item.answer}</p>
              <p><strong>Verdict:</strong> {item.evaluation.verdict}</p>
              <p className="mi-ri-model"><strong>Model answer:</strong> {item.evaluation.model_answer}</p>
            </div>
          </details>
        ))}
      </div>

      <div className="mi-results-actions">
        <button className="primary-button" onClick={restart}>
          <RotateCcw size={15} /> Practice Again
        </button>
      </div>
    </div>
  )

  return null
}
