import { useState } from 'react'
import { Check } from 'lucide-react'

// Apply compact mode immediately to document body
function applyCompact(value: boolean) {
  document.body.setAttribute('data-compact', String(value))
  localStorage.setItem('hire-compact-mode', String(value))
}

export default function SettingsView() {
  const [emailUpdates,    setEmailUpdates]    = useState(() => localStorage.getItem('hire-email-updates') !== 'false')
  const [compact,         setCompact]         = useState(() => localStorage.getItem('hire-compact-mode') === 'true')
  const [analysisNotifs,  setAnalysisNotifs]  = useState(() => localStorage.getItem('hire-analysis-notifs') !== 'false')
  const [saved,           setSaved]           = useState(false)

  const toggle = (key: string, setter: (v: boolean) => void, current: boolean, extra?: (v: boolean) => void) => {
    const next = !current
    setter(next)
    localStorage.setItem(key, String(next))
    extra?.(next)
  }

  const save = () => {
    localStorage.setItem('hire-email-updates',    String(emailUpdates))
    localStorage.setItem('hire-compact-mode',     String(compact))
    localStorage.setItem('hire-analysis-notifs',  String(analysisNotifs))
    applyCompact(compact)
    setSaved(true)
    setTimeout(() => setSaved(false), 2200)
  }

  return (
    <div className="settings-layout">
      <section className="panel settings-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PREFERENCES</p>
            <h3>Make the workspace yours</h3>
          </div>
          {saved && <span className="saved"><Check size={15} /> Saved</span>}
        </div>

        {/* Email updates */}
        <div className="setting-row">
          <div>
            <strong>Email updates</strong>
            <p>Receive important application and analysis updates via email.</p>
            <span className="setting-scope">Local only — browser preference</span>
          </div>
          <button
            type="button"
            className={emailUpdates ? 'switch on' : 'switch'}
            onClick={() => toggle('hire-email-updates', setEmailUpdates, emailUpdates)}
            aria-pressed={emailUpdates}
            aria-label="Toggle email updates"
          >
            <span />
          </button>
        </div>

        {/* Analysis notifications */}
        <div className="setting-row">
          <div>
            <strong>Analysis notifications</strong>
            <p>Get notified when your resume analysis is complete.</p>
            <span className="setting-scope">Local only — browser preference</span>
          </div>
          <button
            type="button"
            className={analysisNotifs ? 'switch on' : 'switch'}
            onClick={() => toggle('hire-analysis-notifs', setAnalysisNotifs, analysisNotifs)}
            aria-pressed={analysisNotifs}
            aria-label="Toggle analysis notifications"
          >
            <span />
          </button>
        </div>

        {/* Compact workspace — applied immediately */}
        <div className="setting-row">
          <div>
            <strong>Compact workspace</strong>
            <p>Use tighter spacing to see more information at once. Applied immediately.</p>
            <span className="setting-scope">Local only — browser preference</span>
          </div>
          <button
            type="button"
            className={compact ? 'switch on' : 'switch'}
            onClick={() => {
              const next = !compact
              setCompact(next)
              applyCompact(next)  // immediate effect
            }}
            aria-pressed={compact}
            aria-label="Toggle compact workspace"
            id="toggle-compact"
          >
            <span />
          </button>
        </div>

        {/* API connection — read-only info */}
        <div className="setting-row">
          <div>
            <strong>Backend connection</strong>
            <p>Connected to the H.I.R.E. FastAPI backend at port 8000.</p>
            <span className="setting-scope">Live connection status shown in the top bar</span>
          </div>
          <span className="connection-label">
            <span className="status-dot" /> Active
          </span>
        </div>

        <div className="form-footer">
          <span>All preferences are saved locally in this browser only</span>
          <button className="primary-button" onClick={save} type="button">
            Save settings <Check size={16} />
          </button>
        </div>
      </section>
    </div>
  )
}
