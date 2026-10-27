import { escapeHtml } from './html-utils.js';
/**
 * Main Application Controller for ReportPDFmaker Web
 * 100% Client-Side SPA
 */

import { state, getPageDimensions } from './state.js';
import {
  convertImageFile,
  convertPdfFile,
  convertDocxFile,
  convertTextFile
} from './converters.js';
import { CanvasPreview } from './canvas-preview.js';
import { buildPdfDocument, downloadPdf } from './pdf-builder.js';
import { compressPdf, formatFileSize } from './pdf-compressor.js';
import { ThreeViewerModal } from './three-viewer.js';

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Preview Canvas
  const preview = new CanvasPreview('canvas-container');

  // Initialize 3D Viewer Modal
  const threeModal = new ThreeViewerModal('modal-3d', 'three-container');

  // Elements
  const fileInput = document.getElementById('file-input');
  const btnAddFiles = document.getElementById('btn-add-files');
  const btnClearAll = document.getElementById('btn-clear-all');
  const pagesListEl = document.getElementById('pages-list');
  const pageCountBadge = document.getElementById('page-count-badge');
  const dropZone = document.getElementById('drop-zone');

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
  const btnRotate90 = document.getElementById('btn-rotate-90');
  const btnRotate180 = document.getElementById('btn-rotate-180');
  const btnRotate270 = document.getElementById('btn-rotate-270');
  const btnRotate0 = document.getElementById('btn-rotate-0');
  const radioPortrait = document.getElementById('orient-portrait');
  const radioLandscape = document.getElementById('orient-landscape');
  const btnFitScale = document.getElementById('btn-fit-scale');
  const scaleSlider = document.getElementById('scale-slider');
  const scaleValueLabel = document.getElementById('scale-value-label');
  const btnMoveUp = document.getElementById('btn-move-up');
  const btnMoveDown = document.getElementById('btn-move-down');
  const btnDeletePage = document.getElementById('btn-delete-page');

  // Page Numbering Controls
  const chkPageNumbers = document.getElementById('chk-page-numbers');
  const pageNumbersConfig = document.getElementById('page-numbers-config');
  const selectNumberPos = document.getElementById('num-position');
  const selectNumberAlign = document.getElementById('num-alignment');
  const selectNumberStyle = document.getElementById('num-style');
  const selectNumberFont = document.getElementById('num-font');
  const inputNumberSize = document.getElementById('num-size');
  const inputNumberColor = document.getElementById('num-color');
  const chkSkipCover = document.getElementById('chk-skip-cover');

  // Document Settings & Export
  const selectPageSize = document.getElementById('doc-page-size');
  const inputFilename = document.getElementById('doc-filename');
  const btnExportPdf = document.getElementById('btn-export-pdf');
  const themeToggle = document.getElementById('theme-toggle');

  // Progress Bar & Modals
  const progressBarContainer = document.getElementById('import-progress-container');
  const progressBarFill = document.getElementById('import-progress-fill');
  const progressBarText = document.getElementById('import-progress-text');

  // Shrink PDF Modal
  const btnShrinkPdf = document.getElementById('btn-shrink-pdf');
  const shrinkModal = document.getElementById('modal-shrink');
  const btnCloseShrink = document.getElementById('btn-close-shrink');
  const shrinkFileInput = document.getElementById('shrink-file-input');
  const shrinkDropZone = document.getElementById('shrink-drop-zone');
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

  // --------------------------------------------------------------------------
  // Theme Management
  // --------------------------------------------------------------------------
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    state.updateSettings({ theme });
    themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
  }
  applyTheme(state.settings.theme || 'dark');

  themeToggle.addEventListener('click', () => {
    const newTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    applyTheme(newTheme);
  });

  // --------------------------------------------------------------------------
  // File Import Handling
  // --------------------------------------------------------------------------
  btnAddFiles.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
      fileInput.value = '';
    }
  });

  // Drag & Drop
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
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  });

  async function handleFiles(files) {
    progressBarContainer.classList.remove('hidden');
    const total = files.length;
    let completed = 0;
    const addedPages = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const ext = file.name.split('.').pop().toLowerCase();

      progressBarFill.style.width = `${Math.round(((i) / total) * 100)}%`;
      progressBarText.textContent = `Importing ${file.name} (${i + 1}/${total})…`;

      try {
        if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(ext)) {
          const page = await convertImageFile(file);
          addedPages.push(page);
        } else if (ext === 'pdf') {
          const pdfPages = await convertPdfFile(file);
          addedPages.push(...pdfPages);
        } else if (ext === 'docx') {
          const docPages = await convertDocxFile(file);
          addedPages.push(...docPages);
        } else if (['txt', 'md', 'csv', 'log', 'json'].includes(ext)) {
          const textPages = await convertTextFile(file);
          addedPages.push(...textPages);
        } else if (['gltf', 'glb'].includes(ext)) {
          // Open 3D viewer modal for interactive camera snapshot
          await threeModal.loadModel(file, (capturedPage) => {
            state.addPages([capturedPage]);
          });
        } else {
          console.warn(`Unsupported file format: ${file.name}`);
        }
      } catch (err) {
        console.error(`Error processing ${file.name}:`, err);
        alert(`Failed to import "${file.name}":\n${err.message}`);
      }
      completed++;
    }

    progressBarFill.style.width = '100%';
    progressBarText.textContent = 'Import complete!';
    setTimeout(() => {
      progressBarContainer.classList.add('hidden');
    }, 600);

    if (addedPages.length > 0) {
      state.addPages(addedPages);
    }
  }

  // --------------------------------------------------------------------------
  // Document Pages UI Rendering & Reordering
  // --------------------------------------------------------------------------
  state.on('pages_changed', renderPagesList);
  state.on('page_selected', updateSelectedPageUI);

  function renderPagesList(pages) {
    pagesListEl.innerHTML = '';
    pageCountBadge.textContent = `${pages.length} page${pages.length === 1 ? '' : 's'}`;

    if (pages.length === 0) {
      emptyEditorMessage.classList.remove('hidden');
      pageEditorControls.classList.add('hidden');
      pageIndicator.textContent = '0 / 0';
      return;
    }

    pages.forEach((page, idx) => {
      const card = document.createElement('div');
      card.className = `page-card ${idx === state.currentIndex ? 'selected' : ''}`;
      card.draggable = true;
      card.dataset.index = idx;

      // Type Badge
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
          <button class="btn-card-action" data-action="up" title="Move Up" ${idx === 0 ? 'disabled' : ''}>▲</button>
          <button class="btn-card-action" data-action="down" title="Move Down" ${idx === pages.length - 1 ? 'disabled' : ''}>▼</button>
          <button class="btn-card-action btn-card-del" data-action="del" title="Delete Page">✕</button>
        </div>
      `;

      // Select page on click
      card.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-card-action')) {
          state.selectPage(idx);
        }
      });

      // Actions within card
      card.querySelectorAll('.btn-card-action').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const action = btn.dataset.action;
          if (action === 'up') state.movePage(idx, idx - 1);
          if (action === 'down') state.movePage(idx, idx + 1);
          if (action === 'del') state.removePage(idx);
        });
      });

      // Drag and Drop reordering
      card.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', idx);
        card.classList.add('dragging');
      });

      card.addEventListener('dragend', () => {
        card.classList.remove('dragging');
      });

      card.addEventListener('dragover', (e) => {
        e.preventDefault();
        card.classList.add('drag-over');
      });

      card.addEventListener('dragleave', () => {
        card.classList.remove('drag-over');
      });

      card.addEventListener('drop', (e) => {
        e.preventDefault();
        card.classList.remove('drag-over');
        const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
        if (!isNaN(fromIdx) && fromIdx !== idx) {
          state.movePage(fromIdx, idx);
        }
      });

      pagesListEl.appendChild(card);
    });
  }

  function updateSelectedPageUI(page) {
    // Update card selection styling
    document.querySelectorAll('.page-card').forEach((card, idx) => {
      card.classList.toggle('selected', idx === state.currentIndex);
    });

    if (!page) {
      emptyEditorMessage.classList.remove('hidden');
      pageEditorControls.classList.add('hidden');
      pageIndicator.textContent = '0 / 0';
      return;
    }

    emptyEditorMessage.classList.add('hidden');
    pageEditorControls.classList.remove('hidden');

    pageIndicator.textContent = `${state.currentIndex + 1} / ${state.pages.length}`;
    btnPrevPage.disabled = state.currentIndex <= 0;
    btnNextPage.disabled = state.currentIndex >= state.pages.length - 1;

    // Orientation
    if (page.pageLandscape) {
      radioLandscape.checked = true;
    } else {
      radioPortrait.checked = true;
    }

    // Scale
    const scalePercent = Math.round((page.imageScale || 1.0) * 100);
    scaleSlider.value = scalePercent;
    scaleValueLabel.textContent = `${scalePercent}%`;

    // Move buttons in editor
    btnMoveUp.disabled = state.currentIndex <= 0;
    btnMoveDown.disabled = state.currentIndex >= state.pages.length - 1;
  }

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
    zoomLevelLabel.textContent = `${Math.round(preview.zoom * 100)}%`;
  });

  btnZoomOut.addEventListener('click', () => {
    preview.setZoom(Math.max(0.2, preview.zoom - 0.15));
    zoomLevelLabel.textContent = `${Math.round(preview.zoom * 100)}%`;
  });

  btnZoomFit.addEventListener('click', () => {
    preview.fitToContainer();
    preview.render();
    zoomLevelLabel.textContent = `${Math.round(preview.zoom * 100)}%`;
  });

  btnClearAll.addEventListener('click', () => {
    if (state.pages.length === 0) return;
    if (confirm('Are you sure you want to clear all pages?')) {
      state.clearAll();
    }
  });

  // --------------------------------------------------------------------------
  // Page Editor Controls
  // --------------------------------------------------------------------------
  btnRotate90.addEventListener('click', () => {
    const page = state.getCurrentPage();
    if (!page) return;
    const nextRot = ((page.imageRotation || 0) + 90) % 360;
    state.updateCurrentPage({ imageRotation: nextRot });
  });

  btnRotate180.addEventListener('click', () => {
    const page = state.getCurrentPage();
    if (!page) return;
    const nextRot = ((page.imageRotation || 0) + 180) % 360;
    state.updateCurrentPage({ imageRotation: nextRot });
  });

  btnRotate270.addEventListener('click', () => {
    const page = state.getCurrentPage();
    if (!page) return;
    const nextRot = ((page.imageRotation || 0) + 270) % 360;
    state.updateCurrentPage({ imageRotation: nextRot });
  });

  btnRotate0.addEventListener('click', () => {
    state.updateCurrentPage({ imageRotation: 0 });
  });

  radioPortrait.addEventListener('change', () => {
    state.updateCurrentPage({ pageLandscape: false });
    if (preview.autoFit) preview.fitToContainer();
  });

  radioLandscape.addEventListener('change', () => {
    state.updateCurrentPage({ pageLandscape: true });
    if (preview.autoFit) preview.fitToContainer();
  });

  btnFitScale.addEventListener('click', () => {
    state.updateCurrentPage({
      imageScale: 1.0,
      imageOffsetX: 0,
      imageOffsetY: 0,
      imageCrop: null
    });
    scaleSlider.value = 100;
    scaleValueLabel.textContent = '100%';
  });

  scaleSlider.addEventListener('input', (e) => {
    const val = parseInt(e.target.value, 10);
    scaleValueLabel.textContent = `${val}%`;
    state.updateCurrentPage({ imageScale: val / 100 });
  });

  btnMoveUp.addEventListener('click', () => {
    if (state.currentIndex > 0) state.movePage(state.currentIndex, state.currentIndex - 1);
  });

  btnMoveDown.addEventListener('click', () => {
    if (state.currentIndex < state.pages.length - 1) state.movePage(state.currentIndex, state.currentIndex + 1);
  });

  btnDeletePage.addEventListener('click', () => {
    state.removePage(state.currentIndex);
  });

  // --------------------------------------------------------------------------
  // Page Numbering Controls
  // --------------------------------------------------------------------------
  chkPageNumbers.checked = state.settings.pageNumbers;
  pageNumbersConfig.classList.toggle('hidden', !state.settings.pageNumbers);

  chkPageNumbers.addEventListener('change', (e) => {
    const enabled = e.target.checked;
    pageNumbersConfig.classList.toggle('hidden', !enabled);
    state.updateSettings({ pageNumbers: enabled });
  });

  selectNumberPos.value = state.settings.pageNumberPosition;
  selectNumberAlign.value = state.settings.pageNumberAlignment;
  selectNumberStyle.value = state.settings.pageNumberStyle;
  selectNumberFont.value = state.settings.pageNumberFont;
  inputNumberSize.value = state.settings.pageNumberFontSize;
  inputNumberColor.value = state.settings.pageNumberColor;
  chkSkipCover.checked = state.settings.skipCoverPage;

  selectNumberPos.addEventListener('change', (e) => state.updateSettings({ pageNumberPosition: e.target.value }));
  selectNumberAlign.addEventListener('change', (e) => state.updateSettings({ pageNumberAlignment: e.target.value }));
  selectNumberStyle.addEventListener('change', (e) => state.updateSettings({ pageNumberStyle: e.target.value }));
  selectNumberFont.addEventListener('change', (e) => state.updateSettings({ pageNumberFont: e.target.value }));
  inputNumberSize.addEventListener('input', (e) => state.updateSettings({ pageNumberFontSize: parseInt(e.target.value, 10) }));
  inputNumberColor.addEventListener('input', (e) => state.updateSettings({ pageNumberColor: e.target.value }));
  chkSkipCover.addEventListener('change', (e) => state.updateSettings({ skipCoverPage: e.target.checked }));

  // Page Size & Filename
  selectPageSize.value = state.settings.pageSize;
  selectPageSize.addEventListener('change', (e) => {
    state.updateSettings({ pageSize: e.target.value });
    if (preview.autoFit) preview.fitToContainer();
  });

  inputFilename.value = state.settings.outputFilename;
  inputFilename.addEventListener('input', (e) => state.updateSettings({ outputFilename: e.target.value }));

  // --------------------------------------------------------------------------
  // 💾 PDF Export (100% Client-Side)
  // --------------------------------------------------------------------------
  btnExportPdf.addEventListener('click', async () => {
    if (state.pages.length === 0) {
      alert('Please add at least one page before exporting.');
      return;
    }

    btnExportPdf.disabled = true;
    btnExportPdf.textContent = 'Generating PDF…';

    try {
      progressBarContainer.classList.remove('hidden');
      const pdfBytes = await buildPdfDocument((current, total, name) => {
        progressBarFill.style.width = `${Math.round((current / total) * 100)}%`;
        progressBarText.textContent = `Assembling page ${current} of ${total}: ${name}`;
      });

      progressBarFill.style.width = '100%';
      progressBarText.textContent = 'Download starting…';

      const filename = inputFilename.value.trim() || 'Report.pdf';
      downloadPdf(pdfBytes, filename);
    } catch (err) {
      console.error('PDF export failed:', err);
      alert('Error generating PDF:\n' + err.message);
    } finally {
      btnExportPdf.disabled = false;
      btnExportPdf.textContent = '💾 Download PDF';
      setTimeout(() => progressBarContainer.classList.add('hidden'), 1200);
    }
  });

  // --------------------------------------------------------------------------
  // 🗜️ Shrink / Compress PDF Modal
  // --------------------------------------------------------------------------
  btnShrinkPdf.addEventListener('click', () => {
    shrinkModal.classList.remove('hidden');
    resetShrinkDialog();
  });

  btnCloseShrink.addEventListener('click', () => {
    shrinkModal.classList.add('hidden');
  });

  function resetShrinkDialog() {
    shrinkSelectedFile = null;
    compressedPdfResult = null;
    shrinkFileDetails.classList.add('hidden');
    shrinkProgress.classList.add('hidden');
    shrinkResult.classList.add('hidden');
    btnStartCompress.disabled = true;
  }

  shrinkDropZone.addEventListener('click', () => shrinkFileInput.click());
  shrinkFileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      handleShrinkFile(e.target.files[0]);
    }
  });

  function handleShrinkFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Please select a PDF file to compress.');
      return;
    }
    shrinkSelectedFile = file;
    shrinkFileName.textContent = file.name;
    shrinkFileSize.textContent = formatFileSize(file.size);
    shrinkFileDetails.classList.remove('hidden');
    shrinkResult.classList.add('hidden');
    btnStartCompress.disabled = false;
  }

  btnStartCompress.addEventListener('click', async () => {
    if (!shrinkSelectedFile) return;

    btnStartCompress.disabled = true;
    shrinkProgress.classList.remove('hidden');
    shrinkResult.classList.add('hidden');

    const level = document.querySelector('input[name="shrink-level"]:checked').value;

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
      alert('Compression failed: ' + err.message);
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

  // 3D Capture button in 3D modal
  document.getElementById('btn-capture-3d').addEventListener('click', () => {
    threeModal.captureSnapshot();
  });
  document.getElementById('btn-close-3d').addEventListener('click', () => {
    threeModal.close();
  });
});
