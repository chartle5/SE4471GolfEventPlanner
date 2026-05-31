import React, { useEffect } from 'react'
import Icon from './Icon'

/**
 * Consistent modal shell used across the app.
 *
 * Props:
 *  - title, subtitle        header text
 *  - tone                   'green' | 'gold' | 'info' | 'plum'  (header gradient)
 *  - note                   optional grey sub-header description
 *  - onClose                close handler (overlay click + ✕ + Esc)
 *  - closeDisabled          when true, blocks close (e.g. while sending)
 *  - footer                 node rendered in the footer (buttons)
 *  - maxWidth               override modal width
 *  - children               body content
 */
export default function Modal({
  title,
  subtitle,
  tone = 'green',
  note,
  onClose,
  closeDisabled = false,
  footer,
  maxWidth,
  children,
}) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape' && !closeDisabled) onClose?.()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, closeDisabled])

  const toneClass = tone === 'green' ? '' : tone

  return (
    <div className="modal-overlay" onClick={() => !closeDisabled && onClose?.()}>
      <div
        className="modal"
        style={maxWidth ? { maxWidth } : undefined}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className={`modal-head ${toneClass}`}>
          <div>
            <div className="modal-title">{title}</div>
            {subtitle && <div className="modal-subtitle">{subtitle}</div>}
          </div>
          {onClose && (
            <button className="modal-x" onClick={onClose} disabled={closeDisabled} aria-label="Close">
              <Icon name="close" size={15} strokeWidth={2} />
            </button>
          )}
        </div>

        {note && <div className="modal-note">{note}</div>}

        <div className="modal-body">{children}</div>

        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  )
}
