# Paper Nautilus / PDF Maker Web Edition

Static browser application. No application server, Python, Node runtime or database is needed by visitors or the hosting server.

Production: https://pdfmaker.11mosswood.us/app/ with the TripoFisch introduction at the hostname root. Relative asset URLs also support standalone hosting at a domain root or any trailing-slash subdirectory.

Publish only `index.html`, `css/`, `js/`, `vendor/`, `assets/` and `LICENSE.txt`. Do not serve `server.py`, `node_modules/`, `tests/`, package manifests or Docker/configuration files. Use HTTPS, correct JavaScript MIME types, a trailing slash, and revalidation for non-fingerprinted assets.

The current deployment uses the existing public Caddy/Cloudflare Tunnel stack, serving a versioned static release. No Docker process is necessary. Docker/Nginx remains an alternative using the included `Dockerfile`, `docker-compose.yml`, and `nginx.conf`. For quick local manual testing, run `python server.py [port]` (defaults to `http://localhost:8080`).

Security: reject POST/PUT/DELETE; restrict scripts, workers and connections to the same origin (plus blob/data as required for local rendering); disable framing. Do not enable `unsafe-eval`. PDF.js is configured with `isEvalSupported: false`, matching Mozilla's GHSA-wgrm-67xf-hhpq workaround. Standard fonts and CMaps are vendored locally with their licenses (`vendor/THIRD-PARTY-NOTICES.txt`).

Files are processed locally. Workspace recovery uses browser IndexedDB (`paper_nautilus_session`) and preferences use `localStorage`. DOCX is text extraction via Mammoth.js, not Word layout preservation; legacy DOC is unsupported. Unedited TXT/DOCX pages export as native vector text (falling back to raster for non-WinAnsi characters). Compression rasterizes pages via PDF.js, removing searchable text and links; if rasterization increases size, the original is retained. Optional 3D preview requires WebGL; PDF tools initialize without it.

Developer checks only: Node 22+ and `npm ci && npm test` inside `web/`. This installs test-only canvas/ZIP tooling and runs three suites:
- `tests/security.mjs` — HTML filename escaping, synthetic PDF merge/reorder/page-number build, and disabled PDF.js `eval`
- `tests/browser-core.mjs` — real canvas image/text/DOCX/PDF import and export, native vector TXT/DOCX export + Unicode fallback, custom `Fit` page size, page-range export, watermarks/headers/footers/metadata, imported-page orientation, long-line pagination, compression fallback, and optional WebGL initialization
- `tests/ui-features.mjs` — `math-utils.js` geometry/color/range/formatting helpers, O(N) text wrapping (`text-layout.js`), command-palette scoring/filtering, keyboard shortcuts (`Ctrl+Z`/`Ctrl+Y`/`Alt+↑/↓`) & input-focus guards, grouped settings diff computation, `state.js` multi-step undo/redo/duplicate/blank/reverse/sort/recents, `session-store.js` round-trip serialization, and zero `alert()`/`confirm()` usage

Browser file selection/save permissions, IndexedDB persistence, modal focus trapping, and visual mobile/tablet responsiveness are separate manual checks.

Repository parity: the Web Edition and the Windows desktop application (`pdf_maker/`) both include a `Ctrl+K` Command Palette, `?` Keyboard Shortcuts overlay with input guards, multi-step `Ctrl+Z`/`Ctrl+Y` undo/redo, `Resize`/`Crop` modes, `Duplicate`/`Blank`/`Reverse`/`Sort` actions, custom page sizes (`A4`/`Letter`/`Legal`/`A3`/`A5`/`Fit`), page-range export, live watermarks & headers/footers, PDF metadata, grouped Settings with change-diff confirmation, and O(N)/geometry/layout optimizations.
