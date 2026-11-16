# Faceless Content

This source snapshot contains two independent static sites and the local production inventory tool.

| Component | Source | Local verification |
| --- | --- | --- |
| Flux Clip Kit | `sites/flux-clip-kit/dist` | Serve the directory with `python3 -m http.server --directory sites/flux-clip-kit/dist`. |
| LaunchPlan and SpecFlow | `sites/distribution-studio/dist` | Run `npm --prefix sites/distribution-studio run check` and `npm --prefix sites/distribution-studio run dev`. |
| Production memory | `production-memory` | Run `python3 -m unittest discover -s production-memory/tests -v`. |

Run the inventory tool with `python3 production-memory/scripts/library.py --workspace /path/to/video-workspace stats`. See the [CRM interchange contract](production-memory/CRM-CONTRACT.md) for validating and importing a CRM event export. The inventory uses a local database. The static sites do not read CRM records; live integration requires an authenticated data source.

Each site's `dist` directory is its deployment root. Media masters, recordings, database exports, private production notes and deployment credentials belong outside this source snapshot.
