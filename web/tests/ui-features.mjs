import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  clamp,
  computePageImageGeometry,
  dataUrlToUint8Array,
  parseHexColorRgb01,
  formatPageNumberText,
  formatFileSize,
  parsePageRange
} from '../js/math-utils.js';
import { wrapTextLines } from '../js/text-layout.js';
import { filterPaletteItems, scorePaletteItem } from '../js/command-palette.js';
import { CORE_SHORTCUTS, isTypingInInput, ShortcutManager } from '../js/shortcuts.js';
import { computeSettingsDiff } from '../js/settings-ui.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { state, DEFAULT_SETTINGS, PageItem, getPageDimensions } = await import('../js/state.js');
const { serializeSessionPages, deserializeSessionPages } = await import('../js/session-store.js');

// 1. math-utils.js checks
assert.equal(clamp(15, 0, 10), 10);
assert.equal(clamp(-3, 0, 10), 0);

// Rotated + cropped image geometry must swap draw dimensions cleanly
const geom = computePageImageGeometry(1000, 500, 600, 800, {
  imageRotation: 90,
  imageCrop: [0.25, 0.0, 0.75, 1.0], // cropped source is 500 x 500
  imageScale: 1.0
});
assert.equal(geom.sw, 500);
assert.equal(geom.sh, 500);
assert.equal(geom.isSwapped, true);
assert.equal(geom.dispW, 600);
assert.equal(geom.dispH, 600);

// Non-square crop + 90deg rotation: 1000x400 cropped to [0, 0, 0.5, 1] => 500x400 -> rotated 90 => 400x500
const geom2 = computePageImageGeometry(1000, 400, 400, 500, {
  imageRotation: 90,
  imageCrop: [0, 0, 0.5, 1]
});
assert.equal(geom2.effW, 400);
assert.equal(geom2.effH, 500);
assert.equal(geom2.dispW, 400);
assert.equal(geom2.dispH, 500);
assert.equal(geom2.drawW, 500);
assert.equal(geom2.drawH, 400);

const b64Bytes = dataUrlToUint8Array('data:text/plain;base64,' + Buffer.from('Nautilus').toString('base64'));
assert.equal(Buffer.from(b64Bytes).toString('utf8'), 'Nautilus');

const rgb = parseHexColorRgb01('#ff8000');
assert(Math.abs(rgb.r - 1) < 0.01);
assert(Math.abs(rgb.g - 128 / 255) < 0.01);
assert.equal(rgb.b, 0);

assert.equal(formatPageNumberText(2, 5, 'page_x_of_y'), 'Page 2 of 5');
assert.equal(formatPageNumberText(2, 5, 'dashes'), '— 2 —');
assert.equal(formatFileSize(1536), '1.5 KB');

// 2. text-layout.js galloping optimizer check
let measureCalls = 0;
const monoMeasure = (str) => {
  measureCalls++;
  return str.length * 10;
};
const longWrapped = wrapTextLines('A'.repeat(20000), 500, monoMeasure);
assert.equal(longWrapped.length, 400);
assert(longWrapped.every(line => line.length === 50));
assert(measureCalls < 6000, `Expected linear O(N) measure calls (<6000), got ${measureCalls}`);

const spaced = wrapTextLines('Hello world from Paper Nautilus report builder', 130, monoMeasure);
assert.deepEqual(spaced, ['Hello world ', 'from Paper ', 'Nautilus ', 'report ', 'builder']);

// 3. command-palette.js checks
const items = [
  { id: '1', category: 'Actions', label: 'Rotate Page +90°', subtitle: 'Turn image' },
  { id: '2', category: 'Pages', label: 'Page 1: Quarterly_Cover.png', subtitle: 'IMAGE · Portrait' },
  { id: '3', category: 'Recent', label: 'Shrink / Compress PDF', subtitle: 'Recent action' }
];
assert(scorePaletteItem(items[0], 'rot') > scorePaletteItem(items[1], 'rot'));
assert.equal(filterPaletteItems(items, 'quarterly').length, 1);
assert.equal(filterPaletteItems(items, 'compress').length, 1);
assert.equal(filterPaletteItems(items, 'nonexistent_xyz').length, 0);

