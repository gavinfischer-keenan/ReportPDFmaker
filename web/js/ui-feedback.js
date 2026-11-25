/**
 * Non-blocking Toast Notifications, Inline Confirm Modal & Modal Focus Trap
 */

import { escapeHtml } from './html-utils.js';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])'
].join(', ');

export function showToast(message, type = 'info', durationMs = 4500) {
  if (typeof document === 'undefined') return;
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' };
  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-msg">${escapeHtml(message)}</span>
    <button type="button" class="toast-close" aria-label="Dismiss notification">&times;</button>
  `;

  const remove = () => {
    toast.classList.add('toast-leaving');
    setTimeout(() => toast.remove(), 180);
  };
  toast.querySelector('.toast-close')?.addEventListener('click', remove);
  container.appendChild(toast);

  if (durationMs > 0) {
    setTimeout(remove, durationMs);
  }
}

export class ModalFocusTrap {
  constructor() {
    this.activeModal = null;
    this.previousFocus = null;
    this._onKeyDown = (e) => this.handleKeyDown(e);
  }

  activate(modalEl, triggerEl = null) {
    if (!modalEl || typeof document === 'undefined') return;
    this.deactivate(false);
    this.activeModal = modalEl;
    this.previousFocus = triggerEl || document.activeElement;
    document.addEventListener('keydown', this._onKeyDown, true);

    setTimeout(() => {
      if (!this.activeModal) return;
      const focusables = this.getFocusables();
      if (focusables.length > 0 && !this.activeModal.contains(document.activeElement)) {
        focusables[0].focus();
      }
    }, 15);
  }

  deactivate(restoreFocus = true) {
    if (typeof document !== 'undefined') {
      document.removeEventListener('keydown', this._onKeyDown, true);
    }
    const prev = this.previousFocus;
    this.activeModal = null;
    this.previousFocus = null;
    if (restoreFocus && prev && typeof prev.focus === 'function' && document.contains(prev)) {
      prev.focus();
    }
  }

  getFocusables() {
    if (!this.activeModal) return [];
    return Array.from(this.activeModal.querySelectorAll(FOCUSABLE_SELECTOR))
      .filter(el => el.offsetParent !== null || el === document.activeElement);
  }

  handleKeyDown(e) {
    if (e.key !== 'Tab' || !this.activeModal) return;
    const focusables = this.getFocusables();
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    if (e.shiftKey && (document.activeElement === first || !this.activeModal.contains(document.activeElement))) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}

export function confirmDialog({
  title = 'Confirm Action',
  message = 'Are you sure?',
  confirmLabel = 'Confirm',
  danger = false
} = {}) {
  if (typeof document === 'undefined') return Promise.resolve(false);
  const modal = document.getElementById('modal-confirm');
  const titleEl = document.getElementById('confirm-modal-title');
  const msgEl = document.getElementById('confirm-modal-message');
  const okBtn = document.getElementById('btn-confirm-ok');
  const cancelBtn = document.getElementById('btn-confirm-cancel');
  const closeBtn = document.getElementById('btn-close-confirm');
  if (!modal || !okBtn || !cancelBtn) return Promise.resolve(false);

  if (titleEl) titleEl.textContent = title;
  if (msgEl) msgEl.textContent = message;
  okBtn.textContent = confirmLabel;
  okBtn.classList.toggle('btn-danger', Boolean(danger));
  okBtn.classList.toggle('btn-primary', !danger);

  const trap = new ModalFocusTrap();
  modal.classList.remove('hidden');
  trap.activate(modal);

  return new Promise((resolve) => {
    const cleanup = (answer) => {
      modal.classList.add('hidden');
      trap.deactivate(true);
      okBtn.removeEventListener('click', onOk);
      cancelBtn.removeEventListener('click', onCancel);
      closeBtn?.removeEventListener('click', onCancel);
      modal.removeEventListener('click', onBackdrop);
      document.removeEventListener('keydown', onKey, true);
      resolve(answer);
    };
    const onOk = () => cleanup(true);
    const onCancel = () => cleanup(false);
    const onBackdrop = (e) => { if (e.target === modal) cleanup(false); };
    const onKey = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        cleanup(false);
      }
    };

    okBtn.addEventListener('click', onOk);
    cancelBtn.addEventListener('click', onCancel);
    closeBtn?.addEventListener('click', onCancel);
    modal.addEventListener('click', onBackdrop);
    document.addEventListener('keydown', onKey, true);
  });
}
