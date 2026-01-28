import { useRef, useEffect, useCallback, useState } from 'react';
import type { BaseStation, CoverageResult, BuildingMaskData } from '../../types/index.ts';
import styles from './MapCanvas.module.css';

const BS_RADIUS = 7;
const HIT_RADIUS = 12;

interface MapCanvasProps {
  maskData: BuildingMaskData | null;
  mapImage: HTMLImageElement | null;
  baseStations: BaseStation[];
  coverageResult: CoverageResult | null;
  isCalculating: boolean;
  onAddBS: (px: number, py: number) => void;
  onMoveBS: (id: number, px: number, py: number) => void;
  onDeleteBS: (id: number) => void;
  statusMessage: string;
}

export default function MapCanvas({
  maskData, mapImage, baseStations, coverageResult,
  isCalculating, onAddBS, onMoveBS, onDeleteBS, statusMessage,
}: MapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState<{ id: number; offsetX: number; offsetY: number } | null>(null);
  const [displaySize, setDisplaySize] = useState({ w: 800, h: 600 });
  const [mousePos, setMousePos] = useState<{ x: number; y: number } | null>(null);

  const imgWidth = maskData?.width ?? 1;
  const imgHeight = maskData?.height ?? 1;

  // Fit canvas to container
  useEffect(() => {
    function resize() {
      const container = containerRef.current;
      if (!container || !maskData) return;
      const cw = container.clientWidth - 20;
      const ch = container.clientHeight - 40;
      const aspect = imgWidth / imgHeight;
      let w: number, h: number;
      if (cw / ch > aspect) {
        h = ch; w = h * aspect;
      } else {
        w = cw; h = w / aspect;
      }
      setDisplaySize({ w: Math.floor(w), h: Math.floor(h) });
    }
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [maskData, imgWidth, imgHeight]);

  // Render canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !maskData) return;

    // Set canvas to display size for crisp rendering
    canvas.width = displaySize.w;
    canvas.height = displaySize.h;
    const ctx = canvas.getContext('2d')!;
    ctx.imageSmoothingEnabled = true;

    if (coverageResult) {
      // Draw coverage image (small res) scaled up to display size
      const srcW = coverageResult.renderWidth;
      const srcH = coverageResult.renderHeight;
      const clampedArr = new Uint8ClampedArray(srcW * srcH * 4);
      clampedArr.set(coverageResult.imageData);
      const imgData = new ImageData(clampedArr, srcW, srcH);
      // Use offscreen canvas to scale
      const offscreen = document.createElement('canvas');
      offscreen.width = srcW;
      offscreen.height = srcH;
      offscreen.getContext('2d')!.putImageData(imgData, 0, 0);
      ctx.drawImage(offscreen, 0, 0, displaySize.w, displaySize.h);
    } else if (mapImage) {
      ctx.drawImage(mapImage, 0, 0, displaySize.w, displaySize.h);
    }

    // Draw base station markers (convert from full-res coords to display coords)
    const scaleX = displaySize.w / imgWidth;
    const scaleY = displaySize.h / imgHeight;
    const colors = coverageResult?.bsColors ?? [];
    baseStations.forEach((bs, i) => {
      const [r, g, b] = colors[i] ?? [255, 0, 0];
      const dx = bs.px * scaleX;
      const dy = bs.py * scaleY;
      ctx.beginPath();
      ctx.arc(dx, dy, BS_RADIUS, 0, 2 * Math.PI);
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fill();
      ctx.strokeStyle = '#000';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
  }, [maskData, mapImage, coverageResult, baseStations, imgWidth, imgHeight, displaySize]);

  // Convert mouse event to full-res image coordinates
  const toImageCoords = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((e.clientX - rect.left) / rect.width) * imgWidth,
      y: ((e.clientY - rect.top) / rect.height) * imgHeight,
    };
  }, [imgWidth, imgHeight]);

  const findBsAt = useCallback((x: number, y: number): BaseStation | null => {
    // Hit test in display coords
    const scaleX = displaySize.w / imgWidth;
    const hitR = HIT_RADIUS / scaleX; // convert hit radius to full-res pixels
    const hitRSq = hitR * hitR;
    for (let i = baseStations.length - 1; i >= 0; i--) {
      const bs = baseStations[i];
      const dx = bs.px - x;
      const dy = bs.py - y;
      if (dx * dx + dy * dy <= hitRSq) return bs;
    }
    return null;
  }, [baseStations, displaySize, imgWidth]);

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    const pos = toImageCoords(e);
    if (!pos || !maskData) return;

    const hitBs = findBsAt(pos.x, pos.y);

    if (e.button === 2) {
      if (hitBs) onDeleteBS(hitBs.id);
      return;
    }

    if (e.button === 0) {
      if (hitBs) {
        setDragging({ id: hitBs.id, offsetX: hitBs.px - pos.x, offsetY: hitBs.py - pos.y });
      } else {
        const ipx = Math.round(pos.x);
        const ipy = Math.round(pos.y);
        if (ipx >= 0 && ipx < imgWidth && ipy >= 0 && ipy < imgHeight) {
          if (maskData.mask[ipy * imgWidth + ipx] !== 1) {
            onAddBS(ipx, ipy);
          }
        }
      }
    }
  }, [toImageCoords, findBsAt, maskData, imgWidth, imgHeight, onAddBS, onDeleteBS]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const pos = toImageCoords(e);
    if (!pos) return;
    setMousePos(pos);

    if (dragging) {
      const newPx = Math.max(0, Math.min(imgWidth - 1, pos.x + dragging.offsetX));
      const newPy = Math.max(0, Math.min(imgHeight - 1, pos.y + dragging.offsetY));
      onMoveBS(dragging.id, Math.round(newPx), Math.round(newPy));
    }
  }, [toImageCoords, dragging, imgWidth, imgHeight, onMoveBS]);

  const handleMouseUp = useCallback(() => {
    setDragging(null);
  }, []);

  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
  }, []);

  const coordText = mousePos
    ? `x: ${((mousePos.x / imgWidth) * 640).toFixed(1)}m, y: ${((mousePos.y / imgHeight) * 430).toFixed(1)}m`
    : '';

  return (
    <div className={styles.container} ref={containerRef}>
      <canvas
        ref={canvasRef}
        className={styles.canvas}
        style={{ width: displaySize.w, height: displaySize.h }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onContextMenu={handleContextMenu}
      />
      <div className={styles.statusBar}>
        <span>{statusMessage}</span>
        <span className={styles.coords}>{coordText}</span>
      </div>
      {isCalculating && (
        <div className={styles.calculatingOverlay}>
          <div className={styles.spinner} />
        </div>
      )}
    </div>
  );
}
