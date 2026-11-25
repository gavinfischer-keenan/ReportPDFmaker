/**
 * PDF Builder for ReportPDFmaker Web
 * 100% Client-Side PDF assembly using PDF-Lib (window.PDFLib)
 * Replicates pdf_maker/converters/pdf_builder.py
 */

import { state, getPageDimensions } from './state.js';
import {
  computePageImageGeometry,
  dataUrlToUint8Array,
  parseHexColorRgb01,
  formatPageNumberText,
  parsePageRange
} from './math-utils.js';
import { wrapTextLines } from './text-layout.js';

const QUALITY_PRESETS = {
  archival: { dpr: 2.0, jpegQuality: 0.92 },
  balanced: { dpr: 1.5, jpegQuality: 0.80 },
  compact: { dpr: 1.0, jpegQuality: 0.65 }
};

export async function buildPdfDocument(onProgress = null, options = {}) {
  if (!window.PDFLib) {
    throw new Error('PDFLib library is not loaded');
  }

  const { PDFDocument, degrees, StandardFonts } = window.PDFLib;
  const pdfDoc = await PDFDocument.create();

  // Load standard fonts only if page numbers are enabled
  let fontMap = null;
  if (state.settings.pageNumbers) {
    fontMap = {
      'Helvetica': await pdfDoc.embedFont(StandardFonts.Helvetica),
      'Helvetica-Bold': await pdfDoc.embedFont(StandardFonts.HelveticaBold),
      'Times-Roman': await pdfDoc.embedFont(StandardFonts.TimesRoman),
      'Times-Bold': await pdfDoc.embedFont(StandardFonts.TimesRomanBold),
      'Courier': await pdfDoc.embedFont(StandardFonts.Courier),
      'Courier-Bold': await pdfDoc.embedFont(StandardFonts.CourierBold),
    };
  }

  // Cache parsed source PDFs so multi-page imports parse once instead of N times
  const srcPdfCache = new Map();
  const vectorFonts = {};
  const allPages = state.pages;
  const rangeSpec = options.pageRange !== undefined ? options.pageRange : state.settings.exportPageRange;
  const selectedIndices = parsePageRange(rangeSpec, allPages.length);
  if (selectedIndices.length === 0) {
    throw new Error('No pages matched the export page range.');
  }
  const pages = selectedIndices.map(idx => allPages[idx]);
  const total = pages.length;

  for (let i = 0; i < total; i++) {
    const pageItem = pages[i];
    if (onProgress) {
      onProgress(i + 1, total, pageItem.name);
    }

    const [ptW, ptH] = getPageDimensions(pageItem.pageLandscape, state.settings.pageSize, pageItem);

    // Copy native vector page when no raster edits have been applied
    const isUneditedPdf = (
      pageItem.sourceType === 'pdf' &&
      pageItem.pdfBytes &&
      !pageItem.imageRotation &&
      pageItem.pageLandscape === pageItem.sourceLandscape &&
      !pageItem.imageCrop &&
      pageItem.imageScale === 1.0 &&
      pageItem.imageOffsetX === 0 &&
      pageItem.imageOffsetY === 0
    );

    if (isUneditedPdf) {
      try {
        let srcPdf = srcPdfCache.get(pageItem.pdfBytes);
        if (!srcPdf) {
          srcPdf = await PDFDocument.load(pageItem.pdfBytes);
          srcPdfCache.set(pageItem.pdfBytes, srcPdf);
        }
        const [copiedPage] = await pdfDoc.copyPages(srcPdf, [pageItem.pdfPageIndex]);

        if (pageItem.rotation) {
          copiedPage.setRotation(degrees(pageItem.rotation));
        }
        pdfDoc.addPage(copiedPage);
        continue;
      } catch (err) {
        console.warn('Vector page copy fallback to rasterized render:', err);
      }
    }

    // Standard Page Generation (Blank/Divider, Image, Text, Docx, 3D, or modified PDF)
    const newPage = pdfDoc.addPage([ptW, ptH]);

    if (pageItem.sourceType === 'blank') {
      await tryDrawBlankDividerPage(pdfDoc, newPage, pageItem, ptW, ptH, vectorFonts);
      continue;
    }

    const drewVectorText = await tryDrawVectorTextPage(pdfDoc, newPage, pageItem, ptW, ptH, vectorFonts);
    if (!drewVectorText && pageItem.sourceImage) {
      await drawImageOnPage(pdfDoc, newPage, pageItem, ptW, ptH);
    }
  }

  // Draw optional Watermark / Header / Footer overlays
  await drawDocumentOverlays(pdfDoc, vectorFonts);

  // Draw Page Numbers if enabled
  if (state.settings.pageNumbers && fontMap) {
    drawPageNumbers(pdfDoc, fontMap);
  }

  // Apply PDF Metadata if provided
  const s = state.settings;
  if (s.pdfTitle) pdfDoc.setTitle(String(s.pdfTitle).trim());
  if (s.pdfAuthor) pdfDoc.setAuthor(String(s.pdfAuthor).trim());
  if (s.pdfSubject) pdfDoc.setSubject(String(s.pdfSubject).trim());
  pdfDoc.setCreator('Paper Nautilus · PDF Maker');

  const pdfBytes = await pdfDoc.save();
  return pdfBytes;
}

