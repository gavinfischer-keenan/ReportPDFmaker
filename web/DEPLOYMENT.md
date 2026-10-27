# Paper Nautilus / PDF Maker Web Edition

Static browser application. No application server, Python, Node runtime or database is needed by visitors or the hosting server.

Production: https://pdfmaker.11mosswood.us/app/ with the TripoFisch introduction at the hostname root. Relative asset URLs also support standalone hosting at a domain root or any trailing-slash subdirectory.

Publish only index.html, css/, js/, vendor/, assets/ and LICENSE.txt. Do not serve node_modules/, tests/, package manifests or Docker/configuration files. Use HTTPS, correct JavaScript MIME types, a trailing slash, and revalidation for non-fingerprinted assets.

The current deployment uses the existing public Caddy/Cloudflare Tunnel stack, serving a versioned static release. No Docker process is necessary. Docker/Nginx remains an alternative using the included files.

Security: reject POST/PUT/DELETE; restrict scripts, workers and connections to the same origin (plus blob/data as required for local rendering); disable framing. Do not enable unsafe-eval. PDF.js is configured with isEvalSupported:false, matching Mozilla's GHSA-wgrm-67xf-hhpq workaround. Standard fonts and CMaps are vendored locally with their licenses.

Files are processed locally. Ordinary static requests still reach the website. DOCX is text extraction, not Word layout preservation; legacy DOC is unsupported. Compression rasterizes pages, losing vector text/links; if rasterization increases size, the original is retained. Large documents may require substantial browser memory. Optional 3D preview requires WebGL; PDF tools initialize without it.

Developer checks only: Node 22+ and `npm ci && npm test` inside web/. This installs test-only canvas/ZIP tooling. Tests exercise filename escaping, native PDF merge/reorder/page numbers, actual canvas image/text/DOCX/PDF import and export, imported-page orientation, long-line pagination, compression fallback and optional WebGL initialization. Browser file selection/save permissions are a separate manual check.

Repository fixes: imported PDF bytes are copied before PDF.js transfer; image rotation/orientation select the proper export path; text wraps before pagination; filenames are escaped; WebGL initializes only on request. The source main/ desktop application was not changed.
