// Mulberry32 - fast seedable 32-bit PRNG
function mulberry32(seed: number): () => number {
  let s = seed | 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Box-Muller transform for Gaussian distribution
export class SeededRNG {
  private rng: () => number;
  private spare: number | null = null;

  constructor(seed: number) {
    this.rng = mulberry32(seed);
  }

  uniform(): number {
    return this.rng();
  }

  normal(mean: number = 0, std: number = 1): number {
    if (this.spare !== null) {
      const val = this.spare;
      this.spare = null;
      return mean + std * val;
    }
    let u: number, v: number, s: number;
    do {
      u = 2.0 * this.rng() - 1.0;
      v = 2.0 * this.rng() - 1.0;
      s = u * u + v * v;
    } while (s >= 1.0 || s === 0.0);
    const mul = Math.sqrt(-2.0 * Math.log(s) / s);
    this.spare = v * mul;
    return mean + std * u * mul;
  }

  normalArray(length: number, mean: number = 0, std: number = 1): Float32Array {
    const arr = new Float32Array(length);
    for (let i = 0; i < length; i++) {
      arr[i] = this.normal(mean, std);
    }
    return arr;
  }
}