async function tryDrawBlankDividerPage(pdfDoc, page, pageItem, pw, ph, vectorFonts) {
  const title = String(pageItem.textHeader || '').trim();
  if (!title) return;
  try {
    const { StandardFonts, rgb } = window.PDFLib;
    if (!vectorFonts.sansBold) {
      vectorFonts.sansBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    }
    const font = vectorFonts.sansBold;
    font.encodeText(title);
    const size = 24;
    const tw = font.widthOfTextAtSize(title, size);
    page.drawText(title, {
      x: Math.max(36, (pw - tw) / 2),
      y: ph / 2,
      size,
      font,
      color: rgb(0.15, 0.2, 0.28)
    });
  } catch {
    // Keep blank page on unsupported characters
  }
}

async function drawDocumentOverlays(pdfDoc, vectorFonts) {
  const { StandardFonts, rgb, degrees } = window.PDFLib;
  const s = state.settings;
  const wmText = String(s.watermarkText || '').trim();
  const headerText = String(s.headerText || '').trim();
  const footerText = String(s.footerText || '').trim();
  if (!wmText && !headerText && !footerText) return;

  const docPages = pdfDoc.getPages();
  if (docPages.length === 0) return;

  let sans = null;
  let sansBold = null;
  if (headerText || footerText) {
    if (!vectorFonts.sans) vectorFonts.sans = await pdfDoc.embedFont(StandardFonts.Helvetica);
    sans = vectorFonts.sans;
  }
  if (wmText) {
    if (!vectorFonts.sansBold) vectorFonts.sansBold = await pdfDoc.embedFont(StandardFonts.HelveticaBold);
    sansBold = vectorFonts.sansBold;
  }

  const wmOpacity = Math.max(0.05, Math.min(0.8, Number(s.watermarkOpacity) || 0.18));
  const wmRgb = parseHexColorRgb01(s.watermarkColor || '#64748b');

  for (const page of docPages) {
    const { width: pw, height: ph } = page.getSize();
    if (headerText && sans) {
      try {
        sans.encodeText(headerText);
        page.drawText(headerText, { x: 40, y: ph - 24, size: 9, font: sans, color: rgb(0.35, 0.4, 0.48) });
      } catch { /* non-WinAnsi fallback */ }
    }
    if (footerText && sans) {
      try {
        sans.encodeText(footerText);
        page.drawText(footerText, { x: 40, y: 16, size: 9, font: sans, color: rgb(0.35, 0.4, 0.48) });
      } catch { /* non-WinAnsi fallback */ }
    }
    if (wmText && sansBold) {
      try {
        sansBold.encodeText(wmText);
        const fontSize = Math.max(24, Math.min(64, Math.min(pw, ph) * 0.09));
        const tw = sansBold.widthOfTextAtSize(wmText, fontSize);
        const angle = Math.PI / 4;
        const cx = pw / 2;
        const cy = ph / 2;
        page.drawText(wmText, {
          x: cx - (tw / 2) * Math.cos(angle),
          y: cy - (tw / 2) * Math.sin(angle),
          size: fontSize,
          font: sansBold,
          color: rgb(wmRgb.r, wmRgb.g, wmRgb.b),
          opacity: wmOpacity,
          rotate: degrees(45)
        });
      } catch { /* non-WinAnsi fallback */ }
    }
  }
}

/**
 * Draw crisp native vector text for unedited TXT/DOCX pages when WinAnsi encoding succeeds.
 * Falls back cleanly (returns false) when rotated, scaled, cropped, or containing non-WinAnsi characters.
 */
