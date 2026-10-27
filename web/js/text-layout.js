export function wrapTextLines(text, maxWidth, measure) {
  const lines = [];
  for (const input of String(text).replaceAll('\t', '    ').split(/\r?\n/)) {
    let points = Array.from(input);
    while (points.length && measure(points.join('')) > maxWidth) {
      let lo = 1, hi = points.length, fit = 1;
      while (lo <= hi) {
        const mid = Math.floor((lo + hi) / 2);
        if (measure(points.slice(0, mid).join('')) <= maxWidth) {fit = mid; lo = mid + 1;} else hi = mid - 1;
      }
      const space = points.slice(0, fit).lastIndexOf(' ');
      if (space > 0) fit = space + 1;
      lines.push(points.slice(0, fit).join(''));
      points = points.slice(fit);
    }
    lines.push(points.join(''));
  }
  return lines;
}
