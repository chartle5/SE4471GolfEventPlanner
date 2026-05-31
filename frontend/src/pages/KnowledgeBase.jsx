import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { documents } from '../data/documents'
import Icon from '../components/Icon'
import Modal from '../components/Modal'

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
      <div className="page-head">
        <div className="eyebrow">Resources</div>
        <h1 className="page-title">Knowledge Base</h1>
        <div className="page-sub">Browse tournament planning resources and best practices</div>
      </div>

      <div style={{ position: 'relative', maxWidth: 440, marginBottom: 22 }}>
        <span style={{ position: 'absolute', left: 13, top: '50%', transform: 'translateY(-50%)', color: 'var(--faint)', pointerEvents: 'none' }}>
          <Icon name="search" size={17} />
        </span>
        <input
          placeholder="Search documents…"
          value={q}
          onChange={e => setQ(e.target.value)}
          style={{ paddingLeft: 38 }}
        />
      </div>

      <div className="doc-list">
        {filtered.map(d => (
          <div key={d.id} className="card card-hover" style={{ display: 'flex', gap: 16, alignItems: 'flex-start' }}>
            <div style={{
              width: 44, height: 44, borderRadius: 11,
              background: 'var(--green-tint)', border: '1px solid var(--success-bd)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: 'var(--fairway)', flexShrink: 0,
            }}>
              <Icon name="doc" size={21} />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}>
                <div style={{ fontFamily: 'var(--font-serif)', fontWeight: 600, fontSize: 17, color: 'var(--ink)' }}>{d.title}</div>
                <button onClick={() => setActiveDoc(d)} className="btn btn-ghost btn-sm" style={{ flexShrink: 0 }}>
                  View
                </button>
              </div>
              <div className="muted small" style={{ marginTop: 4 }}>{d.summary}</div>
              <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                <span className="badge badge-gold">{d.type}</span>
                {d.tags.map(tag => (
                  <span key={tag} className="badge badge-neutral">#{tag}</span>
                ))}
              </div>
            </div>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon"><Icon name="search" size={24} /></div>
            <h3>No documents found</h3>
            <p style={{ margin: 0 }}>No documents match “{q}”. Try a different search.</p>
          </div>
        )}
      </div>

      {activeDoc && (
        <Modal
          title={activeDoc.title}
          subtitle={`${activeDoc.type} · ${activeDoc.tags.join(', ')}`}
          onClose={() => setActiveDoc(null)}
          maxWidth={860}
        >
          <div className="muted small" style={{ marginBottom: 18 }}>{activeDoc.summary}</div>
          <div style={{ color: 'var(--slate)', fontSize: 15, lineHeight: 1.75 }}>
            <ReactMarkdown
              components={{
                h1: ({ children }) => <h1 style={{ fontSize: '24px', marginBottom: '14px', marginTop: '22px' }}>{children}</h1>,
                h2: ({ children }) => <h2 style={{ fontSize: '20px', marginBottom: '12px', marginTop: '20px' }}>{children}</h2>,
                h3: ({ children }) => <h3 style={{ fontSize: '17px', marginBottom: '8px', marginTop: '16px' }}>{children}</h3>,
                p: ({ children }) => <p style={{ marginBottom: '12px', lineHeight: 1.7 }}>{children}</p>,
                ul: ({ children }) => <ul style={{ marginBottom: '12px', paddingLeft: '20px' }}>{children}</ul>,
                ol: ({ children }) => <ol style={{ marginBottom: '12px', paddingLeft: '20px' }}>{children}</ol>,
                li: ({ children }) => <li style={{ marginBottom: '4px' }}>{children}</li>,
                strong: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
                em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
              }}
            >
              {activeDoc.content}
            </ReactMarkdown>
          </div>
        </Modal>
      )}
    </div>
  )
}
