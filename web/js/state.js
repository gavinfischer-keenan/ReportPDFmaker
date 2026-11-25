/**
 * State Management for ReportPDFmaker Web
 * Mirrors python pdf_maker/controller.py and settings_manager.py
 */

export const A4_PORTRAIT = [595.28, 841.89];
export const A4_LANDSCAPE = [841.89, 595.28];
export const LTR_PORTRAIT = [612.0, 792.0];
export const LTR_LANDSCAPE = [792.0, 612.0];

export const PAGE_SIZE_PRESETS = Object.freeze({
  A4: [595.28, 841.89],
  Letter: [612.0, 792.0],
  Legal: [612.0, 1008.0],
  A3: [841.89, 1190.55],
  A5: [419.53, 595.28]
});

export const DEFAULT_SETTINGS = Object.freeze({
  pageSize: 'A4',               // 'A4' | 'Letter' | 'Legal' | 'A3' | 'A5' | 'Fit'
  defaultOrientation: 'auto',   // 'auto' | 'portrait' | 'landscape'
  defaultImageFit: 'fill',      // 'fill' | 'margin'
  outputFilename: 'Report.pdf',
  exportQuality: 'archival',    // 'archival' | 'balanced' | 'compact'
  theme: 'dark',

  // Page numbering settings
  pageNumbers: false,
  pageNumberPosition: 'bottom',    // 'top' | 'bottom'
  pageNumberAlignment: 'center',   // 'left' | 'center' | 'right'
  pageNumberStyle: 'page_x_of_y',  // 'plain' | 'dashes' | 'page_x' | 'page_x_of_y'
  pageNumberFont: 'Helvetica',
  pageNumberFontSize: 10,
  pageNumberColor: '#1e293b',
  pageNumberOffsetEdge: 25,
  pageNumberOffsetSide: 45,
  skipCoverPage: false,

  // Overlays, export range & PDF metadata
  watermarkText: '',
  watermarkOpacity: 0.18,
  watermarkColor: '#64748b',
  headerText: '',
  footerText: '',
  exportPageRange: '',
  pdfTitle: '',
  pdfAuthor: '',
  pdfSubject: ''
});

export function getPageDimensions(landscape, pageSize = 'A4', pageItem = null) {
  if (pageSize === 'Fit' && pageItem?.sourceImage) {
    const natW = pageItem.sourceImage.naturalWidth || pageItem.sourceImage.width || 0;
    const natH = pageItem.sourceImage.naturalHeight || pageItem.sourceImage.height || 0;
    if (natW > 0 && natH > 0) {
      let sw = natW;
      let sh = natH;
      if (Array.isArray(pageItem.imageCrop) && pageItem.imageCrop.length === 4) {
        sw = Math.max(1, sw * Math.max(0.01, pageItem.imageCrop[2] - pageItem.imageCrop[0]));
        sh = Math.max(1, sh * Math.max(0.01, pageItem.imageCrop[3] - pageItem.imageCrop[1]));
      }
      const rot = ((Number(pageItem.imageRotation) || 0) % 360 + 360) % 360;
      const effW = (rot === 90 || rot === 270) ? sh : sw;
      const effH = (rot === 90 || rot === 270) ? sw : sh;
      const scale = 841.89 / Math.max(effW, effH);
      return [
        Math.max(72, Math.round(effW * scale * 100) / 100),
        Math.max(72, Math.round(effH * scale * 100) / 100)
      ];
    }
  }
  const [baseW, baseH] = PAGE_SIZE_PRESETS[pageSize] || A4_PORTRAIT;
  return landscape ? [baseH, baseW] : [baseW, baseH];
}

export class PageItem {
  constructor(opts = {}) {
    this.id = opts.id || 'p_' + Math.random().toString(36).substring(2, 10);
    this.name = opts.name || 'Untitled';
    this.sourceType = opts.sourceType || 'image'; // 'image' | 'pdf' | 'docx' | 'text' | '3d'

    // Page settings
    this.pageLandscape = Boolean(opts.pageLandscape);
    this.sourceLandscape = opts.sourceLandscape ?? this.pageLandscape;
    this.rotation = opts.rotation || 0; // 0, 90, 180, 270

    // Image-specific settings
    this.imageRotation = opts.imageRotation || 0; // 0, 90, 180, 270
    this.imageScale = opts.imageScale !== undefined ? opts.imageScale : 1.0;
    this.imageOffsetX = opts.imageOffsetX || 0.0; // points
    this.imageOffsetY = opts.imageOffsetY || 0.0; // points
    this.imageCrop = opts.imageCrop || null; // [left, top, right, bottom] 0.0 - 1.0

    // Data stores
    this.sourceImage = opts.sourceImage || null; // Image or Canvas
    this.thumbnailUrl = opts.thumbnailUrl || null;
    this.textContent = opts.textContent || '';
    this.textHeader = opts.textHeader || '';

    // For original PDF page embedding
    this.pdfBytes = opts.pdfBytes || null;
    this.pdfPageIndex = opts.pdfPageIndex ?? 0;
  }
}

