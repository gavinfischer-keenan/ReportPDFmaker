/**
 * Main Application Controller for ReportPDFmaker Web
 * 100% Client-Side SPA
 */

import { escapeHtml } from './html-utils.js';
import { state } from './state.js';
import { formatFileSize } from './math-utils.js';
import {
  convertImageFile,
  convertPdfFile,
  convertDocxFile,
  convertTextFile,
  loadImage
} from './converters.js';
import { CanvasPreview } from './canvas-preview.js';
import { buildPdfDocument, downloadPdf } from './pdf-builder.js';
import { compressPdf } from './pdf-compressor.js';
import { ThreeViewerModal } from './three-viewer.js';
import { CommandPalette } from './command-palette.js';
import { ShortcutManager, renderShortcutsModalContent } from './shortcuts.js';
import { SettingsUI } from './settings-ui.js';
import { createSampleReportPages, createSamplePdfFile } from './sample-generator.js';
import { showToast, confirmDialog, ModalFocusTrap } from './ui-feedback.js';
import {
  serializeSessionPages,
  deserializeSessionPages,
  saveSessionToIdb,
  loadSessionFromIdb,
  clearSessionFromIdb
} from './session-store.js';

document.addEventListener('DOMContentLoaded', () => {
  // Core DOM Elements
  const workspaceEl = document.querySelector('.app-workspace');
  const mobileTabBtns = document.querySelectorAll('.mobile-tab-btn');
  const mobileTabCount = document.getElementById('mobile-tab-count');

  const fileInput = document.getElementById('file-input');
  const btnAddFiles = document.getElementById('btn-add-files');
  const btnClearAll = document.getElementById('btn-clear-all');
  const pagesListEl = document.getElementById('pages-list');
  const pageCountBadge = document.getElementById('page-count-badge');
  const dropZone = document.getElementById('drop-zone');

  // Empty State CTA buttons
  const previewEmptyState = document.getElementById('preview-empty-state');
  const btnEmptyAddFiles = document.getElementById('btn-empty-add-files');
  const btnEmptyLoadSample = document.getElementById('btn-empty-load-sample');
  const btnEditorAddFiles = document.getElementById('btn-editor-add-files');
  const btnEditorLoadSample = document.getElementById('btn-editor-load-sample');

  // Navigation & Zoom
  const btnPrevPage = document.getElementById('btn-prev-page');
  const btnNextPage = document.getElementById('btn-next-page');
  const pageIndicator = document.getElementById('page-indicator');
  const btnZoomIn = document.getElementById('btn-zoom-in');
  const btnZoomOut = document.getElementById('btn-zoom-out');
  const btnZoomFit = document.getElementById('btn-zoom-fit');
  const zoomLevelLabel = document.getElementById('zoom-level-label');

  // Page Editor Sidebar
  const emptyEditorMessage = document.getElementById('empty-editor-message');
  const pageEditorControls = document.getElementById('page-editor-controls');
  const entireDocControls = document.getElementById('entire-doc-controls');
  const btnUndo = document.getElementById('btn-undo');
  const btnRedo = document.getElementById('btn-redo');
  const btnModeResize = document.getElementById('btn-mode-resize');
  const btnModeCrop = document.getElementById('btn-mode-crop');
  const btnApplyCrop = document.getElementById('btn-apply-crop');
  const btnRotate0 = document.getElementById('btn-rotate-0');
  const btnRotate90 = document.getElementById('btn-rotate-90');
  const btnRotate180 = document.getElementById('btn-rotate-180');
  const btnRotate270 = document.getElementById('btn-rotate-270');
  const rotButtons = [btnRotate0, btnRotate90, btnRotate180, btnRotate270];
  const btnRotateAll0 = document.getElementById('btn-rotate-all-0');
  const btnRotateAll90 = document.getElementById('btn-rotate-all-90');
  const btnRotateAll180 = document.getElementById('btn-rotate-all-180');
  const btnRotateAll270 = document.getElementById('btn-rotate-all-270');
  const btnAllPortrait = document.getElementById('btn-all-portrait');
  const btnAllLandscape = document.getElementById('btn-all-landscape');
  const radioPortrait = document.getElementById('orient-portrait');
  const radioLandscape = document.getElementById('orient-landscape');
  const btnFitScale = document.getElementById('btn-fit-scale');
  const scaleSlider = document.getElementById('scale-slider');
  const scaleValueLabel = document.getElementById('scale-value-label');
  const btnMoveUp = document.getElementById('btn-move-up');
  const btnMoveDown = document.getElementById('btn-move-down');
  const btnDuplicatePage = document.getElementById('btn-duplicate-page');
  const btnInsertBlank = document.getElementById('btn-insert-blank');
  const btnDeletePage = document.getElementById('btn-delete-page');
  const btnReversePages = document.getElementById('btn-reverse-pages');
  const btnSortPages = document.getElementById('btn-sort-pages');

  // Header Controls & Export
  const btnCommandPalette = document.getElementById('btn-command-palette');
  const btnShortcuts = document.getElementById('btn-shortcuts');
  const btnExportPdf = document.getElementById('btn-export-pdf');
  const themeToggle = document.getElementById('theme-toggle');

  // Progress Banner
  const progressBarContainer = document.getElementById('import-progress-container');
  const progressBarFill = document.getElementById('import-progress-fill');
  const progressBarText = document.getElementById('import-progress-text');

  // Shortcuts Modal
  const shortcutsModal = document.getElementById('modal-shortcuts');
  const shortcutsModalBody = document.getElementById('shortcuts-modal-body');
  const btnCloseShortcuts = document.getElementById('btn-close-shortcuts');
  const btnDoneShortcuts = document.getElementById('btn-done-shortcuts');

  // Shrink PDF Modal
  const btnShrinkPdf = document.getElementById('btn-shrink-pdf');
  const shrinkModal = document.getElementById('modal-shrink');
  const btnCloseShrink = document.getElementById('btn-close-shrink');
  const shrinkFileInput = document.getElementById('shrink-file-input');
  const shrinkDropZone = document.getElementById('shrink-drop-zone');
  const shrinkEmptyHelper = document.getElementById('shrink-empty-helper');
  const btnShrinkBrowse = document.getElementById('btn-shrink-browse');
  const btnShrinkSample = document.getElementById('btn-shrink-sample');
  const shrinkFileDetails = document.getElementById('shrink-file-details');
  const shrinkFileName = document.getElementById('shrink-file-name');
  const shrinkFileSize = document.getElementById('shrink-file-size');
  const btnStartCompress = document.getElementById('btn-start-compress');
  const shrinkProgress = document.getElementById('shrink-progress');
  const shrinkProgressBar = document.getElementById('shrink-progress-bar');
  const shrinkProgressText = document.getElementById('shrink-progress-text');
  const shrinkResult = document.getElementById('shrink-result');
  const shrinkResultDetails = document.getElementById('shrink-result-details');
  const btnDownloadShrunk = document.getElementById('btn-download-shrunk');

  let shrinkSelectedFile = null;
  let compressedPdfResult = null;

  // Initialize Preview Canvas & 3D Viewer
  const preview = new CanvasPreview('canvas-container', (zoom) => {
    zoomLevelLabel.textContent = `${Math.round(zoom * 100)}%`;
  });
  const threeModal = new ThreeViewerModal('modal-3d', 'three-container');

  // --------------------------------------------------------------------------
  // Mobile / Tablet Pane Switching
  // --------------------------------------------------------------------------
  function setActivePane(pane) {
    if (!workspaceEl) return;
    workspaceEl.dataset.activePane = pane;
    mobileTabBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.pane === pane);
    });
    if (pane === 'preview') {
      requestAnimationFrame(() => {
        if (preview.autoFit) preview.fitToContainer();
        preview.render();
      });
    }
  }

  mobileTabBtns.forEach(btn => {
    btn.addEventListener('click', () => setActivePane(btn.dataset.pane));
  });

  // --------------------------------------------------------------------------
  // Theme Management
  // --------------------------------------------------------------------------
  function applyTheme(theme) {
    const resolved = theme === 'light' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', resolved);
    if (state.settings.theme !== resolved) {
      state.updateSettings({ theme: resolved });
    }
    themeToggle.textContent = resolved === 'dark' ? '☀️' : '🌙';
  }
  applyTheme(state.settings.theme || 'dark');

  themeToggle.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme');
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  });

  // --------------------------------------------------------------------------
  // Settings UI (Grouped, Described, Diff Confirmation)
  // --------------------------------------------------------------------------
  const settingsUI = new SettingsUI({
    state,
    onApplyTheme: applyTheme,
    onLayoutChanged: () => {
      if (preview.autoFit) preview.fitToContainer();
      preview.render();
    }
  });

  // --------------------------------------------------------------------------
  // Sample Report Loading
  // --------------------------------------------------------------------------
  async function loadSampleReport() {
    try {
      progressBarContainer.classList.remove('hidden');
      progressBarFill.style.width = '40%';
      progressBarText.textContent = 'Generating 3-page sample report…';

      const samplePages = await createSampleReportPages();
      progressBarFill.style.width = '100%';
      progressBarText.textContent = 'Sample report ready!';

      state.addPages(samplePages);
      state.recordRecent({
        id: 'action:load-sample',
        type: 'action',
        label: 'Load 3-Page Sample Report',
        subtitle: 'Template with cover, landscape chart & appendix',
        actionId: 'load-sample'
      });

      if (window.innerWidth <= 960) {
        setActivePane('preview');
      }
    } catch (err) {
      console.error('Failed to load sample report:', err);
      showToast('Could not generate sample report: ' + err.message, 'error');
    } finally {
      setTimeout(() => progressBarContainer.classList.add('hidden'), 600);
    }
  }

  btnEmptyAddFiles?.addEventListener('click', () => fileInput.click());
  btnEditorAddFiles?.addEventListener('click', () => fileInput.click());
  btnEmptyLoadSample?.addEventListener('click', loadSampleReport);
  btnEditorLoadSample?.addEventListener('click', loadSampleReport);

  // --------------------------------------------------------------------------
  // File Import & Drag/Drop
  // --------------------------------------------------------------------------
  function triggerAddFiles() {
    fileInput.click();
  }

  btnAddFiles.addEventListener('click', triggerAddFiles);
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
      fileInput.value = '';
    }
  });

  dropZone.addEventListener('click', triggerAddFiles);
  dropZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      triggerAddFiles();
    }
  });

  ['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add('drag-active');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove('drag-active');
    });
  });

  dropZone.addEventListener('drop', (e) => {
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  });

  async function handleFiles(files) {
    progressBarContainer.classList.remove('hidden');
    const total = files.length;
    const addedPages = [];
    const orientPref = state.settings.defaultOrientation || 'auto';

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.split('.').pop().toLowerCase();

      progressBarFill.style.width = `${Math.round((i / total) * 100)}%`;
      progressBarText.textContent = `Importing ${file.name} (${i + 1}/${total})…`;

      try {
        let converted = [];
        if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)) {
          converted = [await convertImageFile(file)];
        } else if (ext === 'pdf') {
          converted = await convertPdfFile(file);
        } else if (ext === 'docx') {
          converted = await convertDocxFile(file);
        } else if (['txt', 'md', 'csv', 'log', 'json'].includes(ext)) {
          converted = await convertTextFile(file);
        } else if (['gltf', 'glb'].includes(ext)) {
          await threeModal.loadModel(file, (capturedPage) => {
            if (orientPref === 'portrait') capturedPage.pageLandscape = false;
            else if (orientPref === 'landscape') capturedPage.pageLandscape = true;
            state.addPages([capturedPage]);
          });
        } else {
          console.warn(`Unsupported file format: ${file.name}`);
        }

        if (converted.length > 0) {
          for (const p of converted) {
            if (orientPref === 'portrait') p.pageLandscape = false;
            else if (orientPref === 'landscape') p.pageLandscape = true;
          }
          addedPages.push(...converted);
          state.recordRecent({
            id: `file:${file.name}`,
            type: 'file',
            label: `Imported ${file.name}`,
            subtitle: `${converted.length} page${converted.length === 1 ? '' : 's'}`,
            pageId: converted[0].id
          });
        }
      } catch (err) {
        console.error(`Error processing ${file.name}:`, err);
        showToast(`Failed to import "${file.name}": ${err.message}`, 'error');
      }
    }

    progressBarFill.style.width = '100%';
    progressBarText.textContent = 'Import complete!';
    setTimeout(() => progressBarContainer.classList.add('hidden'), 600);

    if (addedPages.length > 0) {
      state.addPages(addedPages);
      if (window.innerWidth <= 960) {
        setActivePane('preview');
      }
    }
  }

  // --------------------------------------------------------------------------
  // Document Pages UI & Empty States
  // --------------------------------------------------------------------------
  state.on('pages_changed', renderPagesList);
  state.on('page_selected', updateSelectedPageUI);
  state.on('page_updated', updateSelectedPageUI);
  state.on('history_changed', updateHistoryButtons);
  state.on('mode_changed', updateModeButtons);

  function updateHistoryButtons() {
    if (btnUndo) btnUndo.disabled = !state.canUndo();
    if (btnRedo) btnRedo.disabled = !state.canRedo();
  }

  function updateModeButtons() {
    const isCrop = state.editorMode === 'crop';
    const hasImg = Boolean(state.getCurrentPage()?.sourceImage);
    btnModeResize?.classList.toggle('active', !isCrop);
    btnModeCrop?.classList.toggle('active', isCrop);
    if (btnModeCrop) btnModeCrop.disabled = !hasImg;
    btnApplyCrop?.classList.toggle('hidden', !isCrop || !hasImg);
  }

  function renderPagesList(pages) {
    pagesListEl.innerHTML = '';
    pageCountBadge.textContent = `${pages.length} page${pages.length === 1 ? '' : 's'}`;
    if (mobileTabCount) mobileTabCount.textContent = String(pages.length);

    const hasPages = pages.length > 0;
    btnClearAll.disabled = !hasPages;
    entireDocControls?.classList.toggle('hidden', !hasPages);
    previewEmptyState?.classList.toggle('hidden', hasPages && Boolean(state.getCurrentPage()));

    if (!hasPages) {
      emptyEditorMessage.classList.remove('hidden');
      pageEditorControls.classList.add('hidden');
      pageIndicator.textContent = '0 / 0';
      btnPrevPage.disabled = true;
      btnNextPage.disabled = true;
      btnZoomIn.disabled = true;
      btnZoomOut.disabled = true;
      btnZoomFit.disabled = true;

      pagesListEl.innerHTML = `
        <div class="empty-state-card">
          <div class="empty-state-icon">📑</div>
          <div class="empty-state-title">Document Queue is Empty</div>
          <p class="empty-state-desc">
            Add images, PDFs, Word docs, or text files to build your document, then drag cards to reorder pages.
          </p>
          <div class="empty-state-actions">
            <button type="button" id="btn-list-add-files" class="btn btn-primary btn-sm">➕ Add Files</button>
            <button type="button" id="btn-list-load-sample" class="btn btn-secondary btn-sm">✨ Load Sample</button>
          </div>
        </div>
      `;
      document.getElementById('btn-list-add-files')?.addEventListener('click', triggerAddFiles);
      document.getElementById('btn-list-load-sample')?.addEventListener('click', loadSampleReport);
      return;
    }

    btnZoomIn.disabled = false;
    btnZoomOut.disabled = false;
    btnZoomFit.disabled = false;

    pages.forEach((page, idx) => {
      const card = document.createElement('div');
      card.className = `page-card ${idx === state.currentIndex ? 'selected' : ''}`;
      card.draggable = true;
      card.tabIndex = 0;
      card.dataset.index = idx;

      const typeBadge = page.sourceType.toUpperCase();

      card.innerHTML = `
        <div class="page-card-num">${idx + 1}</div>
        <div class="page-card-thumb-wrap">
          <img class="page-card-thumb" src="${page.thumbnailUrl || ''}" alt="Page ${idx + 1}" />
        </div>
        <div class="page-card-info">
          <div class="page-card-title" title="${escapeHtml(page.name)}">${escapeHtml(page.name)}</div>
          <div class="page-card-meta">
            <span class="badge badge-${page.sourceType}">${typeBadge}</span>
            <span class="page-card-orient">${page.pageLandscape ? 'Landscape' : 'Portrait'}</span>
          </div>
        </div>
        <div class="page-card-actions">
          <button type="button" class="btn-card-action" data-action="up" title="Move Up" ${idx === 0 ? 'disabled' : ''}>▲</button>
          <button type="button" class="btn-card-action" data-action="down" title="Move Down" ${idx === pages.length - 1 ? 'disabled' : ''}>▼</button>
          <button type="button" class="btn-card-action btn-card-del" data-action="del" title="Delete Page">✕</button>
        </div>
      `;

      card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-card-action')) {
          state.selectPage(idx);
          if (window.innerWidth <= 960) {
            setActivePane('preview');
          }
        }
      });

      card.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          state.selectPage(idx);
        }
      });

      card.querySelectorAll('.btn-card-action').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;
          if (action === 'up') state.movePage(idx, idx - 1);
          if (action === 'down') state.movePage(idx, idx + 1);
          if (action === 'del') state.removePage(idx);
        });
      });

      card.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', String(idx));
        card.classList.add('dragging');
      });
      card.addEventListener('dragend', () => card.classList.remove('dragging'));
      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        card.classList.add('drag-over');
      });
      card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
      card.addEventListener('drop', (e) => {
        e.preventDefault();
        card.classList.remove('drag-over');
        const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
        if (!Number.isNaN(fromIdx) && fromIdx !== idx) {
          state.movePage(fromIdx, idx);
        }
      });

      pagesListEl.appendChild(card);
    });
  }

  function updateSelectedPageUI(page) {
    document.querySelectorAll('.page-card').forEach((card, idx) => {
      card.classList.toggle('selected', idx === state.currentIndex);
    });

    previewEmptyState?.classList.toggle('hidden', Boolean(page));

    if (!page) {
      emptyEditorMessage.classList.remove('hidden');
      pageEditorControls.classList.add('hidden');
      pageIndicator.textContent = '0 / 0';
      btnPrevPage.disabled = true;
      btnNextPage.disabled = true;
      return;
    }

    emptyEditorMessage.classList.add('hidden');
    pageEditorControls.classList.remove('hidden');

    pageIndicator.textContent = `${state.currentIndex + 1} / ${state.pages.length}`;
    btnPrevPage.disabled = state.currentIndex <= 0;
    btnNextPage.disabled = state.currentIndex >= state.pages.length - 1;

    if (page.pageLandscape) {
      radioLandscape.checked = true;
    } else {
      radioPortrait.checked = true;
    }

    const activeRot = ((page.imageRotation || 0) % 360 + 360) % 360;
    rotButtons.forEach(btn => {
      const btnRot = parseInt(btn?.dataset.rot || '-1', 10);
      btn?.classList.toggle('active', btnRot === activeRot);
    });

    const scalePercent = Math.round((page.imageScale || 1.0) * 100);
    scaleSlider.value = scalePercent;
    scaleValueLabel.textContent = `${scalePercent}%`;

    btnMoveUp.disabled = state.currentIndex <= 0;
    btnMoveDown.disabled = state.currentIndex >= state.pages.length - 1;
    updateModeButtons();
  }

  // Initial empty state render
  renderPagesList(state.pages);
  updateSelectedPageUI(state.getCurrentPage());
  updateHistoryButtons();
  updateModeButtons();

  // --------------------------------------------------------------------------
  // Navigation & Zoom Listeners
  // --------------------------------------------------------------------------
  btnPrevPage.addEventListener('click', () => {
    if (state.currentIndex > 0) state.selectPage(state.currentIndex - 1);
  });

  btnNextPage.addEventListener('click', () => {
    if (state.currentIndex < state.pages.length - 1) state.selectPage(state.currentIndex + 1);
  });

  btnZoomIn.addEventListener('click', () => {
    preview.setZoom(Math.min(3.0, preview.zoom + 0.15));
  });

  btnZoomOut.addEventListener('click', () => {
    preview.setZoom(Math.max(0.2, preview.zoom - 0.15));
  });

  btnZoomFit.addEventListener('click', () => {
    preview.fitToContainer();
    preview.render();
  });

  btnClearAll.addEventListener('click', async () => {
    if (state.pages.length === 0) return;
    const ok = await confirmDialog({
      title: 'Clear All Pages?',
      message: 'This will remove all pages from the current workspace queue. You can still undo with Ctrl+Z.',
      confirmLabel: 'Clear All',
      danger: true
    });
    if (ok) {
      state.clearAll();
      showToast('Cleared all pages from workspace.', 'info');
    }
  });

  // --------------------------------------------------------------------------
  // Page Editor Controls
  // --------------------------------------------------------------------------
  function setCurrentPageRotation(degrees) {
    const page = state.getCurrentPage();
    if (!page) return;
    const normalized = ((degrees % 360) + 360) % 360;
    state.updateCurrentPage({ imageRotation: normalized });
    renderPagesList(state.pages);
  }

  function rotateCurrentPage(delta) {
    const page = state.getCurrentPage();
    if (!page) return;
    setCurrentPageRotation((page.imageRotation || 0) + delta);
  }

  btnRotate0.addEventListener('click', () => setCurrentPageRotation(0));
  btnRotate90.addEventListener('click', () => setCurrentPageRotation(90));
  btnRotate180.addEventListener('click', () => setCurrentPageRotation(180));
  btnRotate270.addEventListener('click', () => setCurrentPageRotation(270));

  radioPortrait.addEventListener('change', () => {
    state.updateCurrentPage({ pageLandscape: false });
    if (preview.autoFit) preview.fitToContainer();
    renderPagesList(state.pages);
  });

  radioLandscape.addEventListener('change', () => {
    state.updateCurrentPage({ pageLandscape: true });
    if (preview.autoFit) preview.fitToContainer();
    renderPagesList(state.pages);
  });

  btnFitScale.addEventListener('click', () => {
    state.updateCurrentPage({
      imageScale: 1.0,
      imageOffsetX: 0,
      imageOffsetY: 0,
      imageCrop: null
    });
  });

  scaleSlider.addEventListener('pointerdown', () => {
    if (state.getCurrentPage()) state.snapshotForUndo();
  });
  scaleSlider.addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    scaleValueLabel.textContent = `${val}%`;
    state.updateCurrentPage({ imageScale: val / 100 }, { saveUndo: false });
  });

  btnUndo?.addEventListener('click', () => state.undo());
  btnRedo?.addEventListener('click', () => state.redo());
  btnModeResize?.addEventListener('click', () => state.setEditorMode('resize'));
  btnModeCrop?.addEventListener('click', () => state.setEditorMode('crop'));
  btnApplyCrop?.addEventListener('click', () => {
    const crop = preview.getTempCrop();
    if (crop) {
      state.updateCurrentPage({ imageCrop: crop });
    }
    state.setEditorMode('resize');
  });

  btnRotateAll0?.addEventListener('click', () => state.rotateAllPages(0));
  btnRotateAll90?.addEventListener('click', () => state.rotateAllPages(90));
  btnRotateAll180?.addEventListener('click', () => state.rotateAllPages(180));
  btnRotateAll270?.addEventListener('click', () => state.rotateAllPages(270));
  async function createBlankCanvasAssets(title = '') {
    const canvas = document.createElement('canvas');
    canvas.width = 620;
    canvas.height = 877;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const clean = String(title || '').trim();
    if (clean) {
      ctx.fillStyle = '#1e293b';
      ctx.font = 'bold 28px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(clean, canvas.width / 2, canvas.height / 2, canvas.width - 80);
    }
    const url = canvas.toDataURL('image/png');
    const img = await loadImage(url);
    return { img, thumbUrl: url };
  }

  async function addBlankOrDividerPage() {
    const { img, thumbUrl } = await createBlankCanvasAssets('');
    state.insertBlankPage(state.currentIndex >= 0 ? state.currentIndex : null, '', img, thumbUrl);
  }

  btnAllPortrait?.addEventListener('click', () => state.setAllOrientation(false));
  btnAllLandscape?.addEventListener('click', () => state.setAllOrientation(true));
  btnDuplicatePage?.addEventListener('click', () => {
    if (state.currentIndex >= 0) state.duplicatePage(state.currentIndex);
  });
  btnInsertBlank?.addEventListener('click', () => { addBlankOrDividerPage(); });
  btnReversePages?.addEventListener('click', () => state.reversePages());
  btnSortPages?.addEventListener('click', () => state.sortPagesByName(false));

  btnMoveUp.addEventListener('click', () => {
    if (state.currentIndex > 0) state.movePage(state.currentIndex, state.currentIndex - 1);
  });

  btnMoveDown.addEventListener('click', () => {
    if (state.currentIndex < state.pages.length - 1) state.movePage(state.currentIndex, state.currentIndex + 1);
  });

  btnDeletePage.addEventListener('click', () => {
    if (state.currentIndex >= 0) state.removePage(state.currentIndex);
  });

  // --------------------------------------------------------------------------
  // PDF Export (100% Client-Side)
  // --------------------------------------------------------------------------
  async function exportDocumentPdf() {
    if (state.pages.length === 0) {
      showToast('Please add at least one page (or load the Sample Report) before downloading.', 'warning');
      return;
    }

    btnExportPdf.disabled = true;
    btnExportPdf.innerHTML = '<span class="btn-emoji">⏳</span><span class="btn-label">Generating…</span>';

    try {
      progressBarContainer.classList.remove('hidden');
      const pdfBytes = await buildPdfDocument((current, total, name) => {
        progressBarFill.style.width = `${Math.round((current / total) * 100)}%`;
        progressBarText.textContent = `Assembling page ${current} of ${total}: ${name}`;
      });

      progressBarFill.style.width = '100%';
      progressBarText.textContent = 'Download starting…';

      const filename = (state.settings.outputFilename || 'Report.pdf').trim() || 'Report.pdf';
      downloadPdf(pdfBytes, filename);
      state.recordRecent({
        id: 'action:export-pdf',
        type: 'action',
        label: `Exported ${filename}`,
        subtitle: `${state.pages.length} page${state.pages.length === 1 ? '' : 's'}`,
        actionId: 'export-pdf'
      });
    } catch (err) {
      console.error('PDF export failed:', err);
      showToast('Error generating PDF: ' + err.message, 'error');
    } finally {
      btnExportPdf.disabled = false;
      btnExportPdf.innerHTML = '<span class="btn-emoji">💾</span><span class="btn-label">Download PDF</span>';
      setTimeout(() => progressBarContainer.classList.add('hidden'), 1200);
    }
  }

  btnExportPdf.addEventListener('click', exportDocumentPdf);

  // --------------------------------------------------------------------------
  // Shrink / Compress PDF Modal
  // --------------------------------------------------------------------------
  function openShrinkModal() {
    shrinkModal.classList.remove('hidden');
    resetShrinkDialog();
    modalTrap.activate(shrinkModal);
  }

  function closeShrinkModal() {
    shrinkModal.classList.add('hidden');
    modalTrap.deactivate(true);
  }

  btnShrinkPdf.addEventListener('click', openShrinkModal);
  btnCloseShrink.addEventListener('click', closeShrinkModal);
  shrinkModal.addEventListener('click', (e) => {
    if (e.target === shrinkModal) closeShrinkModal();
  });

  function resetShrinkDialog() {
    shrinkSelectedFile = null;
    compressedPdfResult = null;
    shrinkFileDetails.classList.add('hidden');
    shrinkEmptyHelper?.classList.remove('hidden');
    shrinkProgress.classList.add('hidden');
    shrinkResult.classList.add('hidden');
    btnStartCompress.disabled = true;
  }

  shrinkDropZone.addEventListener('click', () => shrinkFileInput.click());
  btnShrinkBrowse?.addEventListener('click', () => shrinkFileInput.click());
  shrinkDropZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      shrinkFileInput.click();
    }
  });

  ['dragenter', 'dragover'].forEach(ev => {
    shrinkDropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      shrinkDropZone.classList.add('drag-active');
    });
  });
  ['dragleave', 'drop'].forEach(ev => {
    shrinkDropZone.addEventListener(ev, (e) => {
      e.preventDefault();
      e.stopPropagation();
      shrinkDropZone.classList.remove('drag-active');
    });
  });
  shrinkDropZone.addEventListener('drop', (e) => {
    if (e.dataTransfer?.files?.[0]) {
      handleShrinkFile(e.dataTransfer.files[0]);
    }
  });

  shrinkFileInput.addEventListener('change', (e) => {
    if (e.target.files?.[0]) {
      handleShrinkFile(e.target.files[0]);
    }
  });

  btnShrinkSample?.addEventListener('click', async () => {
    try {
      const sampleFile = await createSamplePdfFile();
      handleShrinkFile(sampleFile);
    } catch (err) {
      showToast('Could not create sample PDF: ' + err.message, 'error');
    }
  });

  function handleShrinkFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      showToast('Please select a PDF file to compress.', 'warning');
      return;
    }
    shrinkSelectedFile = file;
    shrinkFileName.textContent = file.name;
    shrinkFileSize.textContent = formatFileSize(file.size);
    shrinkFileDetails.classList.remove('hidden');
    shrinkEmptyHelper?.classList.add('hidden');
    shrinkResult.classList.add('hidden');
    btnStartCompress.disabled = false;
  }

  btnStartCompress.addEventListener('click', async () => {
    if (!shrinkSelectedFile) return;

    btnStartCompress.disabled = true;
    shrinkProgress.classList.remove('hidden');
    shrinkResult.classList.add('hidden');

    const level = document.querySelector('input[name="shrink-level"]:checked')?.value || 'standard';

    try {
      const result = await compressPdf(shrinkSelectedFile, level, (cur, total, msg) => {
        shrinkProgressBar.style.width = `${Math.round((cur / total) * 100)}%`;
        shrinkProgressText.textContent = msg;
      });

      compressedPdfResult = result;
      shrinkProgress.classList.add('hidden');
      shrinkResult.classList.remove('hidden');

      shrinkResultDetails.innerHTML = `
        <div>Original Size: <strong>${formatFileSize(result.originalSize)}</strong></div>
        <div>Compressed Size: <strong>${formatFileSize(result.compressedSize)}</strong></div>
        <div class="savings-badge">${result.keptOriginal ? 'Already compact — original kept without quality loss.' : 'Saved ' + result.savedPercent + '% of file size!'}</div>
      `;
    } catch (err) {
      console.error('Compression failed:', err);
      showToast('Compression failed: ' + err.message, 'error');
      shrinkProgress.classList.add('hidden');
    } finally {
      btnStartCompress.disabled = false;
    }
  });

  btnDownloadShrunk.addEventListener('click', () => {
    if (!compressedPdfResult) return;
    const baseName = shrinkSelectedFile.name.replace(/\.pdf$/i, '');
    downloadPdf(compressedPdfResult.bytes, `${baseName}_shrunk.pdf`);
  });

  // --------------------------------------------------------------------------
  // 3D Capture Modal
  // --------------------------------------------------------------------------
  document.getElementById('btn-capture-3d').addEventListener('click', () => threeModal.captureSnapshot());
  document.getElementById('btn-close-3d').addEventListener('click', () => threeModal.close());

  // --------------------------------------------------------------------------
  const modalTrap = new ModalFocusTrap();

  // Shortcuts Overlay ("?") & Command Palette (Cmd/Ctrl+K)
  // --------------------------------------------------------------------------
  renderShortcutsModalContent(shortcutsModalBody);

  function openShortcutsModal() {
    shortcutsModal.classList.remove('hidden');
    modalTrap.activate(shortcutsModal);
  }
  function closeShortcutsModal() {
    shortcutsModal.classList.add('hidden');
    modalTrap.deactivate(true);
  }
  function toggleShortcutsModal() {
    if (shortcutsModal.classList.contains('hidden')) openShortcutsModal();
    else closeShortcutsModal();
  }

  btnShortcuts?.addEventListener('click', toggleShortcutsModal);
  btnCloseShortcuts?.addEventListener('click', closeShortcutsModal);
  btnDoneShortcuts?.addEventListener('click', closeShortcutsModal);
  shortcutsModal?.addEventListener('click', (e) => {
    if (e.target === shortcutsModal) closeShortcutsModal();
  });

  function getOpenModalId() {
    const ids = ['modal-command-palette', 'modal-shortcuts', 'modal-settings', 'modal-shrink', 'modal-3d'];
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el && !el.classList.contains('hidden')) return id;
    }
    return null;
  }

  function closeTopModal() {
    const openId = getOpenModalId();
    if (openId === 'modal-command-palette') palette.close();
    else if (openId === 'modal-shortcuts') closeShortcutsModal();
    else if (openId === 'modal-settings') settingsUI.closeModal();
    else if (openId === 'modal-shrink') closeShrinkModal();
    else if (openId === 'modal-3d') threeModal.close();
  }

  function runAppAction(actionId) {
    const page = state.getCurrentPage();
    switch (actionId) {
      case 'open-palette':
        palette.toggle();
        break;
      case 'toggle-shortcuts':
        toggleShortcutsModal();
        break;
      case 'add-files':
        triggerAddFiles();
        break;
      case 'load-sample':
        loadSampleReport();
        break;
      case 'export-pdf':
        exportDocumentPdf();
        break;
      case 'open-shrink':
        openShrinkModal();
        break;
      case 'open-settings':
        settingsUI.openModal();
        break;
      case 'rotate-90':
        if (page) rotateCurrentPage(90);
        break;
      case 'toggle-orientation':
        if (page) {
          state.updateCurrentPage({ pageLandscape: !page.pageLandscape });
          if (preview.autoFit) preview.fitToContainer();
          renderPagesList(state.pages);
        }
        break;
      case 'fit-scale':
        if (page) {
          state.updateCurrentPage({ imageScale: 1.0, imageOffsetX: 0, imageOffsetY: 0, imageCrop: null });
        }
        break;
      case 'toggle-page-numbers':
        state.updateSettings({ pageNumbers: !state.settings.pageNumbers });
        break;
      case 'fit-view':
        if (page) {
          preview.fitToContainer();
          preview.render();
        }
        break;
      case 'zoom-in':
        if (page) preview.setZoom(Math.min(3.0, preview.zoom + 0.15));
        break;
      case 'zoom-out':
        if (page) preview.setZoom(Math.max(0.2, preview.zoom - 0.15));
        break;
      case 'prev-page':
        if (state.currentIndex > 0) state.selectPage(state.currentIndex - 1);
        break;
      case 'next-page':
        if (state.currentIndex < state.pages.length - 1) state.selectPage(state.currentIndex + 1);
        break;
      case 'move-up':
        if (state.currentIndex > 0) state.movePage(state.currentIndex, state.currentIndex - 1);
        break;
      case 'move-down':
        if (state.currentIndex >= 0 && state.currentIndex < state.pages.length - 1) {
          state.movePage(state.currentIndex, state.currentIndex + 1);
        }
        break;
      case 'delete-page':
        if (state.currentIndex >= 0) state.removePage(state.currentIndex);
        break;
      case 'clear-all':
        if (state.pages.length > 0) {
          confirmDialog({
            title: 'Clear All Pages?',
            message: 'This will remove all pages from the current workspace queue. You can still undo with Ctrl+Z.',
            confirmLabel: 'Clear All',
            danger: true
          }).then((ok) => {
            if (ok) {
              state.clearAll();
              showToast('Cleared all pages from workspace.', 'info');
            }
          });
        }
        break;
      case 'undo':
        state.undo();
        break;
      case 'redo':
        state.redo();
        break;
      case 'toggle-crop-mode':
        if (page?.sourceImage) {
          state.setEditorMode(state.editorMode === 'crop' ? 'resize' : 'crop');
        }
        break;
      case 'rotate-all-90':
        if (state.pages.length > 0) {
          const base = page ? (page.imageRotation || 0) : 0;
          state.rotateAllPages((base + 90) % 360);
        }
        break;
      case 'all-portrait':
        state.setAllOrientation(false);
        break;
      case 'all-landscape':
        state.setAllOrientation(true);
        break;
      case 'duplicate-page':
        if (state.currentIndex >= 0) state.duplicatePage(state.currentIndex);
        break;
      case 'insert-blank':
        addBlankOrDividerPage();
        break;
      case 'reverse-pages':
        state.reversePages();
        break;
      case 'sort-pages':
        state.sortPagesByName(false);
        break;
      case 'toggle-theme': {
        const cur = document.documentElement.getAttribute('data-theme');
        applyTheme(cur === 'dark' ? 'light' : 'dark');
        break;
      }
      default:
        break;
    }
    if (!['open-palette', 'toggle-shortcuts', 'load-sample', 'export-pdf'].includes(actionId)) {
      state.recordRecent({
        id: `action:${actionId}`,
        type: 'action',
        label: actionId.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
        subtitle: 'Quick Action',
        actionId
      });
    }
  }

  const palette = new CommandPalette({
    state,
    getActions: () => {
      const hasPage = Boolean(state.getCurrentPage());
      const hasMultiple = state.pages.length > 1;
      return [
        { id: 'add-files', icon: '➕', label: 'Add Files to Document', subtitle: 'Import Images, PDF, DOCX, Text, or 3D', shortcut: 'A', keywords: 'import upload open' },
        { id: 'load-sample', icon: '✨', label: 'Load 3-Page Sample Report', subtitle: 'Populate workspace with sample pages', keywords: 'template demo sample' },
        { id: 'export-pdf', icon: '💾', label: 'Download / Export PDF', subtitle: 'Assemble and download your document', shortcut: 'E', disabled: state.pages.length === 0, keywords: 'save build export' },
        { id: 'open-shrink', icon: '🗜️', label: 'Shrink / Compress PDF', subtitle: 'Optimize an existing PDF locally', shortcut: 'S', keywords: 'compress optimize reduce' },
        { id: 'open-settings', icon: '⚙️', label: 'Open Document & App Settings', subtitle: 'Page size, defaults, numbering, export quality', shortcut: 'G', keywords: 'settings config preferences' },
        { id: 'rotate-90', icon: '🔄', label: 'Rotate Page Content +90°', subtitle: 'Rotate image on current page', shortcut: 'R', disabled: !hasPage, keywords: 'turn spin angle' },
        { id: 'toggle-orientation', icon: '📐', label: 'Toggle Portrait / Landscape', subtitle: 'Switch orientation of selected page', shortcut: 'O', disabled: !hasPage, keywords: 'orientation portrait landscape' },
        { id: 'fit-scale', icon: '⊡', label: 'Reset / Fit Image Scale', subtitle: 'Reset scale, offset, and crop', disabled: !hasPage, keywords: 'reset scale fit' },
        { id: 'toggle-page-numbers', icon: '🔢', label: `${state.settings.pageNumbers ? 'Disable' : 'Enable'} Page Numbers`, subtitle: 'Toggle live header/footer page numbers', shortcut: 'N', keywords: 'numbering footer header' },
        { id: 'fit-view', icon: '👁️', label: 'Fit Page to Preview Window', subtitle: 'Center and fit current page in canvas', shortcut: 'F', disabled: !hasPage, keywords: 'zoom fit preview' },
        { id: 'zoom-in', icon: '🔍', label: 'Zoom In Preview', shortcut: '+', disabled: !hasPage, keywords: 'magnify larger' },
        { id: 'zoom-out', icon: '🔎', label: 'Zoom Out Preview', shortcut: '−', disabled: !hasPage, keywords: 'smaller' },
        { id: 'prev-page', icon: '◀', label: 'Previous Page', shortcut: '←', disabled: state.currentIndex <= 0, keywords: 'back prev' },
        { id: 'next-page', icon: '▶', label: 'Next Page', shortcut: '→', disabled: state.currentIndex >= state.pages.length - 1, keywords: 'forward next' },
        { id: 'move-up', icon: '▲', label: 'Move Selected Page Up', disabled: state.currentIndex <= 0, keywords: 'reorder earlier' },
        { id: 'move-down', icon: '▼', label: 'Move Selected Page Down', disabled: !hasMultiple || state.currentIndex >= state.pages.length - 1, keywords: 'reorder later' },
        { id: 'delete-page', icon: '🗑️', label: 'Delete Selected Page', shortcut: 'Del', disabled: !hasPage, keywords: 'remove delete' },
        { id: 'undo', icon: '↩️', label: 'Undo Last Change', shortcut: 'Ctrl+Z', disabled: !state.canUndo(), keywords: 'undo revert history' },
        { id: 'redo', icon: '↪️', label: 'Redo Change', shortcut: 'Ctrl+Y', disabled: !state.canRedo(), keywords: 'redo history' },
        { id: 'toggle-crop-mode', icon: '✂️', label: state.editorMode === 'crop' ? 'Exit Crop Mode (Resize)' : 'Crop Image', disabled: !hasPage, keywords: 'crop trim' },
        { id: 'rotate-all-90', icon: '🔁', label: 'Rotate All Pages +90°', disabled: state.pages.length === 0, keywords: 'batch rotate all' },
        { id: 'all-portrait', icon: '📄', label: 'Set All Pages to Portrait', disabled: state.pages.length === 0, keywords: 'batch portrait all' },
        { id: 'all-landscape', icon: '🖼️', label: 'Set All Pages to Landscape', disabled: state.pages.length === 0, keywords: 'batch landscape all' },
        { id: 'duplicate-page', icon: '📄', label: 'Duplicate Selected Page', disabled: !hasPage, keywords: 'copy clone duplicate page' },
        { id: 'insert-blank', icon: '➕', label: 'Insert Blank Page', keywords: 'blank divider spacer page' },
        { id: 'reverse-pages', icon: '⇅', label: 'Reverse Page Order', disabled: !hasMultiple, keywords: 'reverse flip order' },
        { id: 'sort-pages', icon: '🔤', label: 'Sort Pages by Name (A→Z)', disabled: !hasMultiple, keywords: 'sort alphabetical name' },
        { id: 'clear-all', icon: '🧹', label: 'Clear All Pages', disabled: state.pages.length === 0, keywords: 'reset empty queue' },
        { id: 'toggle-theme', icon: '🌗', label: 'Toggle Dark / Light Theme', shortcut: 'T', keywords: 'appearance dark light mode' },
        { id: 'toggle-shortcuts', icon: '⌨️', label: 'Show Keyboard Shortcuts', shortcut: '?', keywords: 'help keys hotkeys' }
      ];
    },
    onSelectPage: (idx) => {
      state.selectPage(idx);
      if (window.innerWidth <= 960) setActivePane('preview');
    },
    onNavigateView: (viewId) => {
      if (viewId === 'pages' || viewId === 'preview' || viewId === 'editor') {
        setActivePane(viewId);
      } else if (viewId === 'settings') {
        settingsUI.openModal();
      } else if (viewId === 'shrink') {
        openShrinkModal();
      } else if (viewId === 'shortcuts') {
        openShortcutsModal();
      }
    },
    onRunAction: runAppAction
  });

  btnCommandPalette?.addEventListener('click', () => palette.open());

  const shortcutManager = new ShortcutManager({
    runAction: runAppAction,
    getOpenModalId,
    closeTopModal,
    onToggleShortcuts: toggleShortcutsModal
  });
  shortcutManager.attach();

  // --------------------------------------------------------------------------
  // IndexedDB Workspace Session Auto-Save & Recovery
  // --------------------------------------------------------------------------
  let sessionSaveTimer = null;
  let restoringSession = false;

  function scheduleSessionSave() {
    if (restoringSession) return;
    clearTimeout(sessionSaveTimer);
    sessionSaveTimer = setTimeout(async () => {
      if (state.pages.length === 0) {
        await clearSessionFromIdb();
      } else {
        const payload = serializeSessionPages(state.pages, state.currentIndex);
        await saveSessionToIdb(payload);
      }
    }, 600);
  }

  state.on('pages_changed', scheduleSessionSave);
  state.on('page_updated', scheduleSessionSave);
  state.on('page_selected', scheduleSessionSave);

  (async () => {
    if (state.pages.length > 0) return;
    const saved = await loadSessionFromIdb();
    if (!saved || !Array.isArray(saved.pages) || saved.pages.length === 0) return;
    restoringSession = true;
    try {
      const restored = await deserializeSessionPages(saved, loadImage);
      if (restored.pages.length > 0) {
        state.pages = restored.pages;
        state.currentIndex = restored.currentIndex;
        state.emit('pages_changed', state.pages);
        state.emit('page_selected', state.getCurrentPage());
        showToast(`Restored previous session (${restored.pages.length} page${restored.pages.length === 1 ? '' : 's'})`, 'info');
      }
    } finally {
      restoringSession = false;
    }
  })();
});
