import React, { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { tournamentState as initial } from '../data/tournament'
import Icon from '../components/Icon'
import Modal from '../components/Modal'

const STATUS_ROWS = [
  { key: 'name',                 label: 'Tournament Name',    required: true,                        fmt: v => v },
  { key: 'date',                 label: 'Start Date',         required: true,                        fmt: v => v },
  { key: 'venue',                label: 'Venue',              required: true,                        fmt: v => v },
  { key: 'format',               label: 'Format',             required: true,                        fmt: v => v },
  { key: 'numberOfDays',         label: 'Number of Days',     required: true,                        fmt: v => `${v} day${Number(v) !== 1 ? 's' : ''}` },
  { key: 'playerCount',          label: 'Players',            required: true,                        fmt: v => String(v) },
  { key: 'eventType',            label: 'Event Type',         required: true,                        fmt: v => v },
  { key: 'teamSize',             label: 'Team Size',          required: t => t.eventType === 'team', fmt: v => `${v} per team` },
  { key: 'registrationDeadline', label: 'Reg. Deadline',      required: true,                        fmt: v => v },
  { key: 'teeTimeStart',         label: 'First Tee Time',     required: true,                        fmt: v => v },
  { key: 'teeTimeInterval',      label: 'Tee Interval (min)', required: true,                        fmt: v => `${v} min` },
  { key: 'entryFee',             label: 'Entry Fee',          required: false,                       fmt: v => v ? `$${v}` : '—' },
  { key: 'description',          label: 'Description',        required: false,                       fmt: v => v || '—' },
  { key: 'sponsors',             label: 'Sponsors',           required: false,                       fmt: v => Array.isArray(v) ? v.join(', ') || '—' : (v || '—') },
  { key: 'cateringEnabled',      label: 'Catering Enabled',   required: false,                       fmt: v => v ? 'Yes' : 'No' },
  { key: 'cateringBudget',       label: 'Catering Budget',    required: t => !!t.cateringEnabled,    fmt: v => v ? `$${v}` : '—' },
  { key: 'cateringItems',        label: 'Catering Items',     required: false,                       fmt: v => v || '—' },
  { key: 'cateringServingTime',  label: 'Serving Time',       required: false,                       fmt: v => v || '—' },
  { key: 'cateringDietaryNotes', label: 'Dietary Notes',      required: false,                       fmt: v => v || '—' },
  { key: 'accessibility',        label: 'Accessibility',      required: false,                       fmt: v => v || '—' },
  { key: 'notes',                label: 'Notes',              required: false,                       fmt: v => v || '—' },
]

function isRequired(row, tournament) {
  return typeof row.required === 'function' ? row.required(tournament) : !!row.required
}

function isFilled(key, tournament) {
  const v = tournament[key]
  if (key === 'playerCount' || key === 'numberOfDays' || key === 'teamSize') return Number(v) > 0
  if (Array.isArray(v)) return v.length > 0
  return !!v
}

function getRagIndicator(status) {
  const docCount = Number(status?.document_count || 0)
  const chunkCount = Number(status?.chunk_count || 0)
  const sourceLabel = status?.source_kind === 'bundled' ? 'bundled library' : 'corpus'

  if (status?.state === 'ready' && status?.ready) {
    return {
      label: 'Planning Library Ready',
      background: '#dcfce7',
      border: '#86efac',
      color: '#166534',
      detail: `${docCount} docs indexed into ${chunkCount} chunks from the ${sourceLabel}.`,
    }
  }

  if (status?.state === 'building') {
    return {
      label: 'Planning Library Indexing…',
      background: '#fef3c7',
      border: '#fcd34d',
      color: '#92400e',
      detail: docCount > 0
        ? `Preparing embeddings for ${docCount} docs so retrieval is ready before your first planning-heavy turn.`
        : 'Preparing the retrieval index in the background.',
    }
  }

  if (status?.state === 'error') {
    return {
      label: 'Planning Library Unavailable',
      background: '#fee2e2',
      border: '#fca5a5',
      color: '#991b1b',
      detail: status?.last_error || 'The backend could not finish the retrieval warmup.',
    }
  }

  return {
    label: 'Planning Library Starting…',
    background: '#e0f2fe',
    border: '#7dd3fc',
    color: '#075985',
    detail: 'Waiting for the backend to begin indexing the planning corpus.',
  }
}

function getSourceContent(source) {
  return (source.content || source.preview || 'No source text available.').trim()
}

function formatSourceLabel(source) {
  if (typeof source.score === 'number') {
    return `${source.title} · ${source.score.toFixed(3)}`
  }
  return source.title
}

function escapeHtml(value) {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function openSourceInNewTab(source) {
  const content = escapeHtml(getSourceContent(source))
  const title = escapeHtml(source.title || 'Source Viewer')
  const chunkId = escapeHtml(source.chunk_id || 'n/a')
  const score = typeof source.score === 'number' ? source.score.toFixed(3) : 'n/a'
  const newWindow = window.open('', '_blank', 'noopener,noreferrer')

  if (!newWindow) return

  newWindow.document.write(`<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>${title}</title>
    <style>
      body {
        margin: 0;
        padding: 24px;
        font-family: Georgia, "Times New Roman", serif;
        background: #f8fafc;
        color: #0f172a;
      }
      .meta {
        margin-bottom: 16px;
        font: 600 13px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        color: #475569;
      }
      .chunk {
        background: white;
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 20px;
        white-space: pre-wrap;
        line-height: 1.6;
        font-size: 16px;
      }
    </style>
  </head>
  <body>
    <h1>${title}</h1>
    <div class="meta">Chunk: ${chunkId} | Similarity: ${score}</div>
    <div class="chunk">${content}</div>
  </body>
</html>`)
  newWindow.document.close()
}

function shouldFetchFullChunk(source) {
  if (!source?.chunk_id) return false
  if (source.chunk_id.startsWith('weather_')) return false
  return true
}

function SourceViewerModal({ source, resolvedContent, loading, error, onClose }) {
  if (!source) return null

  const modalContent = (resolvedContent || getSourceContent(source)).trim()

  return (
    <Modal
      title={source.title}
      subtitle={`Chunk: ${source.chunk_id || 'n/a'}${typeof source.score === 'number' ? ` · Similarity ${source.score.toFixed(3)}` : ''}`}
      onClose={onClose}
      maxWidth={860}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => openSourceInNewTab({ ...source, content: modalContent })}>
            <Icon name="external" size={15} /> Open in New Tab
          </button>
          <button type="button" className="btn btn-primary btn-sm" onClick={onClose}>Close</button>
        </>
      }
    >
      <div style={{
        whiteSpace: 'pre-wrap',
        lineHeight: 1.7,
        fontSize: 15,
        color: 'var(--slate)',
        fontFamily: 'var(--font-serif)',
      }}>
        {loading ? 'Loading full chunk…' : error ? error : modalContent}
      </div>
    </Modal>
  )
}

