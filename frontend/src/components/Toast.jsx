import React, { useEffect } from 'react'
import Icon from './Icon'

/**
 * Lightweight auto-dismissing toast. Render when `toast` is set:
 *   {toast && <Toast toast={toast} onClose={() => setToast(null)} />}
 * `toast` shape: { ok: boolean, message: string }
 */
export default function Toast({ toast, onClose, duration = 3200 }) {
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => onClose?.(), duration)
    return () => clearTimeout(t)
  }, [toast, onClose, duration])

  if (!toast) return null

  return (
    <div
      role="status"
      style={{
        position: 'fixed',
        bottom: 24,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 2000,
        minWidth: 280,
        maxWidth: 'min(90vw, 460px)',
        animation: 'modal-in 0.2s var(--ease)',
      }}
    >
      <div
        className={`notice ${toast.ok ? 'notice-success' : 'notice-danger'}`}
        style={{ fontWeight: 600, boxShadow: 'var(--shadow-lg)', alignItems: 'center' }}
      >
        <Icon name={toast.ok ? 'check' : 'close'} size={17} style={{ flexShrink: 0 }} />
        <span style={{ flex: 1 }}>{toast.message}</span>
        <button
          onClick={onClose}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', opacity: 0.6, padding: 0, width: 'auto' }}
          aria-label="Dismiss"
        >
          <Icon name="close" size={15} />
        </button>
      </div>
    </div>
  )
}
