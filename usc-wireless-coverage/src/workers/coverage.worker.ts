import { calculateCoverage } from './coverageEngine.ts';
import type { WorkerInMessage, WorkerOutMessage } from '../types/index.ts';

let storedMask: Uint8Array | null = null;
let storedWidth = 0;
let storedHeight = 0;
let storedOutdoorCount = 0;

self.onmessage = (e: MessageEvent<WorkerInMessage>) => {
  const msg = e.data;

  if (msg.type === 'init') {
    storedMask = msg.mask;
    storedWidth = msg.width;
    storedHeight = msg.height;
    storedOutdoorCount = msg.outdoorCount;
    const response: WorkerOutMessage = { type: 'ready' };
    self.postMessage(response);
    return;
  }

  if (msg.type === 'calculate') {
    if (!storedMask) return;

    const { requestId, baseStations, params } = msg;

    const result = calculateCoverage({
      baseStations,
      txPower: params.txPower,
      noise: params.noise,
      snrThreshold: params.snrThreshold,
      shadowStd: params.shadowStd,
      freqHz: params.freqHz,
      mask: storedMask,
      imgWidth: storedWidth,
      imgHeight: storedHeight,
      outdoorCount: storedOutdoorCount,
      onProgress: (current, total) => {
        const progress: WorkerOutMessage = { type: 'progress', requestId, current, total };
        self.postMessage(progress);
      },
    });

    const response: WorkerOutMessage = {
      type: 'result',
      requestId,
      imageData: result.imageData,
      renderWidth: result.renderWidth,
      renderHeight: result.renderHeight,
      coveragePercent: result.coveragePercent,
      maxRange: result.maxRange,
      bsColors: result.bsColors,
    };
    // Small image (~300x220) — no need for Transferable, just copy
    self.postMessage(response);
  }
};
