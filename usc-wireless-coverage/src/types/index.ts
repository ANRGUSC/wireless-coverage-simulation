export interface BaseStation {
  id: number;
  px: number; // pixel x on the FULL-RES image
  py: number; // pixel y on the FULL-RES image
}

export interface CoverageParams {
  txPower: number;      // dBm
  noise: number;        // dBm
  snrThreshold: number; // dB
  shadowStd: number;    // dB
  freqHz: number;       // Hz
}

export interface CoverageResult {
  imageData: Uint8ClampedArray; // RGBA at renderWidth x renderHeight
  renderWidth: number;
  renderHeight: number;
  coveragePercent: number;
  maxRange: number;
  bsColors: [number, number, number][]; // RGB 0-255
}

export interface BuildingMaskData {
  mask: Uint8Array;          // 1=building, 0=outdoor
  width: number;
  height: number;
  outdoorCount: number;
}

export type WorkerInMessage =
  | { type: 'init'; mask: Uint8Array; width: number; height: number; outdoorCount: number }
  | { type: 'calculate'; requestId: number; baseStations: { px: number; py: number }[]; params: CoverageParams; imgWidth: number; imgHeight: number }

export type WorkerOutMessage =
  | { type: 'ready' }
  | { type: 'progress'; requestId: number; current: number; total: number }
  | { type: 'result'; requestId: number; imageData: Uint8ClampedArray; renderWidth: number; renderHeight: number; coveragePercent: number; maxRange: number; bsColors: [number, number, number][] }
