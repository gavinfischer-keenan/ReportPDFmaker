import assert from 'node:assert/strict';

import {
  clamp,
  computePageImageGeometry,
  dataUrlToUint8Array,
  parseHexColorRgb01,
  formatPageNumberText,
  formatFileSize
} from '../js/math-utils.js';
import { wrapTextLines } from '../js/text-layout.js';
import { filterPaletteItems, scorePaletteItem } from '../js/command-palette.js';
import { CORE_SHORTCUTS, isTypingInInput, ShortcutManager } from '../js/shortcuts.js';
import { computeSettingsDiff } from '../js/settings-ui.js';

globalThis.localStorage = { getItem: () => null, setItem: () => {} };
const { state, DEFAULT_SETTINGS } = await import('../js/state.js');

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

console.log('PASS: math-utils, O(N) text-layout, command-palette, shortcuts input-guard, settings diff, and state recents.');
