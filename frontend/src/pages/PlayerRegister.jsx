import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'

export default function PlayerRegister() {
  const { token } = useParams()
  const [info, setInfo]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName]   = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null) // { ok, message, slot }

  useEffect(() => {
    async function fetchInfo() {
      try {
        const res = await fetch(`http://localhost:8000/register/${token}`)
        if (res.status === 404) { setNotFound(true); return }
        const data = await res.json()
        setInfo(data)
      } catch {
        setNotFound(true)
      } finally {
        setLoading(false)
      }
    }
    fetchInfo()
  }, [token])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!firstName.trim() || !lastName.trim()) return
    setSubmitting(true)
    setResult(null)
    try {
      const res = await fetch(`http://localhost:8000/register/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ first_name: firstName.trim(), last_name: lastName.trim() }),
      })
      const data = await res.json()
      setResult({ ok: data.success, message: data.message, slot: data.slot_description })
      if (data.success) {
        // Refresh slot availability
        const infoRes = await fetch(`http://localhost:8000/register/${token}`)
        if (infoRes.ok) setInfo(await infoRes.json())
      }
    } catch {
      setResult({ ok: false, message: 'Could not reach the server. Please try again later.' })
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div style={pageStyle}>
        <div style={cardStyle}>
          <p style={{ textAlign: 'center', color: '#6b7280' }}>Loading tournament details…</p>
        </div>
      </div>
    )
  }

  if (notFound) {
    return (
      <div style={pageStyle}>
        <div style={cardStyle}>
          <div style={headerStyle}>
            <h1 style={{ margin: 0, fontSize: 20 }}>Registration Link Not Found</h1>
          </div>
          <div style={{ padding: '24px 28px', color: '#374151' }}>
            <p>This registration link is invalid or has expired. Please contact the tournament organiser.</p>
          </div>
        </div>
      </div>
    )
  }

  const isFull = info?.is_full || info?.status === 'finalized'
  const registered = info?.players_registered ?? 0
  const total = info?.total_slots ?? 0

  return (
    <div style={pageStyle}>
      <div style={cardStyle}>
        {/* Card header */}
        <div style={headerStyle}>
          <h1 style={{ margin: 0, fontSize: 20 }}>{info.name}</h1>
          <div style={{ marginTop: 4, fontSize: 13, opacity: 0.85 }}>
            {info.date && <span>{info.date}</span>}
            {info.venue && <span> &nbsp;·&nbsp; {info.venue}</span>}
            {info.format && <span> &nbsp;·&nbsp; {info.format}</span>}
          </div>
        </div>

        <div style={{ padding: '20px 28px' }}>
          {/* Slot progress */}
          <div style={{
            background: isFull ? '#fef2f2' : '#f0fdf4',
            border: `1px solid ${isFull ? '#fecaca' : '#86efac'}`,
            borderRadius: 8,
            padding: '10px 16px',
            marginBottom: 20,
            fontSize: 13,
            color: isFull ? '#dc2626' : '#166534',
            fontWeight: 600,
          }}>
            {isFull
              ? 'This tournament is full — no more slots available.'
              : `${registered} of ${total} spots filled — ${total - registered} remaining`}
          </div>

          {result?.ok ? (
            <div style={{
              background: '#f0fdf4',
              border: '1px solid #86efac',
              borderRadius: 10,
              padding: '20px 24px',
              textAlign: 'center',
            }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🏌️</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: '#166534', marginBottom: 6 }}>
                You're registered!
              </div>
              <div style={{ fontSize: 14, color: '#374151' }}>{result.message}</div>
              {result.slot && (
                <div style={{ marginTop: 10, fontSize: 13, color: '#6b7280' }}>
                  Your slot: <strong style={{ color: '#166534' }}>{result.slot}</strong>
                </div>
              )}
            </div>
          ) : (
            !isFull && (
              <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: 14 }}>
                  <label style={labelStyle}>First Name</label>
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    required
                    disabled={submitting}
                    style={inputStyle}
                    placeholder="e.g. Jane"
                  />
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Last Name</label>
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    required
                    disabled={submitting}
                    style={inputStyle}
                    placeholder="e.g. Smith"
                  />
                </div>

                {result && !result.ok && (
                  <div style={{
                    marginBottom: 14,
                    padding: '10px 14px',
                    borderRadius: 8,
                    background: '#fef2f2',
                    border: '1px solid #fecaca',
                    color: '#dc2626',
                    fontSize: 13,
                    fontWeight: 600,
                  }}>
                    {result.message}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting || !firstName.trim() || !lastName.trim()}
                  style={{
                    width: '100%',
                    background: submitting ? '#86efac' : '#166534',
                    color: '#fff',
                    border: 'none',
                    padding: '11px 0',
                    borderRadius: 8,
                    fontSize: 15,
                    fontWeight: 700,
                    cursor: submitting ? 'default' : 'pointer',
                  }}
                >
                  {submitting ? 'Registering…' : 'Register for Tournament'}
                </button>
              </form>
            )
          )}
        </div>
      </div>
    </div>
  )
}

const pageStyle = {
  minHeight: '100vh',
  background: '#f0fdf4',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontFamily: 'system-ui, sans-serif',
  padding: '32px 16px',
}

const cardStyle = {
  background: '#fff',
  borderRadius: 12,
  boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
  width: '100%',
  maxWidth: 440,
  overflow: 'hidden',
}

const headerStyle = {
  background: '#166534',
  color: '#fff',
  padding: '20px 28px',
}

const labelStyle = {
  display: 'block',
  fontWeight: 600,
  fontSize: 13,
  marginBottom: 5,
  color: '#374151',
}

const inputStyle = {
  width: '100%',
  boxSizing: 'border-box',
  border: '1px solid #d1d5db',
  borderRadius: 8,
  padding: '9px 12px',
  fontSize: 14,
  fontFamily: 'inherit',
  outline: 'none',
  color: '#111827',
}
