/**
 * State Management for ReportPDFmaker Web
 * Mirrors python pdf_maker/controller.py and settings_manager.py
 */

export const A4_PORTRAIT = [595.28, 841.89];
export const A4_LANDSCAPE = [841.89, 595.28];
export const LTR_PORTRAIT = [612.0, 792.0];
export const LTR_LANDSCAPE = [792.0, 612.0];

export const DEFAULT_SETTINGS = Object.freeze({
  pageSize: 'A4',               // 'A4' | 'Letter'
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
  skipCoverPage: false
});

export function getPageDimensions(landscape, pageSize = 'A4') {
  if (pageSize === 'Letter') {
    return landscape ? LTR_LANDSCAPE : LTR_PORTRAIT;
  }
  return landscape ? A4_LANDSCAPE : A4_PORTRAIT;
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

  addPages(newPages) {
    if (!newPages || newPages.length === 0) return;
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

    const [moved] = this.pages.splice(fromIndex, 1);
    this.pages.splice(toIndex, 0, moved);
    this.currentIndex = toIndex;
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', this.getCurrentPage());
  }

  removePage(index) {
    if (index < 0 || index >= this.pages.length) return;
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
    this.pages = [];
    this.currentIndex = -1;
    this.emit('pages_changed', this.pages);
    this.emit('page_selected', null);
  }

  updateCurrentPage(changes) {
    const page = this.getCurrentPage();
    if (!page) return;
    Object.assign(page, changes);
    this.emit('page_updated', page);
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
