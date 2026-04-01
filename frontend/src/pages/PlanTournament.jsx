import React, { useState } from 'react'
import { tournamentState as initial } from '../data/tournament'

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
  { key: 'catering',             label: 'Catering',           required: false,                       fmt: v => v || '—' },
  { key: 'budget',               label: 'Budget',             required: false,                       fmt: v => v ? `$${v}` : '—' },
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

function LiveStatusPanel({ tournament, readyForGeneration, generationDone, generating, onGenerate }) {
  const requiredFilled = STATUS_ROWS.filter(r => isRequired(r, tournament) && isFilled(r.key, tournament)).length
  const totalRequired = STATUS_ROWS.filter(r => isRequired(r, tournament)).length

  return (
    <div style={{
      width: 300,
      flexShrink: 0,
      background: '#f0fdf4',
      border: '1px solid #86efac',
      borderRadius: 10,
      padding: '16px 18px',
      alignSelf: 'flex-start',
      position: 'sticky',
      top: 24,
    }}>
      <div style={{ fontWeight: 700, color: '#166534', fontSize: 15, marginBottom: 4 }}>
        Tournament Details
      </div>
      <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 12 }}>
        {requiredFilled} / {totalRequired} required fields collected
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
        <tbody>
          {STATUS_ROWS.map(row => {
            const filled = isFilled(row.key, tournament)
            const display = filled ? row.fmt(tournament[row.key]) : null
            return (
              <tr key={row.key} style={{ borderBottom: '1px solid #d1fae5' }}>
                <td style={{ padding: '5px 4px', color: '#6b7280', width: '50%', fontWeight: 600, verticalAlign: 'top' }}>
                  {row.label}{isRequired(row, tournament) && !filled ? ' *' : ''}
                </td>
                <td style={{ padding: '5px 4px', color: display ? '#111827' : '#9ca3af', fontStyle: display ? 'normal' : 'italic' }}>
                  {display || '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {readyForGeneration && (
        <div style={{ marginTop: 14 }}>
          <button
            onClick={onGenerate}
            disabled={generating}
            style={{
              background: '#16a34a',
              color: '#fff',
              border: 'none',
              padding: '10px 20px',
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 14,
              cursor: generating ? 'not-allowed' : 'pointer',
              width: '100%',
            }}
          >
            {generating ? 'Generating…' : generationDone ? 'Regenerate Documents' : 'Generate Documents'}
          </button>
        </div>
      )}

      {!readyForGeneration && (
        <div style={{ marginTop: 12, fontSize: 12, color: '#6b7280' }}>
          * Required field
        </div>
      )}
    </div>
  )
}

export default function PlanTournament() {
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

  async function callGenerate(currentTournament) {
    try {
      const res = await fetch('http://localhost:8000/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tournament: currentTournament }),
      })
      const data = await res.json()
      localStorage.setItem('golfDraftSchedule', JSON.stringify(data.schedule))
      localStorage.setItem('golfDraftBrochure', JSON.stringify(data.brochure))
      localStorage.setItem('golfDraftTournament', JSON.stringify(currentTournament))
      return data
    } catch {
      return null
    }
  }

  async function handleGenerate() {
    setGenerating(true)
    const isFirst = !generationDone
    const data = await callGenerate(tournament)
    setGenerating(false)
    if (data) {
      if (isFirst) {
        setGenerationDone(true)
        setPhase('refinement')
        window.open('/schedule-draft', '_blank')
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content:
              "Your schedule has opened in a new tab. Review it, then save it from that tab.\n\nYou can keep chatting here to make any changes — just tell me what you'd like to adjust and I'll update the documents automatically.",
          },
        ])
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Documents regenerated. Refresh the schedule tab to see the updated changes.',
          },
        ])
      }
    } else {
      setError('Generation failed — is the backend running?')
    }
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

      if (data.ready_for_generation) {
        setReadyForGeneration(true)
      }

      if (phase === 'refinement' && data.needs_regeneration && data.tournament) {
        await callGenerate(data.tournament)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: 'Documents updated. Refresh the schedule tab or reopen it to see the changes.',
          },
        ])
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
      <h1 style={{ margin: 0 }}>Plan Tournament</h1>
      <div className="muted small">Chat-driven tournament planner</div>
      <div style={{ height: 16 }} />

      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
        {/* Chat column */}
        <div className="card" style={{ flex: 1, minWidth: 0 }}>
          <h2 style={{ marginTop: 0 }}>Chat</h2>

          {/* Message thread */}
          <div
            style={{
              border: '1px solid #ddd',
              borderRadius: 8,
              padding: 12,
              minHeight: 400,
              maxHeight: 520,
              overflowY: 'auto',
              background: '#fafafa',
            }}
          >
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 10,
                }}
              >
                <div
                  style={{
                    background: msg.role === 'user' ? '#dbeafe' : '#e5e7eb',
                    padding: 10,
                    borderRadius: 10,
                    maxWidth: '78%',
                    whiteSpace: 'pre-wrap',
                    fontSize: 14,
                  }}
                >
                  <strong style={{ fontSize: 12, opacity: 0.7 }}>
                    {msg.role === 'user' ? 'You' : 'Assistant'}
                  </strong>
                  <div style={{ marginTop: 3 }}>{msg.content}</div>
                  {msg.sources?.length > 0 && (
                    <div
                      className="small muted"
                      style={{ marginTop: 8 }}
                    >
                      Sources: {msg.sources.map((source) => source.title).join(' • ')}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="small muted" style={{ padding: 8 }}>Thinking…</div>
            )}
          </div>

          {/* Phase badge */}
          {phase === 'refinement' && (
            <div style={{
              marginTop: 8,
              fontSize: 12,
              color: '#6366f1',
              fontWeight: 600,
            }}>
              Refinement mode — keep chatting to adjust the schedule or tournament details.
            </div>
          )}

          {/* Input form */}
          <form onSubmit={sendMessage} style={{ marginTop: 12 }}>
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
              style={{
                width: '100%',
                padding: 10,
                borderRadius: 8,
                border: '1px solid #ccc',
                boxSizing: 'border-box',
                resize: 'vertical',
                fontSize: 14,
              }}
            />

            {error && <div style={{ color: 'red', fontSize: 13, marginTop: 4 }}>{error}</div>}

            <div style={{ textAlign: 'right', marginTop: 8 }}>
              <button className="button" disabled={loading}>
                Send
              </button>
            </div>
          </form>
        </div>

        {/* Live status panel */}
        <LiveStatusPanel
          tournament={tournament}
          readyForGeneration={readyForGeneration}
          generationDone={generationDone}
          generating={generating}
          onGenerate={handleGenerate}
        />
      </div>
    </div>
  )
}