// 4. shortcuts.js checks (10 core shortcuts + input guard)
assert.equal(CORE_SHORTCUTS.length, 10);
assert.equal(isTypingInInput({ tagName: 'INPUT', type: 'text' }), true);
assert.equal(isTypingInInput({ tagName: 'INPUT', type: 'search' }), true);
assert.equal(isTypingInInput({ tagName: 'INPUT', type: 'number' }), true);
assert.equal(isTypingInInput({ tagName: 'TEXTAREA' }), true);
assert.equal(isTypingInInput({ tagName: 'SELECT' }), true);
assert.equal(isTypingInInput({ tagName: 'DIV', isContentEditable: true }), true);
assert.equal(isTypingInInput({ tagName: 'BUTTON' }), false);
assert.equal(isTypingInInput({ tagName: 'INPUT', type: 'checkbox' }), false);

const triggered = [];
const mgr = new ShortcutManager({
  runAction: (id) => triggered.push(id),
  getOpenModalId: () => null,
  closeTopModal: () => triggered.push('close'),
  onToggleShortcuts: () => triggered.push('shortcuts')
});
// Should NOT fire 'r' while typing in an input
mgr.handleKeyDown({ key: 'r', target: { tagName: 'INPUT', type: 'text' }, preventDefault() {} });
assert.deepEqual(triggered, []);
// Should fire 'r' when focused on body
mgr.handleKeyDown({ key: 'r', target: { tagName: 'BODY' }, preventDefault() {} });
assert.deepEqual(triggered, ['rotate-90']);
// Should fire Cmd/Ctrl+K even inside input
mgr.handleKeyDown({ key: 'k', ctrlKey: true, target: { tagName: 'INPUT', type: 'text' }, preventDefault() {} });
assert.deepEqual(triggered, ['rotate-90', 'open-palette']);
// Should fire '?'
mgr.handleKeyDown({ key: '?', shiftKey: true, target: { tagName: 'BODY' }, preventDefault() {} });
assert.deepEqual(triggered, ['rotate-90', 'open-palette', 'shortcuts']);

// 5. settings-ui.js diff checks
const diffs = computeSettingsDiff(
  { ...DEFAULT_SETTINGS },
  { ...DEFAULT_SETTINGS, pageSize: 'Letter', pageNumbers: true }
);
assert.equal(diffs.length, 2);
assert.equal(diffs[0].label, 'Page Size');
assert.equal(diffs[1].label, 'Page Numbers');

// 6. state.js recents + resetSettings
for (let i = 0; i < 15; i++) {
  state.recordRecent({ id: `item:${i}`, type: 'action', label: `Action ${i}` });
}
assert.equal(state.recentItems.length, 12);
state.updateSettings({ pageSize: 'Letter' });
assert.equal(state.settings.pageSize, 'Letter');
state.resetSettings();
assert.equal(state.settings.pageSize, DEFAULT_SETTINGS.pageSize);

// 7. Web multi-step Undo / Redo + batch actions + Ctrl+Z / Ctrl+Y shortcuts
state.clearAll();
state._undoStack = [];
state._redoStack = [];
state.addPages([
  new PageItem({ id: 'u1', name: 'One.png', sourceType: 'image' }),
  new PageItem({ id: 'u2', name: 'Two.png', sourceType: 'image' })
]);
state.selectPage(0);
state.updateCurrentPage({ imageRotation: 90 });
state.rotateAllPages(180);
state.setAllOrientation(true);
state.movePage(0, 1);
state.removePage(1);
assert.equal(state.pages.length, 1);

assert.equal(state.undo(), true);
assert.equal(state.pages.length, 2);
assert.equal(state.pages[1].id, 'u1');

assert.equal(state.undo(), true);
assert.equal(state.pages[0].id, 'u1');

assert.equal(state.undo(), true);
assert.equal(state.pages.every(p => p.pageLandscape === false), true);

assert.equal(state.redo(), true);
assert.equal(state.pages.every(p => p.pageLandscape === true), true);

// ShortcutManager Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z with input guard
const histTriggered = [];
const histMgr = new ShortcutManager({
  runAction: (id) => histTriggered.push(id),
  getOpenModalId: () => null,
  closeTopModal: () => {},
  onToggleShortcuts: () => {}
});
histMgr.handleKeyDown({ key: 'z', ctrlKey: true, target: { tagName: 'INPUT', type: 'text' }, preventDefault() {} });
assert.deepEqual(histTriggered, []);
histMgr.handleKeyDown({ key: 'z', ctrlKey: true, target: { tagName: 'BODY' }, preventDefault() {} });
histMgr.handleKeyDown({ key: 'y', ctrlKey: true, target: { tagName: 'BODY' }, preventDefault() {} });
histMgr.handleKeyDown({ key: 'z', ctrlKey: true, shiftKey: true, target: { tagName: 'BODY' }, preventDefault() {} });
assert.deepEqual(histTriggered, ['undo', 'redo', 'redo']);

