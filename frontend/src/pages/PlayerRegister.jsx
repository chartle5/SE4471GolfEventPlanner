import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import Icon from '../components/Icon'

export default function PlayerRegister() {
  const { token } = useParams()
  const [info, setInfo]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName]   = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [rentalClubs, setRentalClubs] = useState(false)
  const [clubHand, setClubHand] = useState('')
  const [teamName, setTeamName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null) // { ok, message, slot }

  useEffect(() => {
    async function fetchInfo() {
      try {
        const res = await fetch(`${import.meta.env.VITE_API_URL}/register/${token}`)
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
    const isTeam = info?.event_type === 'team'
    if (!firstName.trim() || !lastName.trim() || !phoneNumber.trim()) return
    if (isTeam && !teamName.trim()) return
    if (rentalClubs && !clubHand) return
    setSubmitting(true)
    setResult(null)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/register/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone_number: phoneNumber.trim(),
          rental_clubs: rentalClubs,
          club_hand: rentalClubs ? clubHand : null,
          team_name: isTeam ? (teamName.trim() || null) : null,
        }),
      })
      const data = await res.json()
      setResult({ ok: data.success, message: data.message, slot: data.slot_description })
      if (data.success) {
        // Refresh slot availability
        const infoRes = await fetch(`${import.meta.env.VITE_API_URL}/register/${token}`)
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
      <div className="auth-shell">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <span className="spinner" style={{ color: 'var(--fairway)', width: 22, height: 22 }} />
          <p className="muted" style={{ marginTop: 12 }}>Loading tournament details…</p>
        </div>
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="auth-shell">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <div className="auth-mark" style={{ background: 'var(--danger-bg)', color: 'var(--danger)' }}>
            <Icon name="close" size={26} strokeWidth={2} />
          </div>
          <div className="auth-title" style={{ fontSize: 22 }}>Link Not Found</div>
          <p className="muted" style={{ marginTop: 10 }}>
            This registration link is invalid or has expired. Please contact the tournament organiser.
          </p>
        </div>
      </div>
    )
  }

  const isFull = info?.is_full || info?.status === 'finalized'
  const registered = info?.players_registered ?? 0
  const total = info?.total_slots ?? 0

  return (
    <div className="auth-shell">
      <div className="auth-card" style={{ maxWidth: 460, padding: 0, overflow: 'hidden' }}>
        {/* Card header */}
        <div style={{
          background: 'linear-gradient(135deg, var(--forest) 0%, var(--pine) 100%)',
          color: '#fff', padding: '24px 30px',
        }}>
          <div className="eyebrow" style={{ color: 'var(--champagne)', marginBottom: 6 }}>Player Registration</div>
          <h1 style={{ margin: 0, fontSize: 24, color: '#fff' }}>{info.name}</h1>
          <div style={{ marginTop: 6, fontSize: 13, opacity: 0.88 }}>
            {info.date && <span>{info.date}</span>}
            {info.venue && <span> · {info.venue}</span>}
            {info.format && <span> · {info.format}</span>}
          </div>
        </div>

        <div style={{ padding: '24px 30px' }}>
          {/* Slot progress */}
          <div className={`notice ${isFull ? 'notice-danger' : 'notice-success'}`} style={{ marginBottom: 20, fontWeight: 600 }}>
            <Icon name={isFull ? 'close' : 'users'} size={16} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>
              {isFull
                ? 'This tournament is full — no more slots available.'
                : `${registered} of ${total} spots filled — ${total - registered} remaining`}
            </span>
          </div>

          {result?.ok ? (
            <div className="notice notice-success" style={{ flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '26px 24px' }}>
              <div style={{
                width: 56, height: 56, borderRadius: '50%', marginBottom: 12,
                background: '#fff', border: '1px solid var(--success-bd)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--fairway)',
              }}>
                <Icon name="check" size={28} strokeWidth={2.2} />
              </div>
              <div style={{ fontFamily: 'var(--font-serif)', fontSize: 22, fontWeight: 700, color: 'var(--forest)', marginBottom: 6 }}>
                You're registered!
              </div>
              <div style={{ fontSize: 14, color: 'var(--slate)' }}>{result.message}</div>
              {result.slot && (
                <div style={{ marginTop: 10, fontSize: 13, color: 'var(--muted)' }}>
                  Your slot: <strong style={{ color: 'var(--forest)' }}>{result.slot}</strong>
                </div>
              )}
            </div>
          ) : (
            !isFull && (
              <form onSubmit={handleSubmit}>
                <div className="field" style={{ marginBottom: 14 }}>
                  <label className="field-label">First Name</label>
                  <input type="text" value={firstName} onChange={(e) => setFirstName(e.target.value)} required disabled={submitting} placeholder="e.g. Jane" />
                </div>
                <div className="field" style={{ marginBottom: 14 }}>
                  <label className="field-label">Last Name</label>
                  <input type="text" value={lastName} onChange={(e) => setLastName(e.target.value)} required disabled={submitting} placeholder="e.g. Smith" />
                </div>
                <div className="field" style={{ marginBottom: 14 }}>
                  <label className="field-label">Phone Number</label>
                  <input type="tel" value={phoneNumber} onChange={(e) => setPhoneNumber(e.target.value)} required disabled={submitting} placeholder="e.g. 555-123-4567" />
                </div>

                <div className="field" style={{ marginBottom: 14 }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 600, fontSize: 13, color: 'var(--slate)', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={rentalClubs}
                      onChange={(e) => { setRentalClubs(e.target.checked); if (!e.target.checked) setClubHand('') }}
                      disabled={submitting}
                    />
                    Rental Clubs
                  </label>
                  {rentalClubs && (
                    <div style={{ marginTop: 8, display: 'flex', gap: 24, paddingLeft: 4 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                        <input type="radio" name="clubHand" value="right" checked={clubHand === 'right'} onChange={() => setClubHand('right')} disabled={submitting} />
                        Right Handed
                      </label>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
                        <input type="radio" name="clubHand" value="left" checked={clubHand === 'left'} onChange={() => setClubHand('left')} disabled={submitting} />
                        Left Handed
                      </label>
                    </div>
                  )}
                </div>

                {info?.event_type === 'team' && (
                  <div className="field" style={{ marginBottom: 14 }}>
                    <label className="field-label">Team Name</label>
                    <input type="text" value={teamName} onChange={(e) => setTeamName(e.target.value)} required disabled={submitting} placeholder="e.g. Eagles" />
                    <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 4 }}>
                      Players with the same team name will be grouped together.
                    </div>
                  </div>
                )}

                {result && !result.ok && (
                  <div className="notice notice-danger" style={{ marginBottom: 14, fontWeight: 600 }}>{result.message}</div>
                )}

                <button
                  type="submit"
                  className="btn btn-gold btn-block"
                  disabled={
                    submitting ||
                    !firstName.trim() ||
                    !lastName.trim() ||
                    !phoneNumber.trim() ||
                    (info?.event_type === 'team' && !teamName.trim()) ||
                    (rentalClubs && !clubHand)
                  }
                  style={{ padding: '12px 0', fontSize: 15 }}
                >
                  {submitting ? <><span className="spinner" /> Registering…</> : 'Register for Tournament'}
                </button>
              </form>
            )
          )}
        </div>
      </div>
    </div>
  )
}
