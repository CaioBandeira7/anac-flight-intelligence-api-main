import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const clamp = (v: number, min = 0, max = 1) => Math.min(max, Math.max(min, v));

/** Maps v from [a,b] to [0,1], clamped. */
export const progressIn = (v: number, a: number, b: number) => clamp((v - a) / (b - a));

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

export const easeInOutCubic = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;

export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

export const easeInCubic = (t: number) => t * t * t;

export const smoothstep = (a: number, b: number, v: number) => {
  const t = progressIn(v, a, b);
  return t * t * (3 - 2 * t);
};

const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });
const full = new Intl.NumberFormat("en-US");

export const formatCompact = (n: number) => compact.format(n);
export const formatNumber = (n: number) => full.format(n);
export const formatPercent = (n: number, digits = 1) => `${(n * 100).toFixed(digits)}%`;
