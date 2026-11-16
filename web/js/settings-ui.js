/**
 * Settings UI Manager for ReportPDFmaker Web
 * Handles grouped settings, clear descriptions, sensible defaults,
 * change-diff tracking, save confirmation, and resetting to defaults.
 */

import { DEFAULT_SETTINGS } from './state.js';
import { escapeHtml } from './html-utils.js';

export const SETTING_META = {
  pageSize: {
    label: 'Page Size',
    group: 'Document Layout & Import Defaults',
    format: (v) => (v === 'Letter' ? 'US Letter (8.5 × 11 in)' : 'A4 (210 × 297 mm)')
  },
  defaultOrientation: {
    label: 'Default Orientation',
    group: 'Document Layout & Import Defaults',
    format: (v) => ({ auto: 'Auto (Match Source)', portrait: 'Portrait', landscape: 'Landscape' }[v] || v)
  },
  defaultImageFit: {
    label: 'Default Image Fit',
    group: 'Document Layout & Import Defaults',
    format: (v) => (v === 'margin' ? 'Fit with Margins' : 'Edge-to-Edge Fill')
  },
  pageNumbers: {
    label: 'Page Numbers',
    group: 'Page Numbering & Header/Footer',
    format: (v) => (v ? 'On' : 'Off')
  },
  skipCoverPage: {
    label: 'Skip Cover Page',
    group: 'Page Numbering & Header/Footer',
    format: (v) => (v ? 'Skip Page 1' : 'Include Page 1')
  },
  pageNumberPosition: {
    label: 'Position',
    group: 'Page Numbering & Header/Footer',
    format: (v) => (v === 'top' ? 'Top' : 'Bottom')
  },
  pageNumberAlignment: {
    label: 'Alignment',
    group: 'Page Numbering & Header/Footer',
    format: (v) => ({ left: 'Left', center: 'Center', right: 'Right' }[v] || v)
  },
  pageNumberStyle: {
    label: 'Number Format',
    group: 'Page Numbering & Header/Footer',
    format: (v) => ({ plain: '1, 2, 3', dashes: '— 1 —', page_x: 'Page 1', page_x_of_y: 'Page 1 of N' }[v] || v)
  },
  pageNumberFont: {
    label: 'Font Family',
    group: 'Page Numbering & Header/Footer',
    format: (v) => v
  },
  pageNumberFontSize: {
    label: 'Font Size',
    group: 'Page Numbering & Header/Footer',
    format: (v) => `${v} pt`
  },
  pageNumberColor: {
    label: 'Text Color',
    group: 'Page Numbering & Header/Footer',
    format: (v) => String(v).toUpperCase()
  },
  outputFilename: {
    label: 'Output Filename',
    group: 'Export, Quality & Appearance',
    format: (v) => v || 'Report.pdf'
  },
  exportQuality: {
    label: 'Export Quality',
    group: 'Export, Quality & Appearance',
    format: (v) => ({ archival: 'Archival (High DPI)', balanced: 'Balanced (150 DPI)', compact: 'Compact (Smaller File)' }[v] || v)
  },
  theme: {
    label: 'Appearance Theme',
    group: 'Export, Quality & Appearance',
    format: (v) => (v === 'light' ? 'Light' : 'Dark')
  }
};

export function computeSettingsDiff(prevSettings, nextSettings) {
  const diffs = [];
  for (const [key, meta] of Object.entries(SETTING_META)) {
    const prevVal = prevSettings?.[key];
    const nextVal = nextSettings?.[key];
    if (prevVal !== nextVal) {
      const from = meta.format(prevVal);
      const to = meta.format(nextVal);
      diffs.push({
        key,
        label: meta.label,
        from,
        to,
        summary: `${meta.label}: ${from} → ${to}`
      });
    }
  }
  return diffs;
}

export class SettingsUI {
  constructor({ state, onApplyTheme, onLayoutChanged }) {
    this.state = state;
    this.onApplyTheme = onApplyTheme;
    this.onLayoutChanged = onLayoutChanged;
    this.savedBaseline = { ...state.settings };
    this._quickTimer = null;

    this.bindQuickControls();
    this.bindSettingsModal();
    this.syncQuickControlsFromState();

    this.state.on('settings_updated', () => {
      this.syncQuickControlsFromState();
    });
  }

