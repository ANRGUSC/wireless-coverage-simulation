// tab10 palette matching Python's color scheme (RGB 0-1)
const TAB10: [number, number, number][] = [
  [0.12, 0.47, 0.71],
  [1.0, 0.50, 0.05],
  [0.17, 0.63, 0.17],
  [0.84, 0.15, 0.16],
  [0.58, 0.40, 0.74],
  [0.55, 0.34, 0.29],
  [0.89, 0.47, 0.76],
  [0.50, 0.50, 0.50],
  [0.74, 0.74, 0.13],
  [0.09, 0.75, 0.81],
];

export function hsvToRgb(h: number, s: number, v: number): [number, number, number] {
  if (s === 0) return [v, v, v];
  const i = Math.floor(h * 6.0);
  const f = h * 6.0 - i;
  const p = v * (1.0 - s);
  const q = v * (1.0 - s * f);
  const t = v * (1.0 - s * (1.0 - f));
  switch (i % 6) {
    case 0: return [v, t, p];
    case 1: return [q, v, p];
    case 2: return [p, v, t];
    case 3: return [p, q, v];
    case 4: return [t, p, v];
    case 5: return [v, p, q];
    default: return [v, t, p];
  }
}

export function getBsColors(count: number): [number, number, number][] {
  if (count <= 10) return TAB10.slice(0, count);
  return Array.from({ length: count }, (_, i) => {
    const hue = count <= 20 ? i / 20 : i / count;
    return hsvToRgb(hue, 0.8, 0.9);
  });
}

export function colorToRgb255(c: [number, number, number]): [number, number, number] {
  return [Math.round(c[0] * 255), Math.round(c[1] * 255), Math.round(c[2] * 255)];
}

export function colorToCss(c: [number, number, number]): string {
  return `rgb(${Math.round(c[0] * 255)},${Math.round(c[1] * 255)},${Math.round(c[2] * 255)})`;
}
