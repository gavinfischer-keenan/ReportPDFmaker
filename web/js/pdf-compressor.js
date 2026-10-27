/**
 * Client-Side PDF Compressor for ReportPDFmaker Web
 * Mirrors pdf_compressor.py & shrink_dialog.py
 * Supports Light, Standard, Aggressive, and Grayscale compression 100% in-browser!
 */

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

  // Level configuration
  const config = {
    light: { scale: 2.0, quality: 0.88, grayscale: false },
    standard: { scale: 1.5, quality: 0.75, grayscale: false },
    aggressive: { scale: 1.0, quality: 0.60, grayscale: false },
    grayscale: { scale: 1.2, quality: 0.65, grayscale: true }
  }[level] || { scale: 1.5, quality: 0.75, grayscale: false };

  // Load document with PDF.js
  const loadingTask = window.pdfjsLib.getDocument({ data: pdfBytes.slice(), isEvalSupported: false, cMapUrl: new URL('../vendor/cmaps/', import.meta.url).href, cMapPacked: true, standardFontDataUrl: new URL('../vendor/standard_fonts/', import.meta.url).href });
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

    // Convert to compressed JPEG data
    const jpegDataUrl = canvas.toDataURL('image/jpeg', config.quality);
    const imgBytes = await fetch(jpegDataUrl).then(r => r.arrayBuffer());
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
    return {bytes: pdfBytes, originalSize, compressedSize: originalSize, savedPercent: 0, keptOriginal: true};
  }
  const savedPercent = Math.max(0, Math.round(((originalSize - compressedSize) / originalSize) * 100));

  return {
    bytes: compressedBytes,
    originalSize,
    compressedSize,
    savedPercent
  };
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}
