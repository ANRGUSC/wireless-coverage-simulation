// Bresenham's line algorithm for line-of-sight checking
// Returns false if any building pixel is encountered along the line
export function hasLineOfSight(
  px1: number, py1: number,
  px2: number, py2: number,
  mask: Uint8Array,
  imgWidth: number,
): boolean {
  let cx = px1;
  let cy = py1;
  const dx = Math.abs(px2 - px1);
  const dy = Math.abs(py2 - py1);
  const sx = px1 < px2 ? 1 : -1;
  const sy = py1 < py2 ? 1 : -1;
  let err = dx - dy;

  while (true) {
    if (mask[cy * imgWidth + cx] === 1) {
      return false;
    }
    if (cx === px2 && cy === py2) break;
    const e2 = 2 * err;
    if (e2 > -dy) {
      err -= dy;
      cx += sx;
    }
    if (e2 < dx) {
      err += dx;
      cy += sy;
    }
  }
  return true;
}