// 8. Phase 3: parsePageRange, custom page sizes, duplicate/blank/reverse/sort, settings diff
assert.deepEqual(parsePageRange('', 4), [0, 1, 2, 3]);
assert.deepEqual(parsePageRange('1, 4-3', 5), [0, 3, 2]);
assert.throws(() => parsePageRange('0', 4));
assert.throws(() => parsePageRange('9', 4));

assert.deepEqual(getPageDimensions(false, 'Legal'), [612.0, 1008.0]);
assert.deepEqual(getPageDimensions(true, 'A3'), [1190.55, 841.89]);
const fitDims = getPageDimensions(false, 'Fit', new PageItem({ sourceImage: { naturalWidth: 2000, naturalHeight: 1000 } }));
assert(Math.abs(fitDims[0] - 841.89) < 0.5 && Math.abs(fitDims[1] - 420.95) < 0.5);

state.clearAll();
state.addPages([
  new PageItem({ id: 's10', name: 'doc10.png', sourceType: 'image' }),
  new PageItem({ id: 's2', name: 'doc2.png', sourceType: 'image' })
]);
state.sortPagesByName();
assert.deepEqual(state.pages.map(p => p.name), ['doc2.png', 'doc10.png']);
state.duplicatePage(0);
assert.equal(state.pages.length, 3);
state.insertBlankPage(1, 'Divider');
assert.equal(state.pages[2].sourceType, 'blank');
state.reversePages();
assert.equal(state.pages[0].name, 'doc10.png');

const phase3Diffs = computeSettingsDiff(
  { ...DEFAULT_SETTINGS },
  { ...DEFAULT_SETTINGS, watermarkText: 'DRAFT', pdfTitle: 'Audit' }
);
assert.equal(phase3Diffs.length, 2);

// 9. Phase 4: session serialization round-trip, Alt+Up/Down reordering, no alert/confirm
const sessPages = [
  new PageItem({
    id: 'sp1',
    name: 'PageOne.png',
    sourceType: 'image',
    imageRotation: 90,
    imageScale: 1.5,
    imageCrop: [0.1, 0.1, 0.9, 0.9],
    sourceImage: { src: 'data:image/png;base64,AA==' }
  }),
  new PageItem({
    id: 'sp2',
    name: 'Note.txt',
    sourceType: 'text',
    textContent: 'Saved body',
    textHeader: 'Note.txt — Page 1'
  })
];
const payload = serializeSessionPages(sessPages, 1);
const restored = await deserializeSessionPages(payload, async (url) => ({ src: url, naturalWidth: 10, naturalHeight: 10 }));
assert.equal(restored.pages.length, 2);
assert.equal(restored.currentIndex, 1);
assert.equal(restored.pages[0].imageRotation, 90);
assert.deepEqual(restored.pages[0].imageCrop, [0.1, 0.1, 0.9, 0.9]);
assert.equal(restored.pages[1].textContent, 'Saved body');

const altTriggered = [];
const altMgr = new ShortcutManager({
  runAction: (id) => altTriggered.push(id),
  getOpenModalId: () => null,
  closeTopModal: () => {},
  onToggleShortcuts: () => {}
});
altMgr.handleKeyDown({ key: 'ArrowUp', altKey: true, target: { tagName: 'INPUT', type: 'text' }, preventDefault() {} });
assert.deepEqual(altTriggered, []);
altMgr.handleKeyDown({ key: 'ArrowUp', altKey: true, target: { tagName: 'BODY' }, preventDefault() {} });
altMgr.handleKeyDown({ key: 'ArrowDown', altKey: true, target: { tagName: 'BODY' }, preventDefault() {} });
assert.deepEqual(altTriggered, ['move-up', 'move-down']);

for (const jsFile of ['../js/app.js', '../js/three-viewer.js']) {
  const src = fs.readFileSync(new URL(jsFile, import.meta.url), 'utf8');
  assert(!/\b(alert|confirm)\(/.test(src), `${jsFile} should use non-blocking toast/confirmDialog instead of alert()/confirm()`);
}

console.log('PASS: math-utils, O(N) text-layout, command-palette, shortcuts input-guard, settings diff, and state recents.');
