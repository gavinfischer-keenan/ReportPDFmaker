/**
 * Client-Side IndexedDB Session Store & Serialization Helpers
 * Automatically preserves the active workspace across browser reloads.
 */

import { PageItem } from './state.js';

const DB_NAME = 'paper_nautilus_session';
const STORE_NAME = 'workspace';
const SESSION_KEY = 'latest';

function imageToDataUrl(img) {
  if (!img) return null;
  if (typeof img.src === 'string' && img.src.startsWith('data:')) {
    return img.src;
  }
  if (typeof document !== 'undefined') {
    try {
      const w = img.naturalWidth || img.width || 0;
      const h = img.naturalHeight || img.height || 0;
      if (w > 0 && h > 0) {
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        canvas.getContext('2d').drawImage(img, 0, 0, w, h);
        return canvas.toDataURL('image/png');
      }
    } catch {
      return null;
    }
  }
  return null;
}

export function serializeSessionPages(pages = [], currentIndex = -1) {
  return {
    version: 1,
    savedAt: Date.now(),
    currentIndex,
    pages: pages.map(p => ({
      id: p.id,
      name: p.name,
      sourceType: p.sourceType,
      pageLandscape: Boolean(p.pageLandscape),
      sourceLandscape: Boolean(p.sourceLandscape),
      rotation: p.rotation || 0,
      imageRotation: p.imageRotation || 0,
      imageScale: p.imageScale !== undefined ? p.imageScale : 1.0,
      imageOffsetX: p.imageOffsetX || 0,
      imageOffsetY: p.imageOffsetY || 0,
      imageCrop: Array.isArray(p.imageCrop) ? [...p.imageCrop] : null,
      thumbnailUrl: p.thumbnailUrl || null,
      textContent: p.textContent || '',
      textHeader: p.textHeader || '',
      pdfBytes: p.pdfBytes ? new Uint8Array(p.pdfBytes) : null,
      pdfPageIndex: p.pdfPageIndex ?? 0,
      imageDataUrl: imageToDataUrl(p.sourceImage)
    }))
  };
}

export async function deserializeSessionPages(payload, loadImageFn = null) {
  if (!payload || !Array.isArray(payload.pages)) {
    return { pages: [], currentIndex: -1 };
  }
  const pages = [];
  for (const raw of payload.pages) {
    let sourceImage = null;
    if (raw.imageDataUrl && typeof loadImageFn === 'function') {
      try {
        sourceImage = await loadImageFn(raw.imageDataUrl);
      } catch {
        sourceImage = null;
      }
    }
    pages.push(new PageItem({
      id: raw.id,
      name: raw.name,
      sourceType: raw.sourceType,
      pageLandscape: raw.pageLandscape,
      sourceLandscape: raw.sourceLandscape,
      rotation: raw.rotation,
      imageRotation: raw.imageRotation,
      imageScale: raw.imageScale,
      imageOffsetX: raw.imageOffsetX,
      imageOffsetY: raw.imageOffsetY,
      imageCrop: Array.isArray(raw.imageCrop) ? [...raw.imageCrop] : null,
      thumbnailUrl: raw.thumbnailUrl,
      textContent: raw.textContent,
      textHeader: raw.textHeader,
      pdfBytes: raw.pdfBytes ? new Uint8Array(raw.pdfBytes) : null,
      pdfPageIndex: raw.pdfPageIndex ?? 0,
      sourceImage
    }));
  }
  const currentIndex = pages.length === 0
    ? -1
    : Math.max(0, Math.min(payload.currentIndex ?? 0, pages.length - 1));
  return { pages, currentIndex };
}

function openSessionDb() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      resolve(null);
      return;
    }
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveSessionToIdb(payload) {
  try {
    const db = await openSessionDb();
    if (!db) return false;
    return await new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).put(payload, SESSION_KEY);
      tx.oncomplete = () => { db.close(); resolve(true); };
      tx.onerror = () => { db.close(); resolve(false); };
    });
  } catch {
    return false;
  }
}

export async function loadSessionFromIdb() {
  try {
    const db = await openSessionDb();
    if (!db) return null;
    return await new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const req = tx.objectStore(STORE_NAME).get(SESSION_KEY);
      req.onsuccess = () => { db.close(); resolve(req.result || null); };
      req.onerror = () => { db.close(); resolve(null); };
    });
  } catch {
    return null;
  }
}

export async function clearSessionFromIdb() {
  try {
    const db = await openSessionDb();
    if (!db) return false;
    return await new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.objectStore(STORE_NAME).delete(SESSION_KEY);
      tx.oncomplete = () => { db.close(); resolve(true); };
      tx.onerror = () => { db.close(); resolve(false); };
    });
  } catch {
    return false;
  }
}
