import type { BuildingMaskData } from '../types/index.ts';

export async function loadBuildingMask(url: string): Promise<BuildingMaskData & { rawImage: HTMLImageElement }> {
  const img = await new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = url;
  });

  const canvas = document.createElement('canvas');
  canvas.width = img.width;
  canvas.height = img.height;
  const ctx = canvas.getContext('2d')!;
  ctx.drawImage(img, 0, 0);
  const imageData = ctx.getImageData(0, 0, img.width, img.height);

  const totalPixels = img.width * img.height;
  const mask = new Uint8Array(totalPixels);
  let outdoorCount = 0;

  for (let i = 0; i < totalPixels; i++) {
    const r = imageData.data[i * 4];
    const g = imageData.data[i * 4 + 1];
    const b = imageData.data[i * 4 + 2];
    const gray = 0.299 * r + 0.587 * g + 0.114 * b;
    mask[i] = gray < 128 ? 1 : 0;
    if (mask[i] === 0) outdoorCount++;
  }

  return { mask, width: img.width, height: img.height, outdoorCount, rawImage: img };
}