  bindQuickControls() {
    this.quickEls = {
      chkPageNumbers: document.getElementById('chk-page-numbers'),
      pageNumbersConfig: document.getElementById('page-numbers-config'),
      selectNumberPos: document.getElementById('num-position'),
      selectNumberAlign: document.getElementById('num-alignment'),
      selectNumberStyle: document.getElementById('num-style'),
      selectNumberFont: document.getElementById('num-font'),
      inputNumberSize: document.getElementById('num-size'),
      inputNumberColor: document.getElementById('num-color'),
      chkSkipCover: document.getElementById('chk-skip-cover'),
      selectPageSize: document.getElementById('doc-page-size'),
      selectExportQuality: document.getElementById('doc-export-quality'),
      inputFilename: document.getElementById('doc-filename'),
      quickBanner: document.getElementById('settings-quick-banner')
    };

    const applyQuick = (patch, relayout = false) => {
      const prev = { ...this.state.settings };
      this.state.updateSettings(patch);
      this.savedBaseline = { ...this.state.settings };
      if (relayout) this.onLayoutChanged?.();
      const diffs = computeSettingsDiff(prev, this.state.settings);
      if (diffs.length > 0) {
        this.showQuickConfirmation(diffs);
      }
    };

    this.quickEls.chkPageNumbers?.addEventListener('change', (e) => {
      applyQuick({ pageNumbers: e.target.checked });
    });
    this.quickEls.selectNumberPos?.addEventListener('change', (e) => {
      applyQuick({ pageNumberPosition: e.target.value });
    });
    this.quickEls.selectNumberAlign?.addEventListener('change', (e) => {
      applyQuick({ pageNumberAlignment: e.target.value });
    });
    this.quickEls.selectNumberStyle?.addEventListener('change', (e) => {
      applyQuick({ pageNumberStyle: e.target.value });
    });
    this.quickEls.selectNumberFont?.addEventListener('change', (e) => {
      applyQuick({ pageNumberFont: e.target.value });
    });
    this.quickEls.inputNumberSize?.addEventListener('change', (e) => {
      const clamped = Math.max(6, Math.min(36, parseInt(e.target.value, 10) || 10));
      applyQuick({ pageNumberFontSize: clamped });
    });
    this.quickEls.inputNumberColor?.addEventListener('change', (e) => {
      applyQuick({ pageNumberColor: e.target.value });
    });
    this.quickEls.chkSkipCover?.addEventListener('change', (e) => {
      applyQuick({ skipCoverPage: e.target.checked });
    });
    this.quickEls.selectPageSize?.addEventListener('change', (e) => {
      applyQuick({ pageSize: e.target.value }, true);
    });
    this.quickEls.selectExportQuality?.addEventListener('change', (e) => {
      applyQuick({ exportQuality: e.target.value });
    });
    this.quickEls.inputFilename?.addEventListener('change', (e) => {
      const clean = e.target.value.trim() || 'Report.pdf';
      applyQuick({ outputFilename: clean });
    });
    this.quickEls.inputFilename?.addEventListener('input', (e) => {
      // Keep state synced live without flashing toast on every keystroke
      this.state.settings.outputFilename = e.target.value;
      this.state.saveSettings();
    });
  }

  syncQuickControlsFromState() {
    const s = this.state.settings;
    const q = this.quickEls;
    if (!q) return;

    if (q.chkPageNumbers) q.chkPageNumbers.checked = Boolean(s.pageNumbers);
    if (q.pageNumbersConfig) q.pageNumbersConfig.classList.toggle('hidden', !s.pageNumbers);
    if (q.selectNumberPos) q.selectNumberPos.value = s.pageNumberPosition || 'bottom';
    if (q.selectNumberAlign) q.selectNumberAlign.value = s.pageNumberAlignment || 'center';
    if (q.selectNumberStyle) q.selectNumberStyle.value = s.pageNumberStyle || 'page_x_of_y';
    if (q.selectNumberFont) q.selectNumberFont.value = s.pageNumberFont || 'Helvetica';
    if (q.inputNumberSize) q.inputNumberSize.value = s.pageNumberFontSize || 10;
    if (q.inputNumberColor) q.inputNumberColor.value = s.pageNumberColor || '#1e293b';
    if (q.chkSkipCover) q.chkSkipCover.checked = Boolean(s.skipCoverPage);
    if (q.selectPageSize) q.selectPageSize.value = s.pageSize || 'A4';
    if (q.selectExportQuality) q.selectExportQuality.value = s.exportQuality || 'archival';
    if (q.inputFilename && document.activeElement !== q.inputFilename) {
      q.inputFilename.value = s.outputFilename || 'Report.pdf';
    }
  }

