/**
 * Command Palette (Cmd/Ctrl + K) for ReportPDFmaker Web
 * Searches pages, views/modals, actions, and recent items.
 */

import { escapeHtml } from './html-utils.js';
import { ModalFocusTrap } from './ui-feedback.js';

export function scorePaletteItem(item, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return 1;

  const label = String(item.label || '').toLowerCase();
  const subtitle = String(item.subtitle || '').toLowerCase();
  const category = String(item.category || '').toLowerCase();
  const keywords = String(item.keywords || '').toLowerCase();
  const haystack = `${label} ${subtitle} ${category} ${keywords}`;

  if (label === q) return 120;
  if (label.startsWith(q)) return 100;
  if (label.includes(` ${q}`)) return 85;
  if (label.includes(q)) return 70;
  if (haystack.includes(q)) return 50;

  // Multi-term AND matching
  const terms = q.split(/\s+/).filter(Boolean);
  if (terms.length > 1 && terms.every(t => haystack.includes(t))) {
    return 45;
  }

  // Ordered subsequence fuzzy match on label
  let qi = 0;
  for (let i = 0; i < label.length && qi < q.length; i++) {
    if (label[i] === q[qi]) qi++;
  }
  if (qi === q.length && q.length >= 2) return 20;

  return 0;
}

export function filterPaletteItems(items, query) {
  const q = String(query || '').trim();
  const scored = [];
  for (const item of items) {
    const score = scorePaletteItem(item, q);
    if (score > 0) {
      scored.push({ item, score });
    }
  }
  if (q) {
    scored.sort((a, b) => b.score - a.score);
  }
  return scored.map(entry => entry.item);
}

export class CommandPalette {
  constructor({ state, getActions, onSelectPage, onNavigateView, onRunAction }) {
    this.state = state;
    this.getActions = getActions;
    this.onSelectPage = onSelectPage;
    this.onNavigateView = onNavigateView;
    this.onRunAction = onRunAction;

    this.modal = document.getElementById('modal-command-palette');
    this.input = document.getElementById('cmd-palette-input');
    this.resultsEl = document.getElementById('cmd-palette-results');
    this.closeBtn = document.getElementById('btn-close-palette');

    this.filteredItems = [];
    this.activeIndex = 0;
    this.focusTrap = new ModalFocusTrap();

    this.bindEvents();
  }

