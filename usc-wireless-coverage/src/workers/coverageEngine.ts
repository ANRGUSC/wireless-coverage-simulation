import { SeededRNG } from './prng.ts';
import { getBsColors } from '../utils/colors.ts';

const MAP_WIDTH_M = 640.0;
const MAP_HEIGHT_M = 430.0;

// Render at 1/8 resolution (~300x220). Canvas CSS scaling handles upscale.
const COMPUTE_SCALE = 8;
const NUM_RAYS = 720;

export function calculateMaxRange(
  txPower: number, noise: number, snrThreshold: number, shadowStd: number, freqHz: number
): number {
  const c = 3e8;
  const wavelength = c / freqHz;
  const maxPathLoss = txPower - noise - snrThreshold + 3 * shadowStd;
  return (wavelength / (4 * Math.PI)) * Math.pow(10, maxPathLoss / 20);
}

export interface CalculateInput {
  baseStations: { px: number; py: number }[];
  txPower: number;
  noise: number;
  snrThreshold: number;
  shadowStd: number;
  freqHz: number;
  mask: Uint8Array;
  imgWidth: number;
  imgHeight: number;
  outdoorCount: number;
  onProgress?: (current: number, total: number) => void;
}

export interface CalculateOutput {
  imageData: Uint8ClampedArray;
  renderWidth: number;
  renderHeight: number;
  coveragePercent: number;
  maxRange: number;
  bsColors: [number, number, number][];
}

function downscaleMask(mask: Uint8Array, fullW: number, fullH: number, scale: number) {
  const smallW = Math.ceil(fullW / scale);
  const smallH = Math.ceil(fullH / scale);
  const smallMask = new Uint8Array(smallW * smallH);
  let smallOutdoorCount = 0;
  for (let sy = 0; sy < smallH; sy++) {
    const fy = Math.min(sy * scale + (scale >> 1), fullH - 1);
    for (let sx = 0; sx < smallW; sx++) {
      const fx = Math.min(sx * scale + (scale >> 1), fullW - 1);
      const val = mask[fy * fullW + fx];
      smallMask[sy * smallW + sx] = val;
      if (val === 0) smallOutdoorCount++;
    }
  }
  return { smallMask, smallW, smallH, smallOutdoorCount };
}

function buildVisibilityMap(
  bsPx: number, bsPy: number, maxRangePx: number,
  mask: Uint8Array, w: number, h: number,
): Float32Array {
  const visDistSq = new Float32Array(NUM_RAYS);
  const twoPi = 2 * Math.PI;
  const maxR = Math.ceil(maxRangePx);
  for (let ri = 0; ri < NUM_RAYS; ri++) {
    const angle = (ri / NUM_RAYS) * twoPi;
    const cosA = Math.cos(angle);
    const sinA = Math.sin(angle);
    let maxVisDist = 0;
    for (let step = 1; step <= maxR; step++) {
      const px = (bsPx + cosA * step + 0.5) | 0;
      const py = (bsPy + sinA * step + 0.5) | 0;
      if (px < 0 || px >= w || py < 0 || py >= h) break;
      if (mask[py * w + px] === 1) break;
      maxVisDist = step;
    }
    visDistSq[ri] = maxVisDist * maxVisDist;
  }
  return visDistSq;
}

const INV_TWO_PI = 1 / (2 * Math.PI);

