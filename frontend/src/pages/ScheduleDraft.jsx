import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext'

export default function ScheduleDraft() {
  const [schedule, setSchedule] = useState(null)
  const [brochure, setBrochure] = useState(null)
  const [tournament, setTournament] = useState(null)
  const [ruleSheet, setRuleSheet] = useState(null)
  const [fnbSummary, setFnbSummary] = useState(null)
  const [saved, setSaved] = useState(false)
  const [saving, setSaving] = useState(false)
  // rule sheet email modal
  const [ruleSheetModal, setRuleSheetModal] = useState(false)
  const [ruleSheetEmails, setRuleSheetEmails] = useState('')
  const [ruleSheetSending, setRuleSheetSending] = useState(false)
  const [ruleSheetResult, setRuleSheetResult] = useState(null)
  // F&B email modal
  const [fnbModal, setFnbModal] = useState(false)
  const [fnbEmails, setFnbEmails] = useState('')
  const [fnbSending, setFnbSending] = useState(false)
  const [fnbResult, setFnbResult] = useState(null)
  const { authHeaders } = useAuth()

  const loadFromStorage = useCallback(() => {
    try {
      const s = localStorage.getItem('golfDraftSchedule')
      const b = localStorage.getItem('golfDraftBrochure')
      const t = localStorage.getItem('golfDraftTournament')
      if (s) setSchedule(JSON.parse(s))
      if (b) setBrochure(JSON.parse(b))
      if (t) setTournament(JSON.parse(t))
      const rs = localStorage.getItem('golfDraftRuleSheet')
      const fb = localStorage.getItem('golfDraftFnBSummary')
      if (rs) setRuleSheet(JSON.parse(rs))
      if (fb) setFnbSummary(JSON.parse(fb))
    } catch {
      // ignore parse errors
    }
  }, [])

  useEffect(() => {
    loadFromStorage()
    // Refresh data when the tab regains focus (e.g. after chat edits)
    const onFocus = () => {
      setSaved(false)
      loadFromStorage()
    }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [loadFromStorage])

  async function handleSave() {
    if (!tournament || !schedule || !brochure) return
    setSaving(true)
    try {
      const existing = JSON.parse(localStorage.getItem('savedReservations') || '[]')
      const entry = {
        id: Date.now(),
        savedAt: new Date().toISOString(),
        tournament,
        schedule,
        brochure,
        tournament_id: null,
        registration_token: null,
      }

      // Attempt to persist to MongoDB so we get a registration token
      try {
        const res = await fetch('http://localhost:8000/tournaments', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({ tournament, schedule, brochure }),
        })
        if (res.ok) {
          const data = await res.json()
          entry.tournament_id = data.tournament_id
          entry.registration_token = data.registration_token
        }
      } catch {
        // DB save failed — still save locally without the registration link
      }

      existing.push(entry)
      localStorage.setItem('savedReservations', JSON.stringify(existing))
      setSaved(true)
    } catch {
      alert('Failed to save — storage error.')
    } finally {
      setSaving(false)
    }
  }

  if (!schedule) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#6b7280' }}>
        <h2>No schedule found</h2>
        <p>Return to the planner and click <strong>Generate Documents</strong> to create a schedule.</p>
      </div>
    )
  }

  const meta = brochure?.meta || {}

  return (
    <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px', fontFamily: 'system-ui, sans-serif' }}>

      {/* Header */}
      <div style={{
        background: '#166534',
        color: '#fff',
        borderRadius: 10,
        padding: '20px 28px',
        marginBottom: 24,
      }}>
        <h1 style={{ margin: 0, fontSize: 22 }}>{meta.name || 'Tournament Schedule'}</h1>
        <div style={{ marginTop: 6, opacity: 0.85, fontSize: 14 }}>
          {meta.date && <span>{meta.date}</span>}
          {meta.numberOfDays > 1 && <span> ({meta.numberOfDays} days)</span>}
          {meta.venue && <span> &nbsp;·&nbsp; {meta.venue}</span>}
          {meta.format && <span> &nbsp;·&nbsp; {meta.format}</span>}
          {meta.eventType && <span> &nbsp;·&nbsp; {meta.eventType === 'team' ? `Teams of ${meta.teamSize}` : 'Individual'}</span>}
        </div>
        <div style={{ marginTop: 4, opacity: 0.75, fontSize: 13 }}>
          {meta.playerCount} players &nbsp;·&nbsp; First tee: {meta.teeTimeStart} &nbsp;·&nbsp; {meta.teeTimeInterval}-min intervals
          {meta.registrationDeadline && <span> &nbsp;·&nbsp; Reg. closes: {meta.registrationDeadline}</span>}
          {meta.entryFee > 0 && <span> &nbsp;·&nbsp; Entry: ${meta.entryFee}</span>}
        </div>
      </div>

      {/* Draft banner */}
      <div style={{
        background: '#fef9c3',
        border: '1px solid #fde047',
        borderRadius: 8,
        padding: '10px 16px',
        fontSize: 13,
        marginBottom: 20,
        color: '#854d0e',
      }}>
        <strong>Draft</strong> — Return to the planner chat to make changes. This page auto-refreshes when you come back.
      </div>

      {/* Tee Time Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', fontWeight: 700, fontSize: 15 }}>
          Tee Time Schedule
        </div>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ background: '#f9fafb' }}>
              <th style={thStyle}>Group</th>
              <th style={thStyle}>Tee Time</th>
              <th style={thStyle}>Players</th>
            </tr>
          </thead>
          <tbody>
            {schedule.map((row) => (
              <tr key={row.group} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={tdStyle}>Group {row.group}</td>
                <td style={{ ...tdStyle, fontWeight: 600, color: '#166534' }}>{row.teeTime}</td>
                <td style={tdStyle}>{row.players.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Save button */}
      <div style={{ marginTop: 24, display: 'flex', alignItems: 'center', gap: 16 }}>
        {saved ? (
          <div style={{
            background: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: 8,
            padding: '10px 20px',
            color: '#166534',
            fontWeight: 600,
            fontSize: 14,
          }}>
            Schedule saved! Return to the planner to continue editing, or visit the Reservations page.
          </div>
        ) : (
          <button
            onClick={handleSave}
            disabled={saving}
            style={{
              background: saving ? '#93c5fd' : '#2563eb',
              color: '#fff',
              border: 'none',
              padding: '10px 28px',
              borderRadius: 8,
              fontWeight: 700,
              fontSize: 15,
              cursor: saving ? 'default' : 'pointer',
            }}
          >
            {saving ? 'Saving…' : 'Save Schedule'}
          </button>
        )}
      </div>

      {/* Rule Sheet card */}
      {ruleSheet && (
        <div className="card" style={{ padding: 0, overflow: 'hidden', marginTop: 24 }}>
          <div style={{
            padding: '14px 20px',
            borderBottom: '1px solid #e5e7eb',
            fontWeight: 700,
            fontSize: 15,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>&#128220; Player Information Guide</span>
            <button
              onClick={() => { setRuleSheetModal(true); setRuleSheetEmails(''); setRuleSheetResult(null) }}
              style={{
                background: '#0891b2', color: '#fff', border: 'none',
                padding: '7px 16px', borderRadius: 6, fontSize: 13,
                fontWeight: 600, cursor: 'pointer',
              }}
            >
              Send to Players
            </button>
          </div>
          <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151' }}>
            <strong>Subject:</strong> {ruleSheet.subject}
          </div>
          <div style={{
            margin: '0 20px 16px',
            background: '#f0fdfa',
            border: '1px solid #99f6e4',
            borderRadius: 6,
            padding: '12px 16px',
          }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#134e4a', lineHeight: 1.6 }}>
              {ruleSheet.body?.slice(0, 600)}{ruleSheet.body?.length > 600 ? '\n…' : ''}
            </pre>
          </div>
        </div>
      )}

      {/* F&B Summary card */}
      {fnbSummary && (
        <div className="card" style={{ padding: 0, overflow: 'hidden', marginTop: 24 }}>
          <div style={{
            padding: '14px 20px',
            borderBottom: '1px solid #e5e7eb',
            fontWeight: 700,
            fontSize: 15,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>&#127869; Food &amp; Beverage Summary</span>
            <button
              onClick={() => { setFnbModal(true); setFnbEmails(''); setFnbResult(null) }}
              style={{
                background: '#d97706', color: '#fff', border: 'none',
                padding: '7px 16px', borderRadius: 6, fontSize: 13,
                fontWeight: 600, cursor: 'pointer',
              }}
            >
              Send to Caterer
            </button>
          </div>
          <div style={{ padding: '14px 20px', fontSize: 13, color: '#374151' }}>
            <strong>Subject:</strong> {fnbSummary.subject}
          </div>
          <div style={{
            margin: '0 20px 16px',
            background: '#fffbeb',
            border: '1px solid #fde68a',
            borderRadius: 6,
            padding: '12px 16px',
          }}>
            <pre style={{ fontFamily: 'monospace', fontSize: 12, whiteSpace: 'pre-wrap', margin: 0, color: '#78350f', lineHeight: 1.6 }}>
              {fnbSummary.body?.slice(0, 600)}{fnbSummary.body?.length > 600 ? '\n…' : ''}
            </pre>
          </div>
        </div>
      )}

      {/* Rule Sheet Email Modal */}
      {ruleSheetModal && (
        <div
          onClick={() => { if (!ruleSheetSending) setRuleSheetModal(false) }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div onClick={(e) => e.stopPropagation()} style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 500, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}>
            <div style={{ background: '#0891b2', color: '#fff', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Send Player Information Guide</div>
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 2 }}>{meta.name || 'Tournament'}</div>
              </div>
              <button onClick={() => setRuleSheetModal(false)} disabled={ruleSheetSending} style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ background: '#ecfeff', borderBottom: '1px solid #e5e7eb', padding: '10px 20px', fontSize: 12, color: '#374151' }}>
              Emails the full Player Information Guide to participants — event details, format, conduct rules, and catering info.
            </div>
            <div style={{ padding: '20px 24px' }}>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Recipient Emails</label>
              <textarea
                value={ruleSheetEmails}
                onChange={(e) => setRuleSheetEmails(e.target.value)}
                placeholder="e.g. player1@example.com player2@example.com"
                rows={3}
                disabled={ruleSheetSending}
                style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none', color: '#111827' }}
              />
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
              {ruleSheetResult && (
                <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: ruleSheetResult.ok ? '#f0fdf4' : '#fef2f2', color: ruleSheetResult.ok ? '#166534' : '#dc2626', border: `1px solid ${ruleSheetResult.ok ? '#bbf7d0' : '#fecaca'}` }}>
                  {ruleSheetResult.message}
                </div>
              )}
            </div>
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setRuleSheetModal(false)} disabled={ruleSheetSending} style={draftBtnStyle}>Cancel</button>
              <button
                disabled={ruleSheetSending}
                onClick={async () => {
                  const emails = ruleSheetEmails.split(/[\s,;]+/).map(e => e.trim()).filter(Boolean)
                  if (!emails.length) { setRuleSheetResult({ ok: false, message: 'Please enter at least one email address.' }); return }
                  setRuleSheetSending(true); setRuleSheetResult(null)
                  try {
                    const r = await fetch('http://localhost:8000/email/send-rule-sheet', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipients: emails, tournament_meta: tournament || {} }) })
                    const d = await r.json()
                    setRuleSheetResult({ ok: d.success, message: d.message })
                    if (d.success) setTimeout(() => setRuleSheetModal(false), 2000)
                  } catch { setRuleSheetResult({ ok: false, message: 'Could not reach the server.' }) }
                  finally { setRuleSheetSending(false) }
                }}
                style={{ background: ruleSheetSending ? '#67e8f9' : '#0891b2', color: '#fff', border: 'none', padding: '7px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: ruleSheetSending ? 'default' : 'pointer' }}
              >
                {ruleSheetSending ? 'Sending…' : 'Send Guide'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* F&B Email Modal */}
      {fnbModal && (
        <div
          onClick={() => { if (!fnbSending) setFnbModal(false) }}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}
        >
          <div onClick={(e) => e.stopPropagation()} style={{ background: '#fff', borderRadius: 12, width: '100%', maxWidth: 500, boxShadow: '0 20px 60px rgba(0,0,0,0.25)', overflow: 'hidden' }}>
            <div style={{ background: '#d97706', color: '#fff', padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16 }}>Send F&amp;B Summary</div>
                <div style={{ fontSize: 12, opacity: 0.8, marginTop: 2 }}>{meta.name || 'Tournament'}</div>
              </div>
              <button onClick={() => setFnbModal(false)} disabled={fnbSending} style={{ background: 'none', border: 'none', color: '#fff', fontSize: 20, cursor: 'pointer' }}>✕</button>
            </div>
            <div style={{ background: '#fffbeb', borderBottom: '1px solid #e5e7eb', padding: '10px 20px', fontSize: 12, color: '#374151' }}>
              Emails the Food &amp; Beverage Summary / Banquet Order Sheet to your caterer or venue contact.
            </div>
            <div style={{ padding: '20px 24px' }}>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Recipient Emails</label>
              <textarea
                value={fnbEmails}
                onChange={(e) => setFnbEmails(e.target.value)}
                placeholder="e.g. catering@venue.com"
                rows={3}
                disabled={fnbSending}
                style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #d1d5db', borderRadius: 8, padding: '10px 12px', fontSize: 13, fontFamily: 'inherit', resize: 'vertical', outline: 'none', color: '#111827' }}
              />
              <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 4 }}>Separate multiple addresses with spaces, commas, or newlines.</div>
              {fnbResult && (
                <div style={{ marginTop: 12, padding: '10px 14px', borderRadius: 8, fontSize: 13, fontWeight: 600, background: fnbResult.ok ? '#f0fdf4' : '#fef2f2', color: fnbResult.ok ? '#166534' : '#dc2626', border: `1px solid ${fnbResult.ok ? '#bbf7d0' : '#fecaca'}` }}>
                  {fnbResult.message}
                </div>
              )}
            </div>
            <div style={{ padding: '12px 24px 20px', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button onClick={() => setFnbModal(false)} disabled={fnbSending} style={draftBtnStyle}>Cancel</button>
              <button
                disabled={fnbSending}
                onClick={async () => {
                  const emails = fnbEmails.split(/[\s,;]+/).map(e => e.trim()).filter(Boolean)
                  if (!emails.length) { setFnbResult({ ok: false, message: 'Please enter at least one email address.' }); return }
                  setFnbSending(true); setFnbResult(null)
                  try {
                    const r = await fetch('http://localhost:8000/email/send-fnb-summary', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ recipients: emails, tournament_meta: tournament || {} }) })
                    const d = await r.json()
                    setFnbResult({ ok: d.success, message: d.message })
                    if (d.success) setTimeout(() => setFnbModal(false), 2000)
                  } catch { setFnbResult({ ok: false, message: 'Could not reach the server.' }) }
                  finally { setFnbSending(false) }
                }}
                style={{ background: fnbSending ? '#fcd34d' : '#d97706', color: '#fff', border: 'none', padding: '7px 20px', borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: fnbSending ? 'default' : 'pointer' }}
              >
                {fnbSending ? 'Sending…' : 'Send Summary'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const thStyle = {
  padding: '10px 16px',
  textAlign: 'left',
  fontWeight: 600,
  color: '#374151',
  borderBottom: '2px solid #e5e7eb',
  fontSize: 13,
}

const tdStyle = {
  padding: '10px 16px',
  color: '#111827',
}

const draftBtnStyle = {
  background: 'transparent',
  border: '1px solid #6b7280',
  color: '#374151',
  padding: '6px 16px',
  borderRadius: 6,
  fontSize: 13,
  cursor: 'pointer',
  fontWeight: 500,
}
