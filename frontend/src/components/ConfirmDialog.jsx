import React from 'react'
import Modal from './Modal'

/**
 * Styled confirmation dialog — drop-in replacement for window.confirm.
 *
 * Render conditionally (when `open`) or pass `open`.
 * Props: open, title, message, confirmLabel, cancelLabel, tone, onConfirm, onCancel
 */
export default function ConfirmDialog({
  open = true,
  title = 'Are you sure?',
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  danger = true,
  onConfirm,
  onCancel,
}) {
  if (!open) return null
  return (
    <Modal
      title={title}
      tone={danger ? 'green' : 'green'}
      onClose={onCancel}
      maxWidth={440}
      footer={
        <>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}>{cancelLabel}</button>
          <button
            className={`btn btn-sm ${danger ? 'btn-danger-solid' : 'btn-primary'}`}
            onClick={onConfirm}
            autoFocus
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <div style={{ fontSize: 14, color: 'var(--slate)', lineHeight: 1.55 }}>{message}</div>
    </Modal>
  )
}
