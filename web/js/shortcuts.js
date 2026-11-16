/**
 * Keyboard Shortcuts Manager & "?" Help Overlay
 * Guards against firing while typing in inputs, textareas, selects, or contenteditable elements.
 */

export const CORE_SHORTCUTS = [
  { key: 'Ctrl/⌘ + K', actionId: 'open-palette', label: 'Open Command Palette', category: 'General' },
  { key: '?', actionId: 'toggle-shortcuts', label: 'Show Keyboard Shortcuts', category: 'General' },
  { key: 'A', actionId: 'add-files', label: 'Add Files to Document', category: 'Document' },
  { key: 'E', actionId: 'export-pdf', label: 'Download / Export PDF', category: 'Document' },
  { key: 'S', actionId: 'open-shrink', label: 'Shrink / Compress PDF', category: 'Tools' },
  { key: 'R', actionId: 'rotate-90', label: 'Rotate Selected Image +90°', category: 'Page Edit' },
  { key: 'O', actionId: 'toggle-orientation', label: 'Toggle Portrait / Landscape', category: 'Page Edit' },
  { key: 'N', actionId: 'toggle-page-numbers', label: 'Toggle Page Numbers', category: 'Settings' },
  { key: 'F', actionId: 'fit-view', label: 'Fit Page to Preview', category: 'View' },
  { key: 'Del / ⌫', actionId: 'delete-page', label: 'Delete Selected Page', category: 'Page Edit' }
];

export const EXTRA_SHORTCUTS = [
  { key: '← / [', actionId: 'prev-page', label: 'Previous Page', category: 'Navigation' },
  { key: '→ / ]', actionId: 'next-page', label: 'Next Page', category: 'Navigation' },
  { key: '+ / −', actionId: 'zoom-step', label: 'Zoom In / Zoom Out', category: 'View' },
  { key: 'T', actionId: 'toggle-theme', label: 'Toggle Dark / Light Theme', category: 'Settings' },
  { key: 'G', actionId: 'open-settings', label: 'Open Document Settings', category: 'Settings' },
  { key: 'Esc', actionId: 'close-modal', label: 'Close Active Overlay', category: 'General' }
];

const TEXT_INPUT_TYPES = new Set([
  '', 'text', 'search', 'number', 'email', 'password', 'url', 'tel',
  'date', 'time', 'datetime-local', 'month', 'week'
]);

/**
 * Returns true when focus/target is inside an editable form field where typing shortcuts must not fire.
 */
export function isTypingInInput(target, activeElement = null) {
  const candidates = [target, activeElement].filter(Boolean);
  for (const el of candidates) {
    if (el.isContentEditable) return true;
    if (typeof el.closest === 'function' && el.closest('[contenteditable="true"], [contenteditable=""]')) {
      return true;
    }
    const tag = (el.tagName || '').toUpperCase();
    if (tag === 'TEXTAREA' || tag === 'SELECT') return true;
    if (tag === 'INPUT') {
      const inputType = (el.type || 'text').toLowerCase();
      if (TEXT_INPUT_TYPES.has(inputType)) return true;
    }
  }
  return false;
}

export class ShortcutManager {
  constructor({ runAction, getOpenModalId, closeTopModal, onToggleShortcuts }) {
    this.runAction = runAction;
    this.getOpenModalId = getOpenModalId;
    this.closeTopModal = closeTopModal;
    this.onToggleShortcuts = onToggleShortcuts;
  }

  attach() {
    if (typeof document === 'undefined') return;
    this._handler = (e) => this.handleKeyDown(e);
    document.addEventListener('keydown', this._handler);
  }

  detach() {
    if (typeof document === 'undefined' || !this._handler) return;
    document.removeEventListener('keydown', this._handler);
  }

