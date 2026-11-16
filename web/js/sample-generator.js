/**
 * Client-Side Sample & Template Generator
 * Provides realistic 3-page sample reports and sample PDF files for empty states
 * without requiring any network fetches or server assets.
 */

import { PageItem } from './state.js';
import { loadImage, convertPlainText } from './converters.js';
import { dataUrlToUint8Array } from './math-utils.js';

function createSampleThumbnail(canvas, maxW = 180, maxH = 240) {
  const thumb = document.createElement('canvas');
  const scale = Math.min(maxW / canvas.width, maxH / canvas.height);
  thumb.width = Math.max(1, Math.round(canvas.width * scale));
  thumb.height = Math.max(1, Math.round(canvas.height * scale));
  const tctx = thumb.getContext('2d');
  tctx.drawImage(canvas, 0, 0, thumb.width, thumb.height);
  return thumb.toDataURL('image/jpeg', 0.84);
}

async function renderCoverCanvas() {
  const w = 1240;
  const h = 1754;
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');

  // Clean paper background
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, h);

  // Header accent band
  ctx.fillStyle = '#312e81';
  ctx.fillRect(0, 0, w, 420);

  ctx.fillStyle = '#6366f1';
  ctx.fillRect(0, 408, w, 16);

  // Header badge & title
  ctx.fillStyle = '#c7d2fe';
  ctx.font = 'bold 24px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillText('PAPER NAUTILUS · SAMPLE TEMPLATE', 96, 130);

  ctx.fillStyle = '#ffffff';
  ctx.font = 'bold 64px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillText('Quarterly Operations', 96, 235);
  ctx.fillText('& Engineering Report', 96, 315);

  // Summary card
  ctx.fillStyle = '#f8fafc';
  ctx.strokeStyle = '#cbd5e1';
  ctx.lineWidth = 2;
  ctx.fillRect(96, 510, w - 192, 240);
  ctx.strokeRect(96, 510, w - 192, 240);

  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 30px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillText('Executive Overview', 136, 575);

  ctx.fillStyle = '#334155';
  ctx.font = '24px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillText('This 3-page sample report demonstrates mixed Portrait images,', 136, 635);
  ctx.fillText('Landscape charts, and formatted text pages assembled in-browser.', 136, 675);
  ctx.fillText('Try resizing handles, rotating content, or toggling page numbers.', 136, 715);

  // Three KPI boxes
  const kpis = [
    { label: 'Processing', value: '100% Local', sub: 'Zero document uploads' },
    { label: 'Formats', value: '5 Types', sub: 'IMG, PDF, DOCX, TXT, 3D' },
    { label: 'Print DPI', value: '300 DPI', sub: 'Archival or compact' }
  ];
  const boxW = (w - 192 - 48) / 3;
  kpis.forEach((kpi, idx) => {
    const bx = 96 + idx * (boxW + 24);
    const by = 815;
    ctx.fillStyle = '#eef2ff';
    ctx.fillRect(bx, by, boxW, 210);
    ctx.strokeStyle = '#c7d2fe';
    ctx.strokeRect(bx, by, boxW, 210);

    ctx.fillStyle = '#4f46e5';
    ctx.font = 'bold 20px sans-serif';
    ctx.fillText(kpi.label.toUpperCase(), bx + 28, by + 56);

    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 42px sans-serif';
    ctx.fillText(kpi.value, bx + 28, by + 118);

    ctx.fillStyle = '#475569';
    ctx.font = '20px sans-serif';
    ctx.fillText(kpi.sub, bx + 28, by + 168);
  });

  // Checklist footer block
  ctx.fillStyle = '#1e293b';
  ctx.font = 'bold 28px sans-serif';
  ctx.fillText('Quick Actions to Try:', 96, 1140);

  const tips = [
    '• Press Cmd/Ctrl+K to open the Command Palette and jump anywhere.',
    '• Press ? to view keyboard shortcuts for common editing actions.',
    '• Drag green corner handles on the canvas to resize this image.',
    '• Enable Page Numbers in the right panel to preview live headers/footers.'
  ];
  ctx.fillStyle = '#334155';
  ctx.font = '24px sans-serif';
  tips.forEach((tip, i) => {
    ctx.fillText(tip, 96, 1205 + i * 52);
  });

  const dataUrl = canvas.toDataURL('image/png');
  const img = await loadImage(dataUrl);
  return new PageItem({
    name: '01_Sample_Cover.png',
    sourceType: 'image',
    sourceImage: img,
    thumbnailUrl: createSampleThumbnail(canvas),
    pageLandscape: false
  });
}