function LiveStatusPanel({ tournament, readyForGeneration, generationDone, generating, onGenerate, ragStatus }) {
  const requiredFilled = STATUS_ROWS.filter(r => isRequired(r, tournament) && isFilled(r.key, tournament)).length
  const totalRequired = STATUS_ROWS.filter(r => isRequired(r, tournament)).length
  const ragIndicator = getRagIndicator(ragStatus)

  const pct = totalRequired > 0 ? Math.round((requiredFilled / totalRequired) * 100) : 0

  return (
    <div className="plan-panel card" style={{ width: 320, flexShrink: 0, alignSelf: 'flex-start', position: 'sticky', top: 24, padding: 0, overflow: 'hidden' }}>
      <div style={{ padding: '16px 18px 14px', borderBottom: '1px solid var(--line-soft)' }}>
        <div className="card-title" style={{ fontSize: 17 }}>
          <Icon name="flag" size={18} style={{ color: 'var(--fairway)' }} /> Tournament Details
        </div>
        <div style={{ fontSize: 12, color: 'var(--muted)', margin: '8px 0 8px' }}>
          {requiredFilled} / {totalRequired} required fields collected
        </div>
        <div style={{ height: 7, borderRadius: 999, background: 'var(--line-soft)', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, borderRadius: 999, background: 'linear-gradient(90deg, var(--fairway), var(--champagne))', transition: 'width 0.4s var(--ease)' }} />
        </div>
      </div>

      <div style={{ padding: '14px 18px' }}>
        <div style={{
          marginBottom: 14,
          padding: '10px 12px',
          borderRadius: 'var(--r-sm)',
          background: ragIndicator.background,
          border: `1px solid ${ragIndicator.border}`,
        }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: ragIndicator.color }}>
            {ragIndicator.label}
          </div>
          <div style={{ fontSize: 11.5, color: 'var(--slate)', marginTop: 4, lineHeight: 1.4 }}>
            {ragIndicator.detail}
          </div>
        </div>

        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <tbody>
            {STATUS_ROWS.map(row => {
              const filled = isFilled(row.key, tournament)
              const display = filled ? row.fmt(tournament[row.key]) : null
              return (
                <tr key={row.key} style={{ borderBottom: '1px solid var(--line-soft)' }}>
                  <td style={{ padding: '6px 4px', color: 'var(--muted)', width: '48%', fontWeight: 600, verticalAlign: 'top' }}>
                    {row.label}{isRequired(row, tournament) && !filled ? ' *' : ''}
                  </td>
                  <td style={{ padding: '6px 4px', color: display ? 'var(--ink)' : 'var(--faint)', fontStyle: display ? 'normal' : 'italic' }}>
                    {display || '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {readyForGeneration ? (
          <button onClick={onGenerate} disabled={generating} className="btn btn-gold btn-block" style={{ marginTop: 16 }}>
            {generating ? <><span className="spinner" /> Saving…</> : (
              <><Icon name={generationDone ? 'check' : 'trophy'} size={16} /> {generationDone ? 'Update Tournament' : 'Save Tournament'}</>
            )}
          </button>
        ) : (
          <div style={{ marginTop: 12, fontSize: 12, color: 'var(--muted)' }}>
            <span style={{ color: 'var(--champagne-dark)', fontWeight: 700 }}>*</span> Required field
          </div>
        )}
      </div>
    </div>
  )
}

export default function PlanTournament() {
  const navigate = useNavigate()
  const { authHeaders } = useAuth()
  const messagesContainerRef = useRef(null)
  const [tournament, setTournament] = useState(initial)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I can help you plan your golf tournament. Tell me about your event — what's the tournament name and when is it?",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [phase, setPhase] = useState('planning')
  const [readyForGeneration, setReadyForGeneration] = useState(false)
  const [generationDone, setGenerationDone] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [savedReservationId, setSavedReservationId] = useState(null)
  const [workingMemory, setWorkingMemory] = useState({})
  const [activeSource, setActiveSource] = useState(null)
  const [activeSourceContent, setActiveSourceContent] = useState('')
  const [activeSourceLoading, setActiveSourceLoading] = useState(false)
  const [activeSourceError, setActiveSourceError] = useState('')
  const [ragStatus, setRagStatus] = useState({
    state: 'idle',
    ready: false,
    document_count: 0,
    chunk_count: 0,
    last_error: '',
    source_kind: 'unknown',
  })

  useEffect(() => {
    let cancelled = false
    let timerId = null

    async function pollRagStatus() {
      let nextDelay = 5000
      try {
        const response = await fetch('http://localhost:8000/rag/status')
        if (!response.ok) {
          throw new Error(`Status ${response.status}`)
        }

        const data = await response.json()
        if (cancelled) return

        setRagStatus(data)
        nextDelay = data.ready ? 30000 : 2000
      } catch {
        if (cancelled) return

        setRagStatus((prev) => ({
          ...prev,
          state: 'error',
          ready: false,
          last_error: 'Unable to reach the backend RAG status endpoint.',
        }))
      } finally {
        if (!cancelled) {
          timerId = window.setTimeout(pollRagStatus, nextDelay)
        }
      }
    }

    pollRagStatus()

    return () => {
      cancelled = true
      if (timerId !== null) {
        window.clearTimeout(timerId)
      }
    }
  }, [])

  useEffect(() => {
    function handleEscape(event) {
      if (event.key === 'Escape') {
        setActiveSource(null)
      }
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }, [messages])

  // Auto-scroll to bottom when user is typing
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }, [input])

  useEffect(() => {
    let cancelled = false

    async function loadFullChunk() {
      if (!activeSource) {
        setActiveSourceContent('')
        setActiveSourceLoading(false)
        setActiveSourceError('')
        return
      }

      setActiveSourceContent(getSourceContent(activeSource))
      setActiveSourceError('')

      if (!shouldFetchFullChunk(activeSource)) {
        setActiveSourceLoading(false)
        return
      }

      setActiveSourceLoading(true)
      try {
        const response = await fetch(`http://localhost:8000/rag/chunk/${encodeURIComponent(activeSource.chunk_id)}`)
        if (!response.ok) {
          throw new Error(`Status ${response.status}`)
        }

        const data = await response.json()
        if (cancelled) return

        setActiveSourceContent((data.text || '').trim() || getSourceContent(activeSource))
      } catch {
        if (cancelled) return

        setActiveSourceError('Unable to load the full chunk from the backend.')
      } finally {
        if (!cancelled) {
          setActiveSourceLoading(false)
        }
      }
    }

    loadFullChunk()

    return () => {
      cancelled = true
    }
  }, [activeSource])

  async function callGenerate(currentTournament) {
    try {
      const res = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tournament: currentTournament }),
      })
      return await res.json()
    } catch {
      return null
    }
  }

  async function saveToReservations(currentTournament, genData, existingId) {
    const resId = existingId || crypto.randomUUID()
    let tournament_id = null
    let registration_token = ''
    try {
      const saveRes = await fetch('http://localhost:8000/tournaments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify({
          tournament: currentTournament,
          schedule: genData.schedule,
          brochure: genData.brochure,
        }),
      })
      if (saveRes.ok) {
        const saveData = await saveRes.json()
        tournament_id = saveData.tournament_id
        registration_token = saveData.registration_token
      }
    } catch { /* store locally even if DB save fails */ }

    const entry = {
      id: resId,
      savedAt: new Date().toISOString(),
      tournament_id,
      registration_token,
      tournament: currentTournament,
      schedule: genData.schedule,
      brochure: genData.brochure,
      rule_sheet: genData.rule_sheet ?? null,
      fnb_summary: genData.fnb_summary ?? null,
    }
    const stored = JSON.parse(localStorage.getItem('savedReservations') || '[]')
    const idx = stored.findIndex(r => r.id === resId)
    if (idx >= 0) {
      stored[idx] = entry
    } else {
      stored.push(entry)
    }
    localStorage.setItem('savedReservations', JSON.stringify(stored))
    return resId
  }

  async function handleGenerate() {
    setGenerating(true)
    const isFirst = !generationDone
    const genData = await callGenerate(tournament)
    if (!genData) {
      setGenerating(false)
      setError('Generation failed — is the backend running?')
      return
    }
    const resId = await saveToReservations(tournament, genData, isFirst ? null : savedReservationId)
    setGenerating(false)
    if (isFirst) {
      setSavedReservationId(resId)
      setGenerationDone(true)
      setPhase('refinement')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content:
            "Your tournament has been saved to Reservations. You can view all documents there, send invites, and manage the event.\n\nYou can still chat here to make any changes — just tell me what you'd like to adjust.",
        },
      ])
    } else {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Your tournament has been updated in Reservations.',
        },
      ])
    }
    navigate('/reservations')
  }

  async function sendMessage(e) {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || loading) return

    const userMessage = { role: 'user', content: trimmed }
    const historyForRequest = messages.map((m) => ({ role: m.role, content: m.content }))

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setError('')
    setLoading(true)

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: trimmed,
          tournament,
          history: historyForRequest,
          phase,
          working_memory: workingMemory,
        }),
      })

      const data = await response.json()

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.message || 'No response',
          sources: data.sources || [],
        },
      ])

      if (data.tournament) {
        setTournament(data.tournament)
      }

      if (data.working_memory) {
        setWorkingMemory(data.working_memory)
      }

      if (data.ready_for_generation) {
        setReadyForGeneration(true)
      }

      if (phase === 'refinement' && data.needs_regeneration && data.tournament) {
        const genData = await callGenerate(data.tournament)
        if (genData) {
          await saveToReservations(data.tournament, genData, savedReservationId)
          setMessages((prev) => [
            ...prev,
            {
              role: 'assistant',
              content: 'Documents updated. Your Reservations page has been refreshed with the latest changes.',
            },
          ])
        }
      }
    } catch {
      setError('Backend error — is the server running?')
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(e)
    }
  }

  return (
    <div>
      <div className="page-head">
        <div className="eyebrow">AI Assistant</div>
        <h1 className="page-title">Plan Tournament</h1>
        <div className="page-sub">Chat with the planner to build your event, then save it to Reservations</div>
      </div>

      <div className="plan-layout" style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        {/* Chat column */}
        <div className="card card-flush" style={{ flex: 1, minWidth: 0 }}>
          <div className="card-head">
            <div className="card-title">
              <Icon name="sparkle" size={18} style={{ color: 'var(--champagne-dark)' }} /> Planning Assistant
            </div>
            {phase === 'refinement' && <span className="badge badge-gold">Refinement mode</span>}
          </div>

          <div style={{ padding: 18 }}>
            {/* Message thread */}
            <div ref={messagesContainerRef} className="chat-thread">
              {messages.map((msg, i) => (
                <div key={i} className={`msg-row ${msg.role}`}>
                  <div className={`msg-avatar ${msg.role}`}>
                    {msg.role === 'user' ? 'You'.charAt(0) : <Icon name="flag" size={15} />}
                  </div>
                  <div className={`bubble ${msg.role}`}>
                    <div className="bubble-meta">{msg.role === 'user' ? 'You' : 'Assistant'}</div>
                    <div>{msg.content}</div>
                    {msg.sources?.length > 0 && (
                      <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'center' }}>
                        <span style={{ fontSize: 11, fontWeight: 600, opacity: 0.7 }}>Sources:</span>
                        {msg.sources.map((source, sourceIndex) => (
                          <button
                            key={`${source.chunk_id}-${sourceIndex}`}
                            type="button"
                            className="source-chip"
                            onClick={() => setActiveSource(source)}
                          >
                            {formatSourceLabel(source)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="msg-row assistant">
                  <div className="msg-avatar assistant"><Icon name="flag" size={15} /></div>
                  <div className="bubble assistant">
                    <span className="typing"><span /><span /><span /></span>
                  </div>
                </div>
              )}
            </div>

            {phase === 'refinement' && (
              <div className="notice notice-info" style={{ marginTop: 12 }}>
                <Icon name="sparkle" size={16} style={{ flexShrink: 0, marginTop: 1 }} />
                <span>Refinement mode — keep chatting to adjust the schedule or tournament details.</span>
              </div>
            )}

            {/* Input form */}
            <form onSubmit={sendMessage} style={{ marginTop: 14 }}>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  phase === 'refinement'
                    ? 'Request changes (e.g. "Move start time to 9 AM")…'
                    : 'Describe your tournament…'
                }
                rows={3}
                style={{ resize: 'vertical' }}
              />

              {error && <div className="notice notice-danger" style={{ marginTop: 8 }}>{error}</div>}

              <div style={{ textAlign: 'right', marginTop: 10 }}>
                <button className="btn btn-primary" disabled={loading}>
                  <Icon name="send" size={15} /> Send
                </button>
              </div>
            </form>
          </div>
        </div>

        {/* Live status panel */}
        <LiveStatusPanel
          tournament={tournament}
          readyForGeneration={readyForGeneration}
          generationDone={generationDone}
          generating={generating}
          onGenerate={handleGenerate}
          ragStatus={ragStatus}
        />
      </div>
      <SourceViewerModal
        source={activeSource}
        resolvedContent={activeSourceContent}
        loading={activeSourceLoading}
        error={activeSourceError}
        onClose={() => setActiveSource(null)}
      />
    </div>
  )
}