class AppState {
  constructor() {
    this.pages = [];
    this.currentIndex = -1;
    this.editorMode = 'resize'; // 'resize' | 'crop'
    this.zoomLevel = 1.0;
    this.autoFit = true;

    this.settings = { ...DEFAULT_SETTINGS };
    this.recentItems = [];
    this.listeners = new Map();
    this._undoStack = [];
    this._redoStack = [];
    this._maxUndo = 50;

    this.loadSettings();
    this.loadRecentItems();
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event).push(callback);
  }

  emit(event, data) {
    if (this.listeners.has(event)) {
      for (const cb of this.listeners.get(event)) {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in listener for ${event}:`, err);
        }
      }
    }
  }

  loadSettings() {
    try {
      const saved = typeof localStorage !== 'undefined'
        ? localStorage.getItem('reportpdfmaker_settings')
        : null;
      if (saved) {
        const parsed = JSON.parse(saved);
        this.settings = { ...DEFAULT_SETTINGS, ...parsed };
      }
    } catch (e) {
      console.warn('Could not load settings from localStorage', e);
    }
  }

  saveSettings() {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('reportpdfmaker_settings', JSON.stringify(this.settings));
      }
    } catch (e) {
      console.warn('Could not save settings to localStorage', e);
    }
  }

  loadRecentItems() {
    try {
      const saved = typeof localStorage !== 'undefined'
        ? localStorage.getItem('reportpdfmaker_recents')
        : null;
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          this.recentItems = parsed.slice(0, 12);
        }
      }
    } catch {
      this.recentItems = [];
    }
  }

  saveRecentItems() {
    try {
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem('reportpdfmaker_recents', JSON.stringify(this.recentItems));
      }
    } catch {
      // Ignore storage quota errors
    }
  }

  recordRecent(item) {
    if (!item || !item.id) return;
    const entry = {
      id: String(item.id),
      type: item.type || 'action', // 'file' | 'page' | 'action'
      label: String(item.label || item.id),
      subtitle: item.subtitle ? String(item.subtitle) : '',
      actionId: item.actionId || null,
      pageId: item.pageId || null,
      timestamp: Date.now()
    };
    this.recentItems = [
      entry,
      ...this.recentItems.filter(r => r.id !== entry.id)
    ].slice(0, 12);
    this.saveRecentItems();
    this.emit('recents_updated', this.recentItems);
  }

  getCurrentPage() {
    if (this.currentIndex >= 0 && this.currentIndex < this.pages.length) {
      return this.pages[this.currentIndex];
    }
    return null;
  }

  _clonePages(pages) {
    return pages.map(p => new PageItem({
      ...p,
      imageCrop: Array.isArray(p.imageCrop) ? [...p.imageCrop] : null
    }));
  }

  _snapshot() {
    return {
      pages: this._clonePages(this.pages),
      currentIndex: this.currentIndex
    };
  }

  snapshotForUndo() {
    this._redoStack = [];
    this._undoStack.push(this._snapshot());
    if (this._undoStack.length > this._maxUndo) {
      this._undoStack.shift();
    }
    this.emit('history_changed', { canUndo: this.canUndo(), canRedo: this.canRedo() });
  }

  canUndo() {
    return this._undoStack.length > 0;
  }

  canRedo() {
    return this._redoStack.length > 0;
  }

  undo() {
    if (!this.canUndo()) return false;
    this._redoStack.push(this._snapshot());
    const prev = this._undoStack.pop();
    this.pages = this._clonePages(prev.pages);
    this.currentIndex = this.pages.length === 0
      ? -1
      : Math.max(0, Math.min(prev.currentIndex, this.pages.length - 1));
    this.emit('history_changed', { canUndo: this.canUndo(), canRedo: this.canRedo() });
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
    return true;
  }

  redo() {
    if (!this.canRedo()) return false;
    this._undoStack.push(this._snapshot());
    const next = this._redoStack.pop();
    this.pages = this._clonePages(next.pages);
    this.currentIndex = this.pages.length === 0
      ? -1
      : Math.max(0, Math.min(next.currentIndex, this.pages.length - 1));
    this.emit('history_changed', { canUndo: this.canUndo(), canRedo: this.canRedo() });
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
    return true;
  }

  setEditorMode(mode) {
    if ((mode === 'resize' || mode === 'crop') && this.editorMode !== mode) {
      this.editorMode = mode;
      this.emit('mode_changed', mode);
    }
  }

  addPages(newPages) {
    if (!newPages || newPages.length === 0) return;
    this.snapshotForUndo();
    this.pages.push(...newPages);
    if (this.currentIndex === -1) {
      this.currentIndex = 0;
    }
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  selectPage(index) {
    if (index >= 0 && index < this.pages.length) {
      this.currentIndex = index;
      const page = this.getCurrentPage();
      if (page) {
        this.recordRecent({
          id: `page:${page.id}`,
          type: 'page',
          label: page.name,
          subtitle: `Page ${index + 1} · ${page.sourceType.toUpperCase()}`,
          pageId: page.id
        });
      }
      this.emit('page_selected', page);
    }
  }

  movePage(fromIndex, toIndex) {
    if (fromIndex < 0 || fromIndex >= this.pages.length) return;
    if (toIndex < 0 || toIndex >= this.pages.length) return;
    if (fromIndex === toIndex) return;

    this.snapshotForUndo();
    const [moved] = this.pages.splice(fromIndex, 1);
    this.pages.splice(toIndex, 0, moved);
    this.currentIndex = toIndex;
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  removePage(index) {
    if (index < 0 || index >= this.pages.length) return;
    this.snapshotForUndo();
    this.pages.splice(index, 1);
    if (this.pages.length === 0) {
      this.currentIndex = -1;
    } else if (this.currentIndex >= this.pages.length) {
      this.currentIndex = this.pages.length - 1;
    }
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  clearAll() {
    if (this.pages.length > 0) {
      this.snapshotForUndo();
    }
    this.pages = [];
    this.currentIndex = -1;
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', null);
  }

  updateCurrentPage(changes, opts = { saveUndo: true }) {
    const page = this.getCurrentPage();
    if (!page) return;
    if (opts?.saveUndo !== false) {
      this.snapshotForUndo();
    }
    Object.assign(page, changes);
    this.emit('page_updated', page);
  }

  rotateAllPages(degrees) {
    if (this.pages.length === 0) return;
    this.snapshotForUndo();
    const norm = ((Number(degrees) || 0) % 360 + 360) % 360;
    for (const page of this.pages) {
      page.imageRotation = norm;
    }
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  setAllOrientation(landscape) {
    if (this.pages.length === 0) return;
    this.snapshotForUndo();
    const isLand = Boolean(landscape);
    for (const page of this.pages) {
      page.pageLandscape = isLand;
    }
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  duplicatePage(index) {
    if (index < 0 || index >= this.pages.length) return;
    this.snapshotForUndo();
    const orig = this.pages[index];
    const copy = new PageItem({
      ...orig,
      id: undefined,
      name: `${orig.name} (copy)`,
      imageCrop: Array.isArray(orig.imageCrop) ? [...orig.imageCrop] : null
    });
    this.pages.splice(index + 1, 0, copy);
    this.currentIndex = index + 1;
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  insertBlankPage(afterIndex = null, title = '', sourceImage = null, thumbnailUrl = null) {
    this.snapshotForUndo();
    const cleanTitle = String(title || '').trim();
    const blank = new PageItem({
      name: cleanTitle || 'Blank Page',
      sourceType: 'blank',
      textHeader: cleanTitle,
      sourceImage,
      thumbnailUrl,
      pageLandscape: false
    });
    const insertAt = (afterIndex === null || afterIndex === undefined || afterIndex < 0)
      ? this.pages.length
      : Math.min(this.pages.length, afterIndex + 1);
    this.pages.splice(insertAt, 0, blank);
    this.currentIndex = insertAt;
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  reversePages() {
    if (this.pages.length < 2) return;
    this.snapshotForUndo();
    const curId = this.getCurrentPage()?.id;
    this.pages.reverse();
    if (curId) {
      const nextIdx = this.pages.findIndex(p => p.id === curId);
      if (nextIdx >= 0) this.currentIndex = nextIdx;
    }
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  sortPagesByName(reverse = false) {
    if (this.pages.length < 2) return;
    this.snapshotForUndo();
    const curId = this.getCurrentPage()?.id;
    this.pages.sort((a, b) => {
      const cmp = String(a.name || '').localeCompare(String(b.name || ''), undefined, { numeric: true, sensitivity: 'base' });
      return reverse ? -cmp : cmp;
    });
    if (curId) {
      const nextIdx = this.pages.findIndex(p => p.id === curId);
      if (nextIdx >= 0) this.currentIndex = nextIdx;
    }
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  updateSettings(changes) {
    Object.assign(this.settings, changes);
    this.saveSettings();
    this.emit('settings_updated', this.settings);
  }

  resetSettings() {
    this.settings = { ...DEFAULT_SETTINGS };
    this.saveSettings();
    this.emit('settings_updated', this.settings);
  }
}

export const state = new AppState();