async function renderChartCanvas() {
  const w = 1754;
  const h = 1240;
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, h);

  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 44px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  ctx.fillText('Performance & Throughput Metrics (Landscape)', 96, 116);

  ctx.fillStyle = '#64748b';
  ctx.font = '24px sans-serif';
  ctx.fillText('Sample landscape chart page — press O to toggle Portrait / Landscape', 96, 164);

  // Chart area
  const cx = 140;
  const cy = 240;
  const cw = w - 280;
  const ch = 560;
  ctx.fillStyle = '#f8fafc';
  ctx.fillRect(cx, cy, cw, ch);
  ctx.strokeStyle = '#cbd5e1';
  ctx.lineWidth = 2;
  ctx.strokeRect(cx, cy, cw, ch);

  // Grid lines & bars
  const bars = [
    { label: 'Q1 Baseline', val: 0.45, color: '#94a3b8' },
    { label: 'Q2 Batching', val: 0.68, color: '#6366f1' },
    { label: 'Q3 Caching', val: 0.84, color: '#4f46e5' },
    { label: 'Q4 Optimized', val: 0.96, color: '#10b981' }
  ];

  for (let g = 1; g <= 4; g++) {
    const gy = cy + ch - (ch * g) / 4;
    ctx.strokeStyle = '#e2e8f0';
    ctx.beginPath();
    ctx.moveTo(cx, gy);
    ctx.lineTo(cx + cw, gy);
    ctx.stroke();
  }

  const slotW = cw / bars.length;
  bars.forEach((b, i) => {
    const bw = 130;
    const bh = Math.round((ch - 80) * b.val);
    const bx = cx + i * slotW + (slotW - bw) / 2;
    const by = cy + ch - 40 - bh;

    ctx.fillStyle = b.color;
    ctx.fillRect(bx, by, bw, bh);

    ctx.fillStyle = '#0f172a';
    ctx.font = 'bold 26px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(`${Math.round(b.val * 100)}%`, bx + bw / 2, by - 16);

    ctx.fillStyle = '#334155';
    ctx.font = '22px sans-serif';
    ctx.fillText(b.label, bx + bw / 2, cy + ch + 38);
  });
  ctx.textAlign = 'left';

  // Summary strip
  ctx.fillStyle = '#0f172a';
  ctx.font = 'bold 26px sans-serif';
  ctx.fillText('Key Takeaway:', 140, 960);
  ctx.fillStyle = '#334155';
  ctx.font = '24px sans-serif';
  ctx.fillText('Document caching and direct binary encoding reduced PDF assembly overhead across multi-page exports.', 140, 1006);

  const dataUrl = canvas.toDataURL('image/png');
  const img = await loadImage(dataUrl);
  return new PageItem({
    name: '02_Metrics_Chart.png',
    sourceType: 'image',
    sourceImage: img,
    thumbnailUrl: createSampleThumbnail(canvas, 240, 180),
    pageLandscape: true
  });
}

export async function createSampleReportPages() {
  const cover = await renderCoverCanvas();
  const chart = await renderChartCanvas();
  const notesText = [
    'APPENDIX A — CLIENT-SIDE PROCESSING NOTES',
    '=========================================',
    '',
    '1. Privacy Guarantee',
    'All image rendering, text layout, DOCX extraction, and PDF compression run entirely inside your local browser memory.',
    '',
    '2. Supported Workflows',
    '- Combine mixed Portrait and Landscape pages in a single report.',
    '- Drag and drop cards in the Document Pages list to reorder.',
    '- Rotate images (0, +90, 180, 270 deg) without changing page orientation.',
    '- Add customizable page headers/footers with live preview.',
    '',
    '3. Keyboard Shortcuts',
    'Use Cmd/Ctrl+K to open the Command Palette or press ? to view all keyboard shortcuts.'
  ].join('\n');

  const notePages = await convertPlainText(notesText, '03_Appendix_Notes.txt');
  return [cover, chart, ...notePages];
}

/**
 * Generates a realistic 2-page PDF File object for trying the Shrink PDF tool.
 */
export async function createSamplePdfFile() {
  if (!window.PDFLib) {
    throw new Error('PDFLib is not available');
  }
  const { PDFDocument, StandardFonts, rgb } = window.PDFLib;
  const doc = await PDFDocument.create();
  const font = await doc.embedFont(StandardFonts.HelveticaBold);
  const bodyFont = await doc.embedFont(StandardFonts.Helvetica);

  // Create a dense colorful raster image to embed so compression produces real savings
  const canvas = document.createElement('canvas');
  canvas.width = 1200;
  canvas.height = 800;
  const ctx = canvas.getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 1200, 800);
  grad.addColorStop(0, '#4f46e5');
  grad.addColorStop(0.5, '#0ea5e9');
  grad.addColorStop(1, '#10b981');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 1200, 800);
  ctx.fillStyle = 'rgba(255,255,255,0.25)';
  for (let i = 0; i < 18; i++) {
    ctx.beginPath();
    ctx.arc(80 + i * 65, 400 + Math.sin(i) * 180, 90, 0, Math.PI * 2);
    ctx.fill();
  }
  const pngDataUrl = canvas.toDataURL('image/png');
  const pngBytes = dataUrlToUint8Array(pngDataUrl);
  const embeddedPng = await doc.embedPng(pngBytes);

  const p1 = doc.addPage([595.28, 841.89]);
  p1.drawText('Paper Nautilus Sample PDF', { x: 54, y: 770, size: 22, font, color: rgb(0.1, 0.12, 0.22) });
  p1.drawText('Use this sample document to benchmark compression presets.', { x: 54, y: 740, size: 12, font: bodyFont, color: rgb(0.3, 0.35, 0.45) });
  p1.drawImage(embeddedPng, { x: 54, y: 360, width: 487, height: 325 });

  const p2 = doc.addPage([595.28, 841.89]);
  p2.drawText('Page 2 — Technical Appendix', { x: 54, y: 770, size: 18, font, color: rgb(0.1, 0.12, 0.22) });
  p2.drawText('High-resolution rasterized graphics benefit most from Standard or Aggressive compression.', { x: 54, y: 736, size: 11, font: bodyFont, color: rgb(0.3, 0.35, 0.45) });

  const bytes = await doc.save();
  return new File([bytes], 'Sample_Report_Uncompressed.pdf', { type: 'application/pdf' });
}
