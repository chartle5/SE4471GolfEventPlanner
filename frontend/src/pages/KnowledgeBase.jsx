import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { documents } from '../data/documents'

export default function KnowledgeBase() {
  const [q, setQ] = useState('')
  const [activeDoc, setActiveDoc] = useState(null)
  const filtered = documents.filter(d => (
    d.title.toLowerCase().includes(q.toLowerCase()) ||
    d.summary.toLowerCase().includes(q.toLowerCase()) ||
    d.content.toLowerCase().includes(q.toLowerCase())
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
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ fontWeight: 600, fontSize: 14, color: '#0f172a' }}>{d.title}</div>
                <button
                  onClick={() => setActiveDoc(d)}
                  style={{
                    background: 'transparent',
                    border: '1px solid #94a3b8',
                    color: '#475569',
                    padding: '6px 10px',
                    borderRadius: 8,
                    cursor: 'pointer',
                    fontSize: 12,
                  }}
                >
                  View
                </button>
              </div>
              <div className="muted small" style={{ marginTop: 3 }}>{d.summary}</div>
              <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                <span style={{ fontSize: 11, color: '#1f2937', background: '#f8fafc', borderRadius: 999, padding: '4px 8px' }}>{d.type}</span>
                {d.tags.map(tag => (
                  <span key={tag} style={{ fontSize: 11, color: '#475569', background: '#eff6ff', borderRadius: 999, padding: '4px 8px' }}>#{tag}</span>
                ))}
              </div>
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

      {activeDoc && (
        <div
          onClick={() => setActiveDoc(null)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
            zIndex: 50,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            style={{
              width: 'min(860px, 100%)',
              maxHeight: '85vh',
              background: '#ffffff',
              borderRadius: 18,
              boxShadow: '0 24px 80px rgba(15,23,42,0.18)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <div style={{ padding: '22px 24px', borderBottom: '1px solid #e2e8f0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontSize: 20, fontWeight: 700, color: '#0f172a' }}>{activeDoc.title}</div>
                  <div style={{ marginTop: 8, fontSize: 13, color: '#64748b' }}>
                    {activeDoc.type} · {activeDoc.tags.join(', ')}
                  </div>
                </div>
                <button
                  onClick={() => setActiveDoc(null)}
                  style={{
                    background: '#f8fafc',
                    border: '1px solid #cbd5e1',
                    borderRadius: 10,
                    padding: '6px 12px',
                    cursor: 'pointer',
                    fontSize: 13,
                  }}
                >
                  Close
                </button>
              </div>
            </div>
            <div style={{ padding: '20px 24px', overflowY: 'auto' }}>
              <div className="muted small" style={{ marginBottom: 18 }}>{activeDoc.summary}</div>
              <div style={{ color: '#334155', fontSize: 15, lineHeight: 1.75 }}>
                <ReactMarkdown
                  components={{
                    h1: ({ children }) => <h1 style={{ fontSize: '24px', fontWeight: 'bold', marginBottom: '16px', marginTop: '24px', color: '#0f172a' }}>{children}</h1>,
                    h2: ({ children }) => <h2 style={{ fontSize: '20px', fontWeight: 'bold', marginBottom: '12px', marginTop: '20px', color: '#0f172a' }}>{children}</h2>,
                    h3: ({ children }) => <h3 style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '8px', marginTop: '16px', color: '#0f172a' }}>{children}</h3>,
                    p: ({ children }) => <p style={{ marginBottom: '12px', lineHeight: 1.6 }}>{children}</p>,
                    ul: ({ children }) => <ul style={{ marginBottom: '12px', paddingLeft: '20px' }}>{children}</ul>,
                    ol: ({ children }) => <ol style={{ marginBottom: '12px', paddingLeft: '20px' }}>{children}</ol>,
                    li: ({ children }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
                    strong: ({ children }) => <strong style={{ fontWeight: 'bold' }}>{children}</strong>,
                    em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
                  }}
                >
                  {activeDoc.content}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