export function calculateCoverage(input: CalculateInput): CalculateOutput {
  const { baseStations, txPower, noise, snrThreshold, shadowStd, freqHz,
          mask, imgWidth, imgHeight, outdoorCount, onProgress } = input;
  const numBs = baseStations.length;
  const maxRange = calculateMaxRange(txPower, noise, snrThreshold, shadowStd, freqHz);

  // Downscale
  const { smallMask, smallW, smallH, smallOutdoorCount } = downscaleMask(mask, imgWidth, imgHeight, COMPUTE_SCALE);
  const smallTotal = smallW * smallH;

  // Build small-res RGBA image (white outdoor, gray buildings)
  const imageData = new Uint8ClampedArray(smallTotal * 4);
  for (let i = 0; i < smallTotal; i++) {
    const i4 = i << 2;
    if (smallMask[i] === 1) {
      imageData[i4] = 77; imageData[i4 + 1] = 77; imageData[i4 + 2] = 77;
    } else {
      imageData[i4] = 255; imageData[i4 + 1] = 255; imageData[i4 + 2] = 255;
    }
    imageData[i4 + 3] = 255;
  }

  if (numBs === 0) {
    return { imageData, renderWidth: smallW, renderHeight: smallH, coveragePercent: 0, maxRange, bsColors: [] };
  }

  // Precompute constants
  const mPerPxX = MAP_WIDTH_M / smallW;
  const mPerPxY = MAP_HEIGHT_M / smallH;
  const wavelength = 3e8 / freqHz;
  const fsplConst = 20 * Math.log10((4 * Math.PI) / wavelength);
  const maxRangeSq = maxRange * maxRange;
  const maxRangeSpxX = maxRange / mPerPxX;
  const maxRangeSpxY = maxRange / mPerPxY;
  const maxRangeSpx = Math.max(maxRangeSpxX, maxRangeSpxY);

  // BS positions in small-grid coords and meters
  const bsSmallPx = new Int32Array(numBs);
  const bsSmallPy = new Int32Array(numBs);
  const bsXm = new Float64Array(numBs);
  const bsYm = new Float64Array(numBs);
  for (let i = 0; i < numBs; i++) {
    bsSmallPx[i] = Math.max(0, Math.min(smallW - 1, Math.round(baseStations[i].px / COMPUTE_SCALE)));
    bsSmallPy[i] = Math.max(0, Math.min(smallH - 1, Math.round(baseStations[i].py / COMPUTE_SCALE)));
    bsXm[i] = (baseStations[i].px / imgWidth) * MAP_WIDTH_M;
    bsYm[i] = (baseStations[i].py / imgHeight) * MAP_HEIGHT_M;
  }

  // Shadowing maps (small res)
  const rng = new SeededRNG(42);
  const shadowingMaps: Float32Array[] = [];
  for (let i = 0; i < numBs; i++) {
    shadowingMaps.push(rng.normalArray(smallTotal, 0, shadowStd));
  }

  // Coverage masks
  const coverageMasks: Uint8Array[] = [];
  for (let i = 0; i < numBs; i++) {
    coverageMasks.push(new Uint8Array(smallTotal));
  }

  // Main computation
  for (let bsIdx = 0; bsIdx < numBs; bsIdx++) {
    const bxm = bsXm[bsIdx];
    const bym = bsYm[bsIdx];
    const bspx = bsSmallPx[bsIdx];
    const bspy = bsSmallPy[bsIdx];

    const visDist2 = buildVisibilityMap(bspx, bspy, maxRangeSpx, smallMask, smallW, smallH);

    const minSx = Math.max(0, (bspx - maxRangeSpxX) | 0);
    const maxSx = Math.min(smallW - 1, Math.ceil(bspx + maxRangeSpxX));
    const minSy = Math.max(0, (bspy - maxRangeSpxY) | 0);
    const maxSy = Math.min(smallH - 1, Math.ceil(bspy + maxRangeSpxY));

    const shadowMap = shadowingMaps[bsIdx];
    const covMask = coverageMasks[bsIdx];

    for (let sy = minSy; sy <= maxSy; sy++) {
      const ptYm = (sy + 0.5) * mPerPxY;
      const dyM = ptYm - bym;
      const dyMSq = dyM * dyM;
      const dyPx = sy - bspy;
      const rowOff = sy * smallW;

      for (let sx = minSx; sx <= maxSx; sx++) {
        const idx = rowOff + sx;
        if (smallMask[idx] === 1) continue;

        const dxM = (sx + 0.5) * mPerPxX - bxm;
        const distSq = dxM * dxM + dyMSq;
        if (distSq > maxRangeSq) continue;

        let distance = Math.sqrt(distSq);
        if (distance < 1.0) distance = 1.0;

        const snr = txPower - (fsplConst + 20 * Math.log10(distance)) - shadowMap[idx] - noise;
        if (snr < snrThreshold) continue;

        // O(1) LOS lookup via precomputed visibility map
        const dxPx = sx - bspx;
        const pixDistSq = dxPx * dxPx + dyPx * dyPx;
        let angle = Math.atan2(dyPx, dxPx);
        if (angle < 0) angle += 6.283185307179586;
        let rayIdx = (angle * INV_TWO_PI * NUM_RAYS + 0.5) | 0;
        if (rayIdx >= NUM_RAYS) rayIdx = 0;

        if (pixDistSq <= visDist2[rayIdx]) {
          covMask[idx] = 1;
        }
      }
    }

    if (onProgress) onProgress(bsIdx + 1, numBs);
  }

  // Colors
  const colorsFloat = getBsColors(numBs);
  const bsColors: [number, number, number][] = colorsFloat.map(cf =>
    [Math.round(cf[0] * 255), Math.round(cf[1] * 255), Math.round(cf[2] * 255)]
  );

  // Render directly into small-res image
  const alpha = 0.35;
  const oneMinusAlpha = 0.65;
  let totalCovered = 0;

  const colR = new Float32Array(numBs);
  const colG = new Float32Array(numBs);
  const colB = new Float32Array(numBs);
  for (let i = 0; i < numBs; i++) {
    colR[i] = alpha * colorsFloat[i][0];
    colG[i] = alpha * colorsFloat[i][1];
    colB[i] = alpha * colorsFloat[i][2];
  }

  for (let i = 0; i < smallTotal; i++) {
    if (smallMask[i] === 1) continue;
    let covered = false;
    let r = 1.0, g = 1.0, b = 1.0;
    for (let bsIdx = 0; bsIdx < numBs; bsIdx++) {
      if (coverageMasks[bsIdx][i] === 1) {
        covered = true;
        r = colR[bsIdx] + oneMinusAlpha * r;
        g = colG[bsIdx] + oneMinusAlpha * g;
        b = colB[bsIdx] + oneMinusAlpha * b;
      }
    }
    if (covered) {
      totalCovered++;
      const i4 = i << 2;
      imageData[i4]     = (r * 255 + 0.5) | 0;
      imageData[i4 + 1] = (g * 255 + 0.5) | 0;
      imageData[i4 + 2] = (b * 255 + 0.5) | 0;
    }
  }

  const coveragePercent = smallOutdoorCount > 0 ? (100 * totalCovered / smallOutdoorCount) : 0;

  return { imageData, renderWidth: smallW, renderHeight: smallH, coveragePercent, maxRange, bsColors };
}
