# Faceless Content

This source snapshot contains the Flux Clip Kit and the local production inventory tool.

| Component | Source | Local verification |
| --- | --- | --- |
| Flux Clip Kit | `sites/flux-clip-kit/dist` | Serve the directory with `python3 -m http.server --directory sites/flux-clip-kit/dist`. |
| Production memory | `production-memory` | Run `python3 -m unittest discover -s production-memory/tests -v`. |

Run the inventory tool with `python3 production-memory/scripts/library.py --workspace /path/to/video-workspace stats`. See the [CRM interchange contract](production-memory/CRM-CONTRACT.md) for validating and importing a CRM event export. The inventory uses a local database. The CRM interchange tool accepts local event exports.

The Flux Clip Kit serves from its `dist` directory. Media masters, recordings, database exports, private production notes and deployment credentials belong outside this source snapshot.
