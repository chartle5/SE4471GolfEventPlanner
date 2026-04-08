import React, { useState } from 'react'
import { documents } from '../data/documents'

export default function KnowledgeBase() {
  const [q, setQ] = useState('')
  const filtered = documents.filter(d => (
    d.title.toLowerCase().includes(q.toLowerCase()) ||
    d.summary.toLowerCase().includes(q.toLowerCase())
  ))

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <h1>Knowledge Base</h1>
        <div className="muted small" style={{ marginTop: 4 }}>Browse tournament planning resources and best practices</div>
      </div>

      <div style={{ maxWidth: 420, marginBottom: 20 }}>
        <input
          placeholder="Search documents…"
          value={q}
          onChange={e => setQ(e.target.value)}
        />
      </div>

      <div className="doc-list">
        {filtered.map(d => (
          <div key={d.id} className="card" style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: 9,
              background: '#f0fdf4',
              border: '1px solid #a7f3d0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
              flexShrink: 0,
            }}>
              📄
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 14, color: '#0f172a' }}>{d.title}</div>
              <div className="muted small" style={{ marginTop: 3 }}>{d.summary}</div>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '48px 24px',
            color: '#94a3b8',
            fontSize: 14,
            background: '#fff',
            borderRadius: 12,
            border: '1px solid #e4eaf2',
          }}>
            No documents match your search.
          </div>
        )}
      </div>
    </div>
  )
}

