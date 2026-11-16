/**
 * Line-wrapping utility using estimated width + exponential galloping search.
 * Runs in O(N) total measured characters instead of O(N^2) on long lines.
 */
export function wrapTextLines(text, maxWidth, measure) {
  const lines = [];
  const paragraphs = String(text).replaceAll('\t', '    ').split(/\r?\n/);

  for (const input of paragraphs) {
    const points = Array.from(input);
    const len = points.length;
    if (len === 0) {
      lines.push('');
      continue;
    }

    let pos = 0;
    const fits = (count) => measure(points.slice(pos, pos + count).join('')) <= maxWidth;

    while (pos < len) {
      const rem = len - pos;

      if (rem <= 128 && fits(rem)) {
        lines.push(points.slice(pos).join(''));
        break;
      }

      const probeLen = Math.min(rem, 64);
      const probeWidth = measure(points.slice(pos, pos + probeLen).join(''));

      if (probeLen === rem && probeWidth <= maxWidth) {
        lines.push(points.slice(pos).join(''));
        break;
      }

      let est = probeWidth > 0
        ? Math.max(1, Math.min(rem, Math.floor((maxWidth / probeWidth) * probeLen)))
        : Math.min(rem, 64);

      let lo = 1;
      let hi = rem;

      if (fits(est)) {
        lo = est;
        if (lo === rem) {
          lines.push(points.slice(pos).join(''));
          break;
        }
        let step = 4;
        let foundUpper = false;
        while (lo < rem) {
          const next = Math.min(rem, lo + step);
          if (fits(next)) {
            lo = next;
            if (lo === rem) break;
            step *= 2;
          } else {
            hi = next - 1;
            foundUpper = true;
            break;
          }
        }
        if (!foundUpper && lo === rem) {
          lines.push(points.slice(pos).join(''));
          break;
        }
      } else {
        hi = est - 1;
        let step = 4;
        let foundLower = false;
        while (hi > 1) {
          const prev = Math.max(1, hi - step);
          if (!fits(prev)) {
            hi = prev - 1;
            step *= 2;
          } else {
            lo = prev;
            foundLower = true;
            break;
          }
        }
        if (!foundLower && hi <= 1) {
          lo = 1;
          hi = 1;
        }
      }

      let fit = lo;
      while (lo <= hi) {
        const mid = (lo + hi) >> 1;
        if (fits(mid)) {
          fit = mid;
          lo = mid + 1;
        } else {
          hi = mid - 1;
        }
      }

      // Break on last space within fitted range when not at the end of paragraph
      if (pos + fit < len) {
        for (let i = pos + fit - 1; i > pos; i--) {
          if (points[i] === ' ') {
            fit = i - pos + 1;
            break;
          }
        }
      }

      lines.push(points.slice(pos, pos + fit).join(''));
      pos += fit;
    }
  }

  return lines;
}
