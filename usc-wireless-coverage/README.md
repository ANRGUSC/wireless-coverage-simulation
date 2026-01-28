# USC Wireless Coverage — Web Application

An interactive Progressive Web App for simulating wireless coverage on the USC campus. This is a browser-based reimplementation of the Python `interactive_coverage_tool.py`.

**Live demo:** [usc-wireless-coverage.vercel.app](https://usc-wireless-coverage.vercel.app)

## Features

- **Place base stations** by clicking on outdoor areas of the campus map
- **Drag to reposition** base stations, **right-click to delete** them
- **Adjust RF parameters** (TX power, noise floor, SNR threshold, shadowing std dev, frequency) via the sidebar
- **Real-time coverage visualization** with color-coded coverage areas per base station
- **Statistics display** showing base station count, coverage percentage, and max range
- **Export** the coverage map as a PNG image
- **Offline support** — installable as a PWA with service worker caching
- **Coordinate readout** on mouse hover (meters)

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | React 18 + TypeScript |
| Build tool | Vite |
| Rendering | HTML5 Canvas 2D with `ImageData` pixel manipulation |
| Computation | Web Worker (all physics runs off the main thread) |
| PWA | vite-plugin-pwa with Workbox |
| Styling | CSS Modules |
| State management | React `useReducer` |

## Architecture

- **Coverage engine** (`src/workers/coverageEngine.ts`) — Implements free-space path loss (Friis), log-normal shadowing with a seedable PRNG, and radial ray-cast line-of-sight checking. Computation runs at 1/8 resolution (~300x220 pixels) for performance, with CSS canvas scaling handling the upscale to display size.
- **Web Worker** (`src/workers/coverage.worker.ts`) — Runs the coverage engine off the main thread so the UI stays responsive. Uses a request-ID pattern to discard stale results during rapid interaction.
- **Seedable PRNG** (`src/workers/prng.ts`) — Mulberry32 uniform generator with Box-Muller polar method for deterministic Gaussian shadowing (seed=42).
- **Canvas interaction** (`src/components/MapCanvas/MapCanvas.tsx`) — Handles click-to-place, drag-to-move, and right-click-to-delete with coordinate transforms between display and image space.
- **Debounced recalculation** — 150ms debounce coalesces rapid parameter or base station changes before triggering the worker.

## Development

```bash
npm install
npm run dev
```

## Build & Deploy

```bash
npm run build
npx vercel --prod
```

## Physics Model

- **Path loss:** FSPL = 20 log10(4 pi d / lambda)
- **Max range:** (lambda / 4 pi) * 10^(maxPathLoss / 20), where maxPathLoss = txPower - noise - snrThreshold + 3 * shadowStd
- **Shadowing:** Gaussian N(0, shadowStd), deterministic via seed=42
- **LOS:** Radial ray-cast from each base station (720 rays), building mask blocks propagation
- **Map scale:** 640m x 430m
