/**
 * Pure Math, Geometry, Color, and Formatting Utilities
 * Shared across CanvasPreview, PDFBuilder, PDFCompressor, and unit tests.
 * Zero DOM dependencies so it runs identically in browsers and Node.js.
 */

export function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

/**
 * Compute crop source box, rotation swap, aspect-locked display box,
 * local pre-rotation draw box, and center offset for an image placed on a page.
 */
export function computePageImageGeometry(natW, natH, pageW, pageH, opts = {}) {
  if (!natW || !natH || !pageW || !pageH) return null;

  let sx = 0;
  let sy = 0;
  let sw = natW;
  let sh = natH;

  if (Array.isArray(opts.imageCrop) && opts.imageCrop.length === 4) {
    const cl = clamp(Number(opts.imageCrop[0]) || 0, 0, 0.99);
    const ct = clamp(Number(opts.imageCrop[1]) || 0, 0, 0.99);
    const cr = clamp(Number(opts.imageCrop[2]) ?? 1, cl + 0.01, 1);
    const cb = clamp(Number(opts.imageCrop[3]) ?? 1, ct + 0.01, 1);
    sx = cl * natW;
    sy = ct * natH;
    sw = Math.max(1, (cr - cl) * natW);
    sh = Math.max(1, (cb - ct) * natH);
  }

  const rot = ((Number(opts.imageRotation) || 0) % 360 + 360) % 360;
  const isSwapped = rot === 90 || rot === 270;
  const effW = isSwapped ? sh : sw;
  const effH = isSwapped ? sw : sh;

  const fitFactor = opts.defaultFit === 'margin' ? 0.88 : 1.0;
  const availW = pageW * fitFactor;
  const availH = pageH * fitFactor;

  const fitScale = Math.min(availW / effW, availH / effH);
  const imageScale = opts.imageScale !== undefined ? (Number(opts.imageScale) || 1.0) : 1.0;
  const finalScale = fitScale * imageScale;

  const dispW = effW * finalScale;
  const dispH = effH * finalScale;

  // Local draw dimensions before ctx.rotate(rad) is applied
  const drawW = isSwapped ? dispH : dispW;
  const drawH = isSwapped ? dispW : dispH;

  const unitScale = opts.unitScale !== undefined ? Number(opts.unitScale) : 1.0;
  const cx = pageW / 2 + (Number(opts.imageOffsetX) || 0) * unitScale;
  const cy = pageH / 2 + (Number(opts.imageOffsetY) || 0) * unitScale;

  return {
    sx,
    sy,
    sw,
    sh,
    rot,
    rad: (rot * Math.PI) / 180,
    isSwapped,
    effW,
    effH,
    fitScale,
    finalScale,
    dispW,
    dispH,
    drawW,
    drawH,
    cx,
    cy
  };
}

/**
 * Fast synchronous base64 data-URL decoder to Uint8Array without fetch() overhead.
 */
export function dataUrlToUint8Array(dataUrl) {
  const commaIdx = dataUrl.indexOf(',');
  const base64 = commaIdx >= 0 ? dataUrl.slice(commaIdx + 1) : dataUrl;

  if (typeof atob === 'function') {
    const binStr = atob(base64);
    const len = binStr.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binStr.charCodeAt(i);
    }
    return bytes;
  }

  if (typeof Buffer !== 'undefined') {
    const buf = Buffer.from(base64, 'base64');
    return new Uint8Array(buf.buffer, buf.byteOffset, buf.byteLength);
  }

  throw new Error('No base64 decoder available');
}

/**
 * Parse #rgb or #rrggbb hex color into normalized [0, 1] RGB channels.
 */
export function parseHexColorRgb01(hex) {
  let c = String(hex || '').trim().replace('#', '');
  if (c.length === 3) {
    c = c[0] + c[0] + c[1] + c[1] + c[2] + c[2];
  }
  const num = parseInt(c, 16);
  if (!/^[0-9a-fA-F]{6}$/.test(c) || Number.isNaN(num)) {
    return { r: 30 / 255, g: 41 / 255, b: 59 / 255 };
  }
  return {
    r: ((num >> 16) & 255) / 255,
    g: ((num >> 8) & 255) / 255,
    b: (num & 255) / 255
  };
}

/**
 * Format a page number string consistently across preview and PDF export.
 */
export function formatPageNumberText(pageNum, totalPages, style = 'plain') {
  if (style === 'dashes') return `— ${pageNum} —`;
  if (style === 'page_x') return `Page ${pageNum}`;
  if (style === 'page_x_of_y') return `Page ${pageNum} of ${totalPages}`;
  return `${pageNum}`;
}

/**
 * Format byte counts into human-readable file size strings.
 */
export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${Math.round(bytes)} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

/**
 * Parse a 1-based page range string (e.g. '1-3, 5') into 0-based indices.
 * Empty / 'all' returns all indices [0 .. totalPages - 1].
 */
export function parsePageRange(spec, totalPages) {
  if (!totalPages || totalPages <= 0) return [];
  const raw = String(spec || '').trim();
  if (!raw || raw.toLowerCase() === 'all') {
    return Array.from({ length: totalPages }, (_, i) => i);
  }

  const selected = [];
  const seen = new Set();
  for (const token of raw.split(',')) {
    const part = token.trim();
    if (!part) {
      throw new Error(`Empty token in page range "${raw}".`);
    }
    if (part.includes('-')) {
      const pieces = part.split('-').map(p => p.trim());
      if (pieces.length !== 2 || !/^\d+$/.test(pieces[0]) || !/^\d+$/.test(pieces[1])) {
        throw new Error(`Invalid page range "${part}".`);
      }
      const start = parseInt(pieces[0], 10);
      const end = parseInt(pieces[1], 10);
      if (start < 1 || end < 1 || start > totalPages || end > totalPages) {
        throw new Error(`Page range "${part}" out of bounds (1-${totalPages}).`);
      }
      const step = start <= end ? 1 : -1;
      for (let num = start; step > 0 ? num <= end : num >= end; num += step) {
        const idx = num - 1;
        if (!seen.has(idx)) {
          seen.add(idx);
          selected.push(idx);
        }
      }
    } else {
      if (!/^\d+$/.test(part)) {
        throw new Error(`Invalid page number "${part}".`);
      }
      const num = parseInt(part, 10);
      if (num < 1 || num > totalPages) {
        throw new Error(`Page ${num} out of bounds (1-${totalPages}).`);
      }
      const idx = num - 1;
      if (!seen.has(idx)) {
        seen.add(idx);
        selected.push(idx);
      }
    }
  }
  return selected;
}