  showQuickConfirmation(diffs) {
    const banner = this.quickEls.quickBanner;
    if (!banner) return;
    const summary = diffs.map(d => d.summary).join(' · ');
    banner.innerHTML = `<span class="save-badge-dot">✓</span> Saved: <strong>${escapeHtml(summary)}</strong>`;
    banner.classList.remove('hidden');
    clearTimeout(this._quickTimer);
    this._quickTimer = setTimeout(() => {
      banner.classList.add('hidden');
    }, 4000);
  }

  bindSettingsModal() {
    this.modal = document.getElementById('modal-settings');
    this.btnOpen = document.getElementById('btn-open-settings');
    this.btnOpenQuick = document.getElementById('btn-open-full-settings');
    this.btnClose = document.getElementById('btn-close-settings');
    this.btnCancel = document.getElementById('btn-cancel-settings');
    this.btnSave = document.getElementById('btn-save-settings');
    this.btnReset = document.getElementById('btn-reset-settings');
    this.pendingDiffEl = document.getElementById('settings-pending-diff');
    this.saveBannerEl = document.getElementById('settings-save-banner');

    this.modalInputs = {
      pageSize: document.getElementById('set-page-size'),
      defaultOrientation: document.getElementById('set-default-orientation'),
      defaultImageFit: document.getElementById('set-default-image-fit'),
      pageNumbers: document.getElementById('set-page-numbers'),
      skipCoverPage: document.getElementById('set-skip-cover'),
      pageNumberPosition: document.getElementById('set-num-position'),
      pageNumberAlignment: document.getElementById('set-num-alignment'),
      pageNumberStyle: document.getElementById('set-num-style'),
      pageNumberFont: document.getElementById('set-num-font'),
      pageNumberFontSize: document.getElementById('set-num-size'),
      pageNumberColor: document.getElementById('set-num-color'),
      outputFilename: document.getElementById('set-output-filename'),
      exportQuality: document.getElementById('set-export-quality'),
      theme: document.getElementById('set-theme')
    };

    this.btnOpen?.addEventListener('click', () => this.openModal());
    this.btnOpenQuick?.addEventListener('click', () => this.openModal());
    this.btnClose?.addEventListener('click', () => this.closeModal());
    this.btnCancel?.addEventListener('click', () => this.closeModal());
    this.modal?.addEventListener('click', (e) => {
      if (e.target === this.modal) this.closeModal();
    });

    Object.values(this.modalInputs).forEach(el => {
      if (!el) return;
      el.addEventListener('input', () => this.updatePendingDiffPreview());
      el.addEventListener('change', () => this.updatePendingDiffPreview());
    });

    this.btnReset?.addEventListener('click', () => {
      this.populateModalFromValues(DEFAULT_SETTINGS);
      this.updatePendingDiffPreview();
    });

    this.btnSave?.addEventListener('click', () => this.saveModalSettings());
  }

  openModal() {
    if (!this.modal) return;
    this.savedBaseline = { ...this.state.settings };
    this.populateModalFromValues(this.state.settings);
    this.saveBannerEl?.classList.add('hidden');
    this.updatePendingDiffPreview();
    this.modal.classList.remove('hidden');
  }

  closeModal() {
    this.modal?.classList.add('hidden');
  }