  handleKeyDown(e) {
    const isMod = Boolean(e.ctrlKey || e.metaKey);
    const key = e.key;
    const lower = (key || '').toLowerCase();
    const activeEl = typeof document !== 'undefined' ? document.activeElement : null;
    const typing = isTypingInInput(e.target, activeEl);
    const openModalId = this.getOpenModalId ? this.getOpenModalId() : null;

    // 1. Escape closes active modal/overlay even from inside inputs
    if (key === 'Escape' && openModalId) {
      e.preventDefault();
      this.closeTopModal?.();
      return;
    }

    // 2. Cmd/Ctrl+K always opens/toggles Command Palette
    if (isMod && !e.altKey && lower === 'k') {
      e.preventDefault();
      this.runAction('open-palette');
      return;
    }

    // 3. Cmd/Ctrl+S exports PDF unless typing in an input
    if (isMod && !e.altKey && lower === 's') {
      e.preventDefault();
      this.runAction('export-pdf');
      return;
    }

    // 4. Never fire single-key shortcuts while typing in inputs
    if (typing) return;

    // 5. Block single-key shortcuts when a modal (other than shortcuts overlay) is open
    if (openModalId && openModalId !== 'modal-shortcuts') {
      return;
    }

    // Ignore modifier combos (e.g. Ctrl+R reload, Ctrl+A select all, Ctrl+F find)
    if (isMod || e.altKey) return;

    // "?" overlay (either '?' key or Shift+'/')
    if (key === '?' || (e.shiftKey && key === '/')) {
      e.preventDefault();
      this.onToggleShortcuts?.();
      return;
    }

    if (openModalId === 'modal-shortcuts') {
      return;
    }

    // Prevent range slider / button arrow keys from hijacking if focused on range
    const targetTag = (e.target?.tagName || '').toUpperCase();
    const isRangeInput = targetTag === 'INPUT' && (e.target?.type || '').toLowerCase() === 'range';

    switch (lower) {
      case 'a':
        e.preventDefault();
        this.runAction('add-files');
        break;
      case 'e':
        e.preventDefault();
        this.runAction('export-pdf');
        break;
      case 's':
        e.preventDefault();
        this.runAction('open-shrink');
        break;
      case 'r':
        e.preventDefault();
        this.runAction('rotate-90');
        break;
      case 'o':
        e.preventDefault();
        this.runAction('toggle-orientation');
        break;
      case 'n':
        e.preventDefault();
        this.runAction('toggle-page-numbers');
        break;
      case 'f':
        e.preventDefault();
        this.runAction('fit-view');
        break;
      case 't':
        e.preventDefault();
        this.runAction('toggle-theme');
        break;
      case 'g':
        e.preventDefault();
        this.runAction('open-settings');
        break;
      case '[':
        e.preventDefault();
        this.runAction('prev-page');
        break;
      case ']':
        e.preventDefault();
        this.runAction('next-page');
        break;
      case '=':
      case '+':
        e.preventDefault();
        this.runAction('zoom-in');
        break;
      case '-':
        if (!isRangeInput) {
          e.preventDefault();
          this.runAction('zoom-out');
        }
        break;
      default:
        if (key === 'Delete' || key === 'Backspace') {
          // Only delete page if focus is not on a button where Backspace/Enter may be expected, or explicitly handle Delete
          if (key === 'Delete' || (key === 'Backspace' && targetTag !== 'BUTTON')) {
            e.preventDefault();
            this.runAction('delete-page');
          }
        } else if (key === 'ArrowLeft' && !isRangeInput) {
          e.preventDefault();
          this.runAction('prev-page');
        } else if (key === 'ArrowRight' && !isRangeInput) {
          e.preventDefault();
          this.runAction('next-page');
        }
        break;
    }
  }
}

export function renderShortcutsModalContent(containerEl) {
  if (!containerEl) return;
  const renderRows = (list) => list.map(s => `
    <div class="shortcut-row">
      <div class="shortcut-meta">
        <span class="shortcut-category">${s.category}</span>
        <span class="shortcut-label">${s.label}</span>
      </div>
      <kbd class="kbd-badge">${s.key}</kbd>
    </div>
  `).join('');

  containerEl.innerHTML = `
    <div class="shortcuts-section">
      <h3 class="shortcuts-heading">10 Essential Actions</h3>
      <div class="shortcuts-grid">${renderRows(CORE_SHORTCUTS)}</div>
    </div>
    <div class="shortcuts-section">
      <h3 class="shortcuts-heading">Navigation &amp; Utilities</h3>
      <div class="shortcuts-grid">${renderRows(EXTRA_SHORTCUTS)}</div>
    </div>
  `;
}
