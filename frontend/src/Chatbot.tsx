import { useEffect, useRef, useState, KeyboardEvent } from 'react'
import { Bot, Send, X, Minimize2, Maximize2, RotateCcw } from 'lucide-react'
import { api, parseError } from './api'

// ─── Types ────────────────────────────────────────────────────────────────────
interface Message {
  id: number
  role: 'user' | 'model'
  content: string
  error?: boolean
}

const WELCOME: Message = {
  id: 0,
  role: 'model',
  content:
    "Hi! I'm **ARIA**, your H.I.R.E. career assistant 👋\n\nI can help you with:\n- **Resume tips** & how to use Resume Intelligence\n- **Job search** strategies and interview prep\n- **Using H.I.R.E.** — features, navigation, troubleshooting\n- **Career advice** tailored to your goals\n\nWhat's on your mind?",
}

let _id = 1
const uid = () => _id++

// ─── Markdown renderer: bold, italic, headings, bullets, numbered lists ───────
function applyInline(text: string, key: number): React.ReactNode {
  // Bold **text** and italic *text*
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
  return (
    <span key={key}>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**')) return <strong key={i}>{p.slice(2, -2)}</strong>
        if (p.startsWith('*')  && p.endsWith('*'))  return <em key={i}>{p.slice(1, -1)}</em>
        return p
      })}
    </span>
  )
}

function renderContent(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0

  while (i < lines.length) {
    const line = lines[i]
    const trimmed = line.trim()

    if (!trimmed) {
      // blank line → small spacer
      elements.push(<div key={i} style={{ height: 6 }} />)
      i++; continue
    }

    // ## Heading
    if (trimmed.startsWith('## ')) {
      elements.push(
        <p key={i} className="chat-h2">{applyInline(trimmed.slice(3), i)}</p>
      )
      i++; continue
    }

    // ### Sub-heading
    if (trimmed.startsWith('### ')) {
      elements.push(
        <p key={i} className="chat-h3">{applyInline(trimmed.slice(4), i)}</p>
      )
      i++; continue
    }

    // --- horizontal rule
    if (trimmed === '---' || trimmed === '***') {
      elements.push(<hr key={i} className="chat-hr" />)
      i++; continue
    }

    // Bullet: - or •
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      elements.push(
        <div key={i} className="chat-bullet">
          <span className="chat-bullet-dot">•</span>
          <span>{applyInline(trimmed.slice(2), i)}</span>
        </div>
      )
      i++; continue
    }

    // Numbered list: 1. 2. etc.
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/)
    if (numMatch) {
      elements.push(
        <div key={i} className="chat-numbered">
          <span className="chat-num">{numMatch[1]}.</span>
          <span>{applyInline(numMatch[2], i)}</span>
        </div>
      )
      i++; continue
    }

    // Normal paragraph
    elements.push(<p key={i} className="chat-para">{applyInline(trimmed, i)}</p>)
    i++
  }
  return elements
}

// ─── Component ────────────────────────────────────────────────────────────────
export default function Chatbot() {
  const [open, setOpen]           = useState(false)
  const [expanded, setExpanded]   = useState(false)
  const [messages, setMessages]   = useState<Message[]>([WELCOME])
  const [input, setInput]         = useState('')
  const [busy, setBusy]           = useState(false)
  const [unread, setUnread]       = useState(0)
  const bottomRef                 = useRef<HTMLDivElement>(null)
  const inputRef                  = useRef<HTMLTextAreaElement>(null)

  // Scroll to bottom whenever messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-focus input when opened
  useEffect(() => {
    if (open) { inputRef.current?.focus(); setUnread(0) }
  }, [open])

  const openChat = () => { setOpen(true); setUnread(0) }

  const clearChat = () => {
    setMessages([WELCOME])
    setInput('')
    setBusy(false)
  }

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return

    const userMsg: Message = { id: uid(), role: 'user', content: text }
    const history = [...messages, userMsg]
    setMessages(history)
    setInput('')
    setBusy(true)

    // Add a typing indicator
    const typingId = uid()
    setMessages(prev => [...prev, { id: typingId, role: 'model', content: '…', error: false }])

    try {
      const { reply } = await api.chat(
        history.map(m => ({ role: m.role, content: m.content }))
      )
      setMessages(prev =>
        prev.map(m => m.id === typingId ? { ...m, content: reply } : m)
      )
      // Badge when chat is closed
      if (!open) setUnread(n => n + 1)
    } catch (err) {
      const errText = parseError(err)
      setMessages(prev =>
        prev.map(m =>
          m.id === typingId
            ? { ...m, content: errText, error: true }
            : m
        )
      )
    } finally {
      setBusy(false)
    }
  }

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  // ── Floating button ────────────────────────────────────────────────────────
  if (!open) return (
    <button className="chatbot-fab" onClick={openChat} aria-label="Open AI assistant">
      <Bot size={24} />
      {unread > 0 && <span className="chatbot-badge">{unread}</span>}
    </button>
  )

  // ── Chat window ────────────────────────────────────────────────────────────
  return (
    <div className={`chatbot-window ${expanded ? 'chatbot-expanded' : ''}`}>
      {/* Header */}
      <div className="chatbot-header">
        <div className="chatbot-header-info">
          <div className="chatbot-avatar"><Bot size={16} /></div>
          <div>
            <p className="chatbot-name">ARIA</p>
            <p className="chatbot-status">
              <span className="chatbot-dot" />
              AI Career Assistant
            </p>
          </div>
        </div>
        <div className="chatbot-header-actions">
          <button onClick={clearChat} title="Clear conversation" aria-label="Clear">
            <RotateCcw size={14} />
          </button>
          <button
            onClick={() => setExpanded(e => !e)}
            title={expanded ? 'Shrink' : 'Expand'}
            aria-label="Toggle size"
          >
            {expanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
          </button>
          <button onClick={() => setOpen(false)} title="Close" aria-label="Close chat">
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="chatbot-body">
        {messages.map(msg => (
          <div
            key={msg.id}
            className={`chat-msg ${msg.role === 'user' ? 'chat-user' : 'chat-ai'}${msg.error ? ' chat-error' : ''}`}
          >
            {msg.role === 'model' && (
              <div className="chat-ai-icon"><Bot size={13} /></div>
            )}
            <div className="chat-bubble">
              {msg.content === '…'
                ? <span className="chat-typing"><span /><span /><span /></span>
                : renderContent(msg.content)
              }
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chatbot-footer">
        <textarea
          ref={inputRef}
          className="chatbot-input"
          placeholder="Ask ARIA anything…"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          rows={1}
          disabled={busy}
        />
        <button
          className="chatbot-send"
          onClick={send}
          disabled={!input.trim() || busy}
          aria-label="Send"
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  )
}