  populateModalFromValues(values) {
    const m = this.modalInputs;
    if (m.pageSize) m.pageSize.value = values.pageSize || 'A4';
    if (m.defaultOrientation) m.defaultOrientation.value = values.defaultOrientation || 'auto';
    if (m.defaultImageFit) m.defaultImageFit.value = values.defaultImageFit || 'fill';
    if (m.pageNumbers) m.pageNumbers.checked = Boolean(values.pageNumbers);
    if (m.skipCoverPage) m.skipCoverPage.checked = Boolean(values.skipCoverPage);
    if (m.pageNumberPosition) m.pageNumberPosition.value = values.pageNumberPosition || 'bottom';
    if (m.pageNumberAlignment) m.pageNumberAlignment.value = values.pageNumberAlignment || 'center';
    if (m.pageNumberStyle) m.pageNumberStyle.value = values.pageNumberStyle || 'page_x_of_y';
    if (m.pageNumberFont) m.pageNumberFont.value = values.pageNumberFont || 'Helvetica';
    if (m.pageNumberFontSize) m.pageNumberFontSize.value = values.pageNumberFontSize || 10;
    if (m.pageNumberColor) m.pageNumberColor.value = values.pageNumberColor || '#1e293b';
    if (m.outputFilename) m.outputFilename.value = values.outputFilename || 'Report.pdf';
    if (m.exportQuality) m.exportQuality.value = values.exportQuality || 'archival';
    if (m.theme) m.theme.value = values.theme || 'dark';
  }

  readModalValues() {
    const m = this.modalInputs;
    return {
      ...this.state.settings,
      pageSize: m.pageSize?.value || 'A4',
      defaultOrientation: m.defaultOrientation?.value || 'auto',
      defaultImageFit: m.defaultImageFit?.value || 'fill',
      pageNumbers: Boolean(m.pageNumbers?.checked),
      skipCoverPage: Boolean(m.skipCoverPage?.checked),
      pageNumberPosition: m.pageNumberPosition?.value || 'bottom',
      pageNumberAlignment: m.pageNumberAlignment?.value || 'center',
      pageNumberStyle: m.pageNumberStyle?.value || 'page_x_of_y',
      pageNumberFont: m.pageNumberFont?.value || 'Helvetica',
      pageNumberFontSize: Math.max(6, Math.min(36, parseInt(m.pageNumberFontSize?.value, 10) || 10)),
      pageNumberColor: m.pageNumberColor?.value || '#1e293b',
      outputFilename: (m.outputFilename?.value || '').trim() || 'Report.pdf',
      exportQuality: m.exportQuality?.value || 'archival',
      theme: m.theme?.value || 'dark'
    };
  }

  updatePendingDiffPreview() {
    if (!this.pendingDiffEl) return;
    const draft = this.readModalValues();
    const diffs = computeSettingsDiff(this.savedBaseline, draft);
    if (diffs.length === 0) {
      this.pendingDiffEl.innerHTML = `<span class="text-muted">No unsaved changes.</span>`;
    } else {
      const items = diffs.map(d => `<li><strong>${escapeHtml(d.label)}:</strong> ${escapeHtml(d.from)} → ${escapeHtml(d.to)}</li>`).join('');
      this.pendingDiffEl.innerHTML = `
        <div class="pending-diff-title">${diffs.length} pending change${diffs.length === 1 ? '' : 's'}:</div>
        <ul class="pending-diff-list">${items}</ul>
      `;
    }
  }

  saveModalSettings() {
    const draft = this.readModalValues();
    const diffs = computeSettingsDiff(this.savedBaseline, draft);

    this.state.updateSettings(draft);
    if (draft.theme !== this.savedBaseline.theme) {
      this.onApplyTheme?.(draft.theme);
    }
    this.savedBaseline = { ...this.state.settings };
    this.onLayoutChanged?.();
    this.updatePendingDiffPreview();

    if (this.saveBannerEl) {
      if (diffs.length > 0) {
        const list = diffs.map(d => `<li>${escapeHtml(d.summary)}</li>`).join('');
        this.saveBannerEl.innerHTML = `
          <div><strong>✓ Saved ${diffs.length} change${diffs.length === 1 ? '' : 's'}:</strong></div>
          <ul class="save-diff-list">${list}</ul>
        `;
      } else {
        this.saveBannerEl.innerHTML = `<div><strong>✓ Settings saved</strong> (all values already matched defaults/saved state).</div>`;
      }
      this.saveBannerEl.classList.remove('hidden');
    }

    if (diffs.length > 0) {
      this.showQuickConfirmation(diffs);
    }
  }
}