async function tryDrawVectorTextPage(pdfDoc, page, pageItem, pw, ph, vectorFonts) {
  const isUneditedText = (
    (pageItem.sourceType === 'text' || pageItem.sourceType === 'docx') &&
    typeof pageItem.textContent === 'string' &&
    !pageItem.imageRotation &&
    !pageItem.imageCrop &&
    pageItem.imageScale === 1.0 &&
    pageItem.imageOffsetX === 0 &&
    pageItem.imageOffsetY === 0
  );
  if (!isUneditedText) return false;

  try {
    const { StandardFonts, rgb } = window.PDFLib;
    if (!vectorFonts.mono) {
      vectorFonts.mono = await pdfDoc.embedFont(StandardFonts.Courier);
    }
    if (!vectorFonts.sans) {
      vectorFonts.sans = await pdfDoc.embedFont(StandardFonts.Helvetica);
    }

    const mono = vectorFonts.mono;
    const sans = vectorFonts.sans;
    const marginX = 42;
    const maxWidth = Math.max(120, pw - marginX * 2);
    const bodySize = 9.5;
    const lineHeight = 14.5;
    const header = pageItem.textHeader || pageItem.name || 'Document';
    const wrapped = wrapTextLines(
      pageItem.textContent,
      maxWidth,
      (line) => mono.widthOfTextAtSize(line, bodySize)
    );

    const startY = ph - 74;
    if (startY - wrapped.length * lineHeight < 42) {
      return false;
    }

    // Validate WinAnsi encodability before drawing anything on the page
    sans.encodeText(header);
    for (const line of wrapped) {
      if (line) mono.encodeText(line);
    }

    page.drawText(header, {
      x: marginX,
      y: ph - 40,
      size: 8.5,
      font: sans,
      color: rgb(0.39, 0.45, 0.55)
    });
    page.drawLine({
      start: { x: marginX, y: ph - 50 },
      end: { x: pw - marginX, y: ph - 50 },
      thickness: 0.75,
      color: rgb(0.89, 0.91, 0.94)
    });

    let y = startY;
    for (const line of wrapped) {
      if (line) {
        page.drawText(line, {
          x: marginX,
          y,
          size: bodySize,
          font: mono,
          color: rgb(0.12, 0.16, 0.23)
        });
      }
      y -= lineHeight;
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Accurately renders and embeds an image with scale, aspect ratio lock,
 * rotation, offsets, and hard clipping at page boundaries.
 */
async function drawImageOnPage(pdfDoc, page, pageItem, pw, ph) {
  const img = pageItem.sourceImage;
  const natW = img.naturalWidth || img.width;
  const natH = img.naturalHeight || img.height;

  if (!natW || !natH) return;

  const preset = QUALITY_PRESETS[state.settings.exportQuality] || QUALITY_PRESETS.archival;
  const dpr = preset.dpr;
  const renderCanvas = document.createElement('canvas');
  renderCanvas.width = Math.round(pw * dpr);
  renderCanvas.height = Math.round(ph * dpr);
  const ctx = renderCanvas.getContext('2d');

  // Strict page bounds clipping
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, renderCanvas.width, renderCanvas.height);
  ctx.clip();

  // White paper base
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, renderCanvas.width, renderCanvas.height);

  const geom = computePageImageGeometry(natW, natH, renderCanvas.width, renderCanvas.height, {
    imageRotation: pageItem.imageRotation,
    imageScale: pageItem.imageScale,
    imageOffsetX: pageItem.imageOffsetX,
    imageOffsetY: pageItem.imageOffsetY,
    imageCrop: pageItem.imageCrop,
    unitScale: dpr,
    defaultFit: state.settings.defaultImageFit || 'fill'
  });

  if (geom) {
    ctx.translate(geom.cx, geom.cy);
    if (geom.rad !== 0) {
      ctx.rotate(geom.rad);
    }
    ctx.drawImage(
      img,
      geom.sx, geom.sy, geom.sw, geom.sh,
      -geom.drawW / 2, -geom.drawH / 2, geom.drawW, geom.drawH
    );
  }

  ctx.restore();

  const dataUrl = renderCanvas.toDataURL('image/jpeg', preset.jpegQuality);
  const imgBytes = dataUrlToUint8Array(dataUrl);
  const embeddedImage = await pdfDoc.embedJpg(imgBytes);

  page.drawImage(embeddedImage, {
    x: 0,
    y: 0,
    width: pw,
    height: ph
  });
}

/**
 * Draws page numbers across all pages according to configuration
 */
function drawPageNumbers(pdfDoc, fontMap) {
  const { rgb } = window.PDFLib;
  const s = state.settings;
  const docPages = pdfDoc.getPages();
  const total = docPages.length;

  const font = fontMap[s.pageNumberFont] || fontMap['Helvetica'];
  const fontSize = s.pageNumberFontSize || 10;
  const { r, g, b } = parseHexColorRgb01(s.pageNumberColor || '#1e293b');
  const color = rgb(r, g, b);

  for (let i = 0; i < total; i++) {
    if (i === 0 && s.skipCoverPage) continue;

    const page = docPages[i];
    const { width, height } = page.getSize();
    const pageNum = i + 1;
    const text = formatPageNumberText(pageNum, total, s.pageNumberStyle);

    const textWidth = font.widthOfTextAtSize(text, fontSize);
    const textHeight = font.heightAtSize(fontSize);

    let x = (width - textWidth) / 2;
    if (s.pageNumberAlignment === 'left') {
      x = s.pageNumberOffsetSide;
    } else if (s.pageNumberAlignment === 'right') {
      x = width - s.pageNumberOffsetSide - textWidth;
    }

    let y = s.pageNumberOffsetEdge;
    if (s.pageNumberPosition === 'top') {
      y = height - s.pageNumberOffsetEdge - textHeight;
    }

    page.drawText(text, {
      x: Math.max(0, x),
      y: Math.max(0, y),
      size: fontSize,
      font,
      color
    });
  }
}

/**
 * Triggers instant browser download of Uint8Array PDF
 */
export function downloadPdf(bytes, filename = 'document.pdf') {
  const blob = new Blob([bytes], { type: 'application/pdf' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
