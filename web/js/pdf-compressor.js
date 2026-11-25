/**
 * Client-Side PDF Compressor for ReportPDFmaker Web
 * Mirrors pdf_compressor.py & shrink_dialog.py
 * Supports Light, Standard, Aggressive, and Grayscale compression 100% in-browser!
 */

import { dataUrlToUint8Array, formatFileSize } from './math-utils.js';

export { formatFileSize };

export async function compressPdf(fileOrBytes, level = 'standard', onProgress = null) {
  if (!window.pdfjsLib || !window.PDFLib) {
    throw new Error('PDF libraries are required for compression');
  }

  let pdfBytes;
  if (fileOrBytes instanceof File) {
    pdfBytes = new Uint8Array(await fileOrBytes.arrayBuffer());
  } else {
    pdfBytes = fileOrBytes;
  }

  const originalSize = pdfBytes.byteLength;

  // Level configuration (72 PDF points = 1 inch)
  const config = {
    light: { scale: 200 / 72, quality: 0.88, grayscale: false },
    standard: { scale: 150 / 72, quality: 0.75, grayscale: false },
    aggressive: { scale: 96 / 72, quality: 0.50, grayscale: false },
    grayscale: { scale: 120 / 72, quality: 0.65, grayscale: true }
  }[level] || { scale: 150 / 72, quality: 0.75, grayscale: false };

  // Load document with PDF.js
  const loadingTask = window.pdfjsLib.getDocument({
    data: pdfBytes.slice(),
    isEvalSupported: false,
    cMapUrl: new URL('../vendor/cmaps/', import.meta.url).href,
    cMapPacked: true,
    standardFontDataUrl: new URL('../vendor/standard_fonts/', import.meta.url).href
  });
  const srcDoc = await loadingTask.promise;
  const numPages = srcDoc.numPages;

  // New compressed document with PDF-Lib
  const { PDFDocument } = window.PDFLib;
  const outDoc = await PDFDocument.create();

  for (let i = 1; i <= numPages; i++) {
    if (onProgress) {
      onProgress(i, numPages, `Compressing page ${i} of ${numPages}…`);
    }

    const page = await srcDoc.getPage(i);
    const viewport = page.getViewport({ scale: config.scale });
    const originalViewport = page.getViewport({ scale: 1.0 });

    const canvas = document.createElement('canvas');
    canvas.width = Math.round(viewport.width);
    canvas.height = Math.round(viewport.height);
    const ctx = canvas.getContext('2d');

    if (config.grayscale) {
      ctx.filter = 'grayscale(100%) contrast(105%)';
    }

    await page.render({
      canvasContext: ctx,
      viewport: viewport
    }).promise;

    // Convert to compressed JPEG data without fetch() overhead
    const jpegDataUrl = canvas.toDataURL('image/jpeg', config.quality);
    const imgBytes = dataUrlToUint8Array(jpegDataUrl);
    const embeddedImg = await outDoc.embedJpg(imgBytes);

    const newPage = outDoc.addPage([originalViewport.width, originalViewport.height]);
    newPage.drawImage(embeddedImg, {
      x: 0,
      y: 0,
      width: originalViewport.width,
      height: originalViewport.height
    });
  }

  const compressedBytes = await outDoc.save();
  const compressedSize = compressedBytes.byteLength;
  if (compressedSize >= originalSize) {
    return {
      bytes: pdfBytes,
      originalSize,
      compressedSize: originalSize,
      savedPercent: 0,
      keptOriginal: true
    };
  }
  const savedPercent = Math.max(0, Math.round(((originalSize - compressedSize) / originalSize) * 100));

  return {
    bytes: compressedBytes,
    originalSize,
    compressedSize,
    savedPercent
  };
}
