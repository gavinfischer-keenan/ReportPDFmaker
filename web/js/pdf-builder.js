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
  formatPageNumberText
} from './math-utils.js';

const QUALITY_PRESETS = {
  archival: { dpr: 2.0, jpegQuality: 0.92 },
  balanced: { dpr: 1.5, jpegQuality: 0.80 },
  compact: { dpr: 1.0, jpegQuality: 0.65 }
};

export async function buildPdfDocument(onProgress = null) {
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
  const pages = state.pages;
  const total = pages.length;

  for (let i = 0; i < total; i++) {
    const pageItem = pages[i];
    if (onProgress) {
      onProgress(i + 1, total, pageItem.name);
    }

    const [ptW, ptH] = getPageDimensions(pageItem.pageLandscape, state.settings.pageSize);

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

    // Standard Page Generation (Image, Text, Docx, 3D, or modified PDF)
    const newPage = pdfDoc.addPage([ptW, ptH]);

    if (pageItem.sourceImage) {
      await drawImageOnPage(pdfDoc, newPage, pageItem, ptW, ptH);
    }
  }

  // Draw Page Numbers if enabled
  if (state.settings.pageNumbers && fontMap) {
    drawPageNumbers(pdfDoc, fontMap);
  }

  const pdfBytes = await pdfDoc.save();
  return pdfBytes;
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
