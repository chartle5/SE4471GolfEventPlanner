import React, { useState } from 'react'
import { tournamentState as initial } from '../data/tournament'

export default function PlanTournament() {
  const [tournament, setTournament] = useState(initial)
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        'Hi! I can help you plan your golf tournament. Tell me what you already know.',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function sendMessage(e) {
    e.preventDefault()

    const trimmed = input.trim()
    if (!trimmed || loading) return

    const userMessage = { role: 'user', content: trimmed }
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
        }),
      })

      const data = await response.json()

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.message || 'No response',
        },
      ])

      if (data.tournament) {
        setTournament(data.tournament)
      }

      // 🔥 OPTIONAL: reveal state if user asks
      if (trimmed.toLowerCase().includes('show state')) {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content:
              'Here is the current tournament state:\n\n' +
              JSON.stringify(data.tournament, null, 2),
          },
        ])
      }
    } catch (err) {
      setError('Backend error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Plan Tournament</h1>
      <div className="muted small">
        Chat-driven tournament planner
      </div>
      <button onClick={() => alert(JSON.stringify(tournament, null, 2))}>
        Debug State
      </button>
      <div style={{ height: 16 }} />

      <div className="card">
        <h2 style={{ marginTop: 0 }}>Chat</h2>

        <div
          style={{
            border: '1px solid #ddd',
            borderRadius: 8,
            padding: 12,
            minHeight: 400,
            maxHeight: 500,
            overflowY: 'auto',
            background: '#fafafa',
          }}
        >
          {messages.map((msg, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent:
                  msg.role === 'user' ? 'flex-end' : 'flex-start',
                marginBottom: 10,
              }}
            >
              <div
                style={{
                  background:
                    msg.role === 'user' ? '#dbeafe' : '#e5e7eb',
                  padding: 10,
                  borderRadius: 10,
                  maxWidth: '75%',
                  whiteSpace: 'pre-wrap',
                }}
              >
                <strong>
                  {msg.role === 'user' ? 'You' : 'Assistant'}
                </strong>
                <div>{msg.content}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="small muted">Thinking...</div>
          )}
        </div>

        <form onSubmit={sendMessage} style={{ marginTop: 12 }}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Describe your tournament..."
            rows={3}
            style={{
              width: '100%',
              padding: 10,
              borderRadius: 8,
              border: '1px solid #ccc',
            }}
          />

          {error && (
            <div style={{ color: 'red' }}>{error}</div>
          )}

          <div style={{ textAlign: 'right', marginTop: 10 }}>
            <button className="button" disabled={loading}>
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}