  bindEvents() {
    if (!this.modal || !this.input || !this.resultsEl) return;

    this.closeBtn?.addEventListener('click', () => this.close());

    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) this.close();
    });

    this.input.addEventListener('input', () => {
      this.activeIndex = 0;
      this.render();
    });

    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (this.filteredItems.length > 0) {
          this.activeIndex = (this.activeIndex + 1) % this.filteredItems.length;
          this.updateActiveSelection();
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (this.filteredItems.length > 0) {
          this.activeIndex = (this.activeIndex - 1 + this.filteredItems.length) % this.filteredItems.length;
          this.updateActiveSelection();
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const chosen = this.filteredItems[this.activeIndex];
        if (chosen && !chosen.disabled) {
          this.executeItem(chosen);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        this.close();
      }
    });
  }

  isOpen() {
    return Boolean(this.modal && !this.modal.classList.contains('hidden'));
  }

  open() {
    if (!this.modal) return;
    this.modal.classList.remove('hidden');
    this.input.value = '';
    this.activeIndex = 0;
    this.render();
    this.focusTrap.activate(this.modal);
    setTimeout(() => this.input?.focus(), 20);
  }

  close() {
    if (!this.modal) return;
    this.modal.classList.add('hidden');
    this.focusTrap.deactivate(true);
  }

  toggle() {
    if (this.isOpen()) this.close();
    else this.open();
  }

  buildItems() {
    const items = [];
    const pages = this.state.pages || [];
    const recents = this.state.recentItems || [];

    // 1. Recent items
    for (const r of recents) {
      if (r.type === 'page') {
        const idx = pages.findIndex(p => p.id === r.pageId);
        if (idx === -1) continue;
        items.push({
          id: `recent:${r.id}`,
          category: 'Recent',
          icon: '🕒',
          label: r.label,
          subtitle: `Recent page · #${idx + 1}`,
          keywords: 'recent page jump',
          kind: 'page',
          pageIndex: idx
        });
      } else if (r.actionId) {
        items.push({
          id: `recent:${r.id}`,
          category: 'Recent',
          icon: '🕒',
          label: r.label,
          subtitle: r.subtitle || 'Recent action',
          keywords: 'recent action',
          kind: 'action',
          actionId: r.actionId
        });
      }
    }

    // 2. Document Pages
    pages.forEach((p, idx) => {
      items.push({
        id: `page:${p.id}`,
        category: 'Pages',
        icon: p.sourceType === 'pdf' ? '📕' : p.sourceType === 'text' ? '📋' : p.sourceType === 'docx' ? '📄' : p.sourceType === '3d' ? '🎲' : '🖼️',
        label: `Page ${idx + 1}: ${p.name}`,
        subtitle: `${p.sourceType.toUpperCase()} · ${p.pageLandscape ? 'Landscape' : 'Portrait'}`,
        keywords: `page ${idx + 1} ${p.sourceType} ${p.pageLandscape ? 'landscape' : 'portrait'}`,
        kind: 'page',
        pageIndex: idx
      });
    });

    // 3. Views / Panels / Modals
    const views = [
      { id: 'view:pages', icon: '📋', label: 'View: Document Pages Queue', subtitle: 'Open page list and drag-drop queue', keywords: 'panel pages queue list', viewId: 'pages' },
      { id: 'view:preview', icon: '👁️', label: 'View: Interactive Canvas Preview', subtitle: 'Inspect, zoom, and resize page content', keywords: 'panel preview canvas zoom', viewId: 'preview' },
      { id: 'view:editor', icon: '✏️', label: 'View: Page & Document Editor', subtitle: 'Orientation, rotation, scale, and quick settings', keywords: 'panel editor inspector', viewId: 'editor' },
      { id: 'view:settings', icon: '⚙️', label: 'Settings: Document & Page Numbering', subtitle: 'Configure page size, defaults, numbering, and export quality', keywords: 'preferences config settings numbering', viewId: 'settings', shortcut: 'G' },
      { id: 'view:shrink', icon: '🗜️', label: 'Tool: Shrink / Compress PDF', subtitle: 'Compress an existing PDF locally in-browser', keywords: 'compress optimize shrink pdf', viewId: 'shrink', shortcut: 'S' },
      { id: 'view:shortcuts', icon: '⌨️', label: 'Help: Keyboard Shortcuts', subtitle: 'View all keyboard shortcuts', keywords: 'help shortcuts hotkeys keys', viewId: 'shortcuts', shortcut: '?' }
    ];
    for (const v of views) {
      items.push({ ...v, category: 'Pages & Views', kind: 'view' });
    }

    // 4. Actions
    const actions = this.getActions ? this.getActions() : [];
    for (const act of actions) {
      items.push({
        id: `action:${act.id}`,
        category: 'Actions',
        icon: act.icon || '⚡',
        label: act.label,
        subtitle: act.subtitle || '',
        keywords: act.keywords || '',
        shortcut: act.shortcut || '',
        disabled: Boolean(act.disabled),
        kind: 'action',
        actionId: act.id
      });
    }

    return items;
  }

  render() {
    if (!this.resultsEl) return;
    const query = this.input?.value || '';
    const allItems = this.buildItems();
    this.filteredItems = filterPaletteItems(allItems, query);

    if (this.activeIndex >= this.filteredItems.length) {
      this.activeIndex = 0;
    }

    if (this.filteredItems.length === 0) {
      this.resultsEl.innerHTML = `
        <div class="empty-state-card palette-empty">
          <div class="empty-state-icon">🔎</div>
          <div class="empty-state-title">No matching commands or pages</div>
          <p class="empty-state-desc">
            Search across imported pages, workspace panels, settings, recent items, or quick actions like <strong>rotate</strong>, <strong>sample</strong>, or <strong>shrink</strong>.
          </p>
          <button type="button" id="btn-clear-palette-search" class="btn btn-secondary btn-sm">Clear Search</button>
        </div>
      `;
      document.getElementById('btn-clear-palette-search')?.addEventListener('click', () => {
        this.input.value = '';
        this.activeIndex = 0;
        this.render();
        this.input.focus();
      });
      return;
    }

    // Group items by category preserving display order
    const groups = new Map();
    this.filteredItems.forEach((item, flatIdx) => {
      const cat = item.category || 'Results';
      if (!groups.has(cat)) groups.set(cat, []);
      groups.get(cat).push({ item, flatIdx });
    });

    let html = '';
    for (const [cat, entries] of groups.entries()) {
      html += `<div class="palette-group-label">${escapeHtml(cat)}</div>`;
      for (const { item, flatIdx } of entries) {
        const isActive = flatIdx === this.activeIndex;
        const disabledAttr = item.disabled ? 'aria-disabled="true"' : '';
        html += `
          <button type="button"
            class="palette-item ${isActive ? 'active' : ''} ${item.disabled ? 'disabled' : ''}"
            data-flat-idx="${flatIdx}"
            ${disabledAttr}>
            <span class="palette-item-icon">${escapeHtml(item.icon || '⚡')}</span>
            <span class="palette-item-text">
              <span class="palette-item-title">${escapeHtml(item.label)}</span>
              ${item.subtitle ? `<span class="palette-item-sub">${escapeHtml(item.subtitle)}</span>` : ''}
            </span>
            ${item.shortcut ? `<kbd class="kbd-badge">${escapeHtml(item.shortcut)}</kbd>` : ''}
          </button>
        `;
      }
    }

    this.resultsEl.innerHTML = html;

    this.resultsEl.querySelectorAll('.palette-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx = parseInt(btn.dataset.flatIdx, 10);
        const item = this.filteredItems[idx];
        if (item && !item.disabled) {
          this.executeItem(item);
        }
      });
    });
  }

  updateActiveSelection() {
    const buttons = this.resultsEl.querySelectorAll('.palette-item');
    buttons.forEach(btn => {
      const idx = parseInt(btn.dataset.flatIdx, 10);
      const active = idx === this.activeIndex;
      btn.classList.toggle('active', active);
      if (active) {
        btn.scrollIntoView({ block: 'nearest' });
      }
    });
  }

  executeItem(item) {
    this.close();
    if (item.kind === 'page') {
      this.onSelectPage?.(item.pageIndex);
    } else if (item.kind === 'view') {
      this.onNavigateView?.(item.viewId);
    } else if (item.kind === 'action') {
      this.onRunAction?.(item.actionId);
    }
  }
}
