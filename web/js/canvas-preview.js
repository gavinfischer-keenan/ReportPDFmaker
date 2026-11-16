/**
 * Interactive Live Preview Canvas for ReportPDFmaker Web
 * Replicates the Tkinter PreviewPanel with corner handles, aspect-ratio locked resizing,
 * panning/offsets, rotation, cropping, and live page numbers.
 */

import { state, getPageDimensions } from './state.js';
import { computePageImageGeometry, formatPageNumberText } from './math-utils.js';

export class CanvasPreview {
  constructor(canvasContainerId, onZoomChange = null) {
    this.container = document.getElementById(canvasContainerId);
    this.onZoomChange = onZoomChange;
    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.container.appendChild(this.canvas);

    // Zoom & display
    this.zoom = 0.8;
    this.autoFit = true;

    // Interaction state
    this.isDragging = false;
    this.dragMode = null; // 'handle-nw' | 'handle-ne' | 'handle-sw' | 'handle-se' | 'pan'
    this.dragStartMouse = { x: 0, y: 0 };
    this.dragStartScale = 1.0;
    this.dragStartOffset = { x: 0, y: 0 };

    // Geometry caches
    this.pageRect = { x: 0, y: 0, w: 0, h: 0 };
    this.imgRect = { x: 0, y: 0, w: 0, h: 0, cx: 0, cy: 0 };
    this.handles = {};

    this.HANDLE_SIZE = 8; // px half-side
    this.HANDLE_HIT_RADIUS = 14;

    this.initEvents();
  }

  initEvents() {
    window.addEventListener('resize', () => {
      if (this.autoFit) this.fitToContainer();
      this.render();
    });

    if (typeof ResizeObserver !== 'undefined' && this.container) {
      this._resizeObserver = new ResizeObserver(() => {
        if (this.container.clientWidth > 0 && this.container.clientHeight > 0) {
          if (this.autoFit) this.fitToContainer();
          this.render();
        }
      });
      this._resizeObserver.observe(this.container);
    }

    this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
    window.addEventListener('mousemove', (e) => this.onMouseMove(e));
    window.addEventListener('mouseup', (e) => this.onMouseUp(e));

    // Wheel zoom
    this.canvas.addEventListener('wheel', (e) => {
      if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const delta = e.deltaY < 0 ? 0.08 : -0.08;
        this.setZoom(Math.max(0.2, Math.min(3.0, this.zoom + delta)), false);
      }
    }, { passive: false });

    // Touch support for tablets/phones
    this.canvas.addEventListener('touchstart', (e) => {
      if (e.touches.length === 1) {
        const touch = e.touches[0];
        this.onMouseDown({
          clientX: touch.clientX,
          clientY: touch.clientY,
          preventDefault: () => e.preventDefault()
        });
      }
    }, { passive: false });

    window.addEventListener('touchmove', (e) => {
      if (this.isDragging && e.touches.length === 1) {
        const touch = e.touches[0];
        this.onMouseMove({
          clientX: touch.clientX,
          clientY: touch.clientY
        });
      }
    }, { passive: false });

    window.addEventListener('touchend', () => {
      if (this.isDragging) this.onMouseUp();
    });

