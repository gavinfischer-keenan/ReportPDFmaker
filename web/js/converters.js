import { wrapTextLines } from './text-layout.js';
/**
 * Converters for ReportPDFmaker Web
 * Handles Images, PDF multi-page extraction, Word DOCX via Mammoth, Plain Text, and 3D
 */

import { PageItem, getPageDimensions } from './state.js';

// Configure PDF.js worker
if (window.pdfjsLib) {
  window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'vendor/pdf.worker.min.js';
}

/**
 * Creates an image element from a Data URL or Blob
 */
export function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = (e) => reject(new Error('Failed to load image: ' + e));
    img.src = src;
  });
}

/**
 * Convert an image file into a PageItem
 */
export async function convertImageFile(file) {
  const dataUrl = await readFileAsDataURL(file);
  const img = await loadImage(dataUrl);
  
  // Render thumbnail
  const thumbUrl = createThumbnail(img, 180, 240);

  return new PageItem({
    name: file.name,
    sourceType: 'image',
    sourceImage: img,
    thumbnailUrl: thumbUrl,
    pageLandscape: img.naturalWidth > img.naturalHeight
  });
}

/**
 * Convert a multi-page PDF file into an array of PageItem objects
 */
export async function convertPdfFile(file) {
  const arrayBuffer = await readFileAsArrayBuffer(file);
  const pdfBytes = new Uint8Array(arrayBuffer);
  
  const loadingTask = window.pdfjsLib.getDocument({ data: pdfBytes.slice(), isEvalSupported: false, cMapUrl: new URL('../vendor/cmaps/', import.meta.url).href, cMapPacked: true, standardFontDataUrl: new URL('../vendor/standard_fonts/', import.meta.url).href });
  const pdfDoc = await loadingTask.promise;
  const numPages = pdfDoc.numPages;
  const pages = [];

  for (let i = 1; i <= numPages; i++) {
    const pdfPage = await pdfDoc.getPage(i);
    const viewport = pdfPage.getViewport({ scale: 1.5 });
    
    // Render to canvas for preview / thumbnail
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    
    await pdfPage.render({
      canvasContext: ctx,
      viewport: viewport
    }).promise;

    const dataUrl = canvas.toDataURL('image/jpeg', 0.88);
    const img = await loadImage(dataUrl);
    const thumbUrl = createThumbnail(img, 180, 240);

    const isLandscape = viewport.width > viewport.height;

    pages.push(new PageItem({
      name: `${file.name} (p. ${i})`,
      sourceType: 'pdf',
      sourceImage: img,
      thumbnailUrl: thumbUrl,
      pdfBytes: pdfBytes,
      pdfPageIndex: i - 1,
      pageLandscape: isLandscape
    }));
  }

  return pages;
}

/**
 * Convert a Word (.docx) file into one or more PageItems using Mammoth.js
 */
export async function convertDocxFile(file) {
  const arrayBuffer = await readFileAsArrayBuffer(file);
  
  if (!window.mammoth) {
    throw new Error('Mammoth.js library not loaded');
  }

  const result = await window.mammoth.extractRawText({ arrayBuffer: arrayBuffer });
  const text = result.value || 'Empty document';
  
  return convertPlainText(text, file.name);
}

/**
 * Convert plain text into paginated PageItems
 */
export async function convertTextFile(file) {
  const text = await readFileAsText(file);
  return convertPlainText(text, file.name);
}

/**
 * Paginate plain text and render onto styled document canvas pages
 */
export async function convertPlainText(text, filename = 'Document.txt') {
  const measuringCanvas = document.createElement('canvas');
  const measuringContext = measuringCanvas.getContext('2d');
  measuringContext.font = '22px "Courier New", monospace';
  const lines = wrapTextLines(text, 1080, line => measuringContext.measureText(line).width);
  const linesPerPage = 42;
  const pages = [];
  
  const chunks = [];
  for (let i = 0; i < lines.length; i += linesPerPage) {
    chunks.push(lines.slice(i, i + linesPerPage));
  }
  if (chunks.length === 0) chunks.push(['']);

  for (let idx = 0; idx < chunks.length; idx++) {
    const chunkLines = chunks[idx];
    const pageNum = idx + 1;
    
    // Render text to canvas (high-res A4: 1240 x 1754 at 150 DPI)
    const cw = 1240;
    const ch = 1754;
    const canvas = document.createElement('canvas');
    canvas.width = cw;
    canvas.height = ch;
    const ctx = canvas.getContext('2d');
    
    // Background
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, cw, ch);
    
    // Header line
    ctx.fillStyle = '#64748b';
    ctx.font = '16px sans-serif';
    ctx.fillText(`${filename} — Page ${pageNum}`, 80, 70);
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(80, 85);
    ctx.lineTo(cw - 80, 85);
    ctx.stroke();

    // Body Text
    ctx.fillStyle = '#1e293b';
    ctx.font = '22px "Courier New", monospace';
    let y = 130;
    for (const line of chunkLines) {
      // Simple word wrap
      ctx.fillText(line, 80, y, cw - 160);
      y += 34;
      if (y > ch - 100) break;
    }

    const dataUrl = canvas.toDataURL('image/png');
    const img = await loadImage(dataUrl);
    const thumbUrl = createThumbnail(img, 180, 240);

    pages.push(new PageItem({
      name: `${filename} (p. ${pageNum})`,
      sourceType: 'text',
      sourceImage: img,
      thumbnailUrl: thumbUrl,
      textContent: chunkLines.join('\n'),
      pageLandscape: false
    }));
  }

  return pages;
}

/**
 * Creates a scaled thumbnail dataURL
 */
function createThumbnail(image, maxW, maxH) {
  const canvas = document.createElement('canvas');
  let w = image.naturalWidth || image.width;
  let h = image.naturalHeight || image.height;
  
  if (w <= 0 || h <= 0) {
    w = 200;
    h = 280;
  }
  
  const scale = Math.min(maxW / w, maxH / h);
  canvas.width = Math.max(1, Math.round(w * scale));
  canvas.height = Math.max(1, Math.round(h * scale));
  
  const ctx = canvas.getContext('2d');
  ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.82);
}

// Helpers
function readFileAsDataURL(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });
}

function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsText(file);
  });
}
