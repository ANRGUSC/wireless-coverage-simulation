const MAP_WIDTH_M = 640.0;
const MAP_HEIGHT_M = 430.0;

export function pixelsToMeters(px: number, py: number, imgWidth: number, imgHeight: number): [number, number] {
  const xMeters = (px / imgWidth) * MAP_WIDTH_M;
  const yMeters = (py / imgHeight) * MAP_HEIGHT_M;
  return [xMeters, yMeters];
}

export function metersToPixels(xm: number, ym: number, imgWidth: number, imgHeight: number): [number, number] {
  const px = Math.floor((xm / MAP_WIDTH_M) * imgWidth);
  const py = Math.floor((ym / MAP_HEIGHT_M) * imgHeight);
  return [
    Math.max(0, Math.min(imgWidth - 1, px)),
    Math.max(0, Math.min(imgHeight - 1, py)),
  ];
}

export { MAP_WIDTH_M, MAP_HEIGHT_M };