    // Listen to state events
    state.on('page_selected', () => {
      if (this.autoFit) this.fitToContainer();
      this.render();
    });
    state.on('page_updated', () => this.render());
    state.on('settings_updated', () => {
      if (this.autoFit) this.fitToContainer();
      this.render();
    });
  }

  fitToContainer() {
    const page = state.getCurrentPage();
    if (!page) return;

    const [ptW, ptH] = getPageDimensions(page.pageLandscape, state.settings.pageSize);
    const pad = this.container.clientWidth < 500 ? 24 : 40;
    const containerW = this.container.clientWidth - pad;
    const containerH = this.container.clientHeight - pad;

    if (containerW <= 0 || containerH <= 0) return;

    const scaleX = containerW / ptW;
    const scaleY = containerH / ptH;
    this.zoom = Math.max(0.2, Math.min(scaleX, scaleY, 1.25));
    this.autoFit = true;
    this.notifyZoom();
  }

  setZoom(zoom, autoFit = false) {
    this.zoom = zoom;
    this.autoFit = autoFit;
    this.notifyZoom();
    this.render();
  }

  notifyZoom() {
    if (typeof this.onZoomChange === 'function') {
      this.onZoomChange(this.zoom);
    }
  }

  render() {
    const dpr = window.devicePixelRatio || 1;
    const cw = this.container.clientWidth;
    const ch = this.container.clientHeight;

    if (cw === 0 || ch === 0) return;

    this.canvas.width = Math.round(cw * dpr);
    this.canvas.height = Math.round(ch * dpr);
    this.canvas.style.width = `${cw}px`;
    this.canvas.style.height = `${ch}px`;

    const ctx = this.ctx;
    ctx.resetTransform();
    ctx.scale(dpr, dpr);

    // Workspace background
    const isDark = state.settings.theme === 'dark';
    ctx.fillStyle = isDark ? '#090d16' : '#e2e8f0';
    ctx.fillRect(0, 0, cw, ch);

    const page = state.getCurrentPage();
    if (!page) {
      this.handles = {};
      this.imgRect = { x: 0, y: 0, w: 0, h: 0, cx: 0, cy: 0 };
      return;
    }

    // Calculate Page Rectangle on screen
    const [ptW, ptH] = getPageDimensions(page.pageLandscape, state.settings.pageSize);
    const pageW = ptW * this.zoom;
    const pageH = ptH * this.zoom;
    const pageX = (cw - pageW) / 2;
    const pageY = (ch - pageH) / 2;

    this.pageRect = { x: pageX, y: pageY, w: pageW, h: pageH };

    // Drop shadow
    ctx.save();
    ctx.shadowColor = 'rgba(0, 0, 0, 0.35)';
    ctx.shadowBlur = 18;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = 6;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(pageX, pageY, pageW, pageH);
    ctx.restore();

    // White paper background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(pageX, pageY, pageW, pageH);

    // Clip rendering to the page boundaries
    ctx.save();
    ctx.beginPath();
    ctx.rect(pageX, pageY, pageW, pageH);
    ctx.clip();

    // Render Page Content
    this.renderPageContent(ctx, page, pageX, pageY, pageW, pageH);

    // Render Page Number overlay if enabled
    if (state.settings.pageNumbers) {
      this.renderPageNumber(ctx, page, pageX, pageY, pageW, pageH);
    }

    ctx.restore();

    // Page Border
    ctx.strokeStyle = isDark ? 'rgba(255, 255, 255, 0.15)' : 'rgba(0, 0, 0, 0.12)';
    ctx.lineWidth = 1;
    ctx.strokeRect(pageX, pageY, pageW, pageH);

    // Interactive Handles
    if (page.sourceImage) {
      if (state.editorMode === 'crop') {
        this.renderCropOverlay(ctx, page, pageX, pageY, pageW, pageH);
      } else {
        this.renderResizeHandles(ctx);
      }
    }
  }

  renderPageContent(ctx, page, px, py, pw, ph) {
    if (!page.sourceImage) return;

    const img = page.sourceImage;
    const natW = img.naturalWidth || img.width;
    const natH = img.naturalHeight || img.height;

    const geom = computePageImageGeometry(natW, natH, pw, ph, {
      imageRotation: page.imageRotation,
      imageScale: page.imageScale,
      imageOffsetX: page.imageOffsetX,
      imageOffsetY: page.imageOffsetY,
      imageCrop: page.imageCrop,
      unitScale: this.zoom,
      defaultFit: state.settings.defaultImageFit || 'fill'
    });
    if (!geom) return;

    const cx = px + geom.cx;
    const cy = py + geom.cy;

    this.imgRect = {
      x: cx - geom.dispW / 2,
      y: cy - geom.dispH / 2,
      w: geom.dispW,
      h: geom.dispH,
      cx,
      cy
    };

    ctx.save();
    ctx.translate(cx, cy);
    if (geom.rad !== 0) {
      ctx.rotate(geom.rad);
    }
    ctx.drawImage(
      img,
      geom.sx, geom.sy, geom.sw, geom.sh,
      -geom.drawW / 2, -geom.drawH / 2, geom.drawW, geom.drawH
    );
    ctx.restore();
  }

  renderResizeHandles(ctx) {
    const { x, y, w, h } = this.imgRect;
    if (!w || !h) return;

    this.handles = {
      nw: { x: x, y: y },
      ne: { x: x + w, y: y },
      sw: { x: x, y: y + h },
      se: { x: x + w, y: y + h }
    };

    ctx.save();
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(x, y, w, h);
    ctx.setLineDash([]);

    const s = this.HANDLE_SIZE;
    for (const pt of Object.values(this.handles)) {
      ctx.fillStyle = '#22c55e';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.rect(pt.x - s, pt.y - s, s * 2, s * 2);
      ctx.fill();
      ctx.stroke();
    }
    ctx.restore();
  }

  renderCropOverlay(ctx, page, px, py, pw, ph) {
    const crop = page.imageCrop || [0, 0, 1, 1];
    const cropX = px + crop[0] * pw;
    const cropY = py + crop[1] * ph;
    const cropW = (crop[2] - crop[0]) * pw;
    const cropH = (crop[3] - crop[1]) * ph;

    ctx.save();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
    ctx.fillRect(px, py, pw, cropY - py);
    ctx.fillRect(px, cropY + cropH, pw, py + ph - (cropY + cropH));
    ctx.fillRect(px, cropY, cropX - px, cropH);
    ctx.fillRect(cropX + cropW, cropY, px + pw - (cropX + cropW), cropH);

    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2;
    ctx.strokeRect(cropX, cropY, cropW, cropH);

    ctx.fillStyle = '#38bdf8';
    const s = 6;
    ctx.fillRect(cropX - s, cropY - s, s * 2, s * 2);
    ctx.fillRect(cropX + cropW - s, cropY - s, s * 2, s * 2);
    ctx.fillRect(cropX - s, cropY + cropH - s, s * 2, s * 2);
    ctx.fillRect(cropX + cropW - s, cropY + cropH - s, s * 2, s * 2);
    ctx.restore();
  }

  renderPageNumber(ctx, page, px, py, pw, ph) {
    const s = state.settings;
    const pageIndex = state.pages.indexOf(page);
    if (pageIndex === 0 && s.skipCoverPage) return;

    const totalPages = state.pages.length;
    const pageNum = pageIndex + 1;
    const text = formatPageNumberText(pageNum, totalPages, s.pageNumberStyle);

    const fontSizePx = (s.pageNumberFontSize || 10) * this.zoom * (96 / 72);
    ctx.font = `${fontSizePx}px ${s.pageNumberFont || 'sans-serif'}`;
    ctx.fillStyle = s.pageNumberColor || '#1e293b';

    let tx = px + pw / 2;
    if (s.pageNumberAlignment === 'left') {
      ctx.textAlign = 'left';
      tx = px + s.pageNumberOffsetSide * this.zoom;
    } else if (s.pageNumberAlignment === 'right') {
      ctx.textAlign = 'right';
      tx = px + pw - s.pageNumberOffsetSide * this.zoom;
    } else {
      ctx.textAlign = 'center';
    }

    let ty = py + ph - s.pageNumberOffsetEdge * this.zoom;
    if (s.pageNumberPosition === 'top') {
      ty = py + s.pageNumberOffsetEdge * this.zoom + fontSizePx;
      ctx.textBaseline = 'top';
    } else {
      ctx.textBaseline = 'bottom';
    }

    ctx.fillText(text, tx, ty);
  }

  // --------------------------------------------------------------------------
  // Interaction Handlers (Mouse / Touch)
  // --------------------------------------------------------------------------

  getCanvasPoint(e) {
    const rect = this.canvas.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  }

  hitTestHandle(pt) {
    for (const [corner, hPt] of Object.entries(this.handles)) {
      const dist = Math.hypot(pt.x - hPt.x, pt.y - hPt.y);
      if (dist <= this.HANDLE_HIT_RADIUS) {
        return `handle-${corner}`;
      }
    }
    return null;
  }

  isPointInImage(pt) {
    const { x, y, w, h } = this.imgRect;
    return pt.x >= x && pt.x <= x + w && pt.y >= y && pt.y <= y + h;
  }

  onMouseDown(e) {
    const page = state.getCurrentPage();
    if (!page || !page.sourceImage) return;

    const pt = this.getCanvasPoint(e);

    const handleHit = this.hitTestHandle(pt);
    if (handleHit) {
      this.isDragging = true;
      this.dragMode = handleHit;
      this.dragStartMouse = pt;
      this.dragStartScale = page.imageScale || 1.0;
      this.dragStartOffset = { x: page.imageOffsetX || 0, y: page.imageOffsetY || 0 };
      if (e.preventDefault) e.preventDefault();
      return;
    }

    if (this.isPointInImage(pt)) {
      this.isDragging = true;
      this.dragMode = 'pan';
      this.dragStartMouse = pt;
      this.dragStartOffset = { x: page.imageOffsetX || 0, y: page.imageOffsetY || 0 };
      if (e.preventDefault) e.preventDefault();
    }
  }

  onMouseMove(e) {
    const page = state.getCurrentPage();
    if (!page || !page.sourceImage) return;

    const pt = this.getCanvasPoint(e);

    if (!this.isDragging) {
      const handleHit = this.hitTestHandle(pt);
      if (handleHit === 'handle-nw' || handleHit === 'handle-se') {
        this.canvas.style.cursor = 'nwse-resize';
      } else if (handleHit === 'handle-ne' || handleHit === 'handle-sw') {
        this.canvas.style.cursor = 'nesw-resize';
      } else if (this.isPointInImage(pt)) {
        this.canvas.style.cursor = 'grab';
      } else {
        this.canvas.style.cursor = 'default';
      }
      return;
    }

    const dx = pt.x - this.dragStartMouse.x;
    const dy = pt.y - this.dragStartMouse.y;

    if (this.dragMode === 'pan') {
      this.canvas.style.cursor = 'grabbing';
      const offsetPtX = this.dragStartOffset.x + dx / this.zoom;
      const offsetPtY = this.dragStartOffset.y + dy / this.zoom;
      state.updateCurrentPage({
        imageOffsetX: Math.round(offsetPtX * 10) / 10,
        imageOffsetY: Math.round(offsetPtY * 10) / 10
      });
      return;
    }

    if (this.dragMode && this.dragMode.startsWith('handle-')) {
      const cx = this.imgRect.cx;
      const cy = this.imgRect.cy;

      const startDist = Math.hypot(this.dragStartMouse.x - cx, this.dragStartMouse.y - cy);
      const currentDist = Math.hypot(pt.x - cx, pt.y - cy);

      if (startDist > 5) {
        const factor = currentDist / startDist;
        const newScale = Math.max(0.1, Math.min(4.0, this.dragStartScale * factor));
        state.updateCurrentPage({ imageScale: Math.round(newScale * 100) / 100 });
      }
    }
  }

  onMouseUp() {
    this.isDragging = false;
    this.dragMode = null;
    this.canvas.style.cursor = 'default';
  }
}
