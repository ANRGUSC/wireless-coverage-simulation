import { useEffect, useRef, useCallback, useState } from 'react';
import type { BuildingMaskData, CoverageParams, CoverageResult, WorkerOutMessage } from '../types/index.ts';

interface UseCoverageWorkerReturn {
  calculate: (baseStations: { px: number; py: number }[], params: CoverageParams) => void;
  result: CoverageResult | null;
  isCalculating: boolean;
  progress: { current: number; total: number } | null;
  isReady: boolean;
}

export function useCoverageWorker(maskData: BuildingMaskData | null): UseCoverageWorkerReturn {
  const workerRef = useRef<Worker | null>(null);
  const requestIdRef = useRef(0);
  const [result, setResult] = useState<CoverageResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const worker = new Worker(
      new URL('../workers/coverage.worker.ts', import.meta.url),
      { type: 'module' }
    );
    workerRef.current = worker;

    worker.onmessage = (e: MessageEvent<WorkerOutMessage>) => {
      const msg = e.data;
      if (msg.type === 'ready') {
        setIsReady(true);
      } else if (msg.type === 'progress') {
        if (msg.requestId === requestIdRef.current) {
          setProgress({ current: msg.current, total: msg.total });
        }
      } else if (msg.type === 'result') {
        if (msg.requestId === requestIdRef.current) {
          setResult({
            imageData: new Uint8ClampedArray(msg.imageData),
            renderWidth: msg.renderWidth,
            renderHeight: msg.renderHeight,
            coveragePercent: msg.coveragePercent,
            maxRange: msg.maxRange,
            bsColors: msg.bsColors,
          });
          setIsCalculating(false);
          setProgress(null);
        }
      }
    };

    return () => {
      worker.terminate();
    };
  }, []);

  useEffect(() => {
    if (workerRef.current && maskData) {
      const maskCopy = new Uint8Array(maskData.mask);
      workerRef.current.postMessage(
        { type: 'init', mask: maskCopy, width: maskData.width, height: maskData.height, outdoorCount: maskData.outdoorCount },
        [maskCopy.buffer]
      );
    }
  }, [maskData]);

  const calculate = useCallback((baseStations: { px: number; py: number }[], params: CoverageParams) => {
    if (!workerRef.current || !isReady) return;
    const requestId = ++requestIdRef.current;
    setIsCalculating(true);
    setProgress(null);
    workerRef.current.postMessage({
      type: 'calculate',
      requestId,
      baseStations,
      params,
      imgWidth: maskData?.width ?? 0,
      imgHeight: maskData?.height ?? 0,
    });
  }, [isReady, maskData]);

  return { calculate, result, isCalculating, progress, isReady };
}
