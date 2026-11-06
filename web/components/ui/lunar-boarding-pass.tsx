"use client"

/* eslint-disable react-hooks/refs, react-hooks/set-state-in-effect, @typescript-eslint/no-unused-vars --
 * Original third-party component, kept as shipped: it mirrors props into refs
 * during render and marks the back as printed from an effect. Both are
 * intentional there and behave correctly; rewriting them would change the
 * component this integration is required to preserve. */

import * as React from "react"

/**
 * Lunar Boarding Pass — a two-sided ticket for a trip to the Moon.
 *
 * Front: a black VIP pass. A halftone Moon sits in the stub, its craters and
 * maria placed from real selenographic coordinates, with the landing site
 * marked. Sweep the pointer across the ticket and the light swings round it
 * through its phases. A clarinet and a Saturn V float in a star field: point
 * at the clarinet and it plays, point at the rocket and it fires.
 *
 * Back: a silver boarding pass with a perforated stub. Tear the stub off
 * (drag it, or click / Enter) and the pass is stamped. Click either face, or
 * use the switch under it, to turn the ticket over.
 *
 * No dependencies and nothing fetched: React is the only import, the Moon is
 * canvas, the clarinet, rocket and stars are SVG built from numbers.
 *
 * Flight Intelligence integration — additive props only, the original look and
 * behaviour are unchanged when they are left at their defaults:
 *  - `lockTorn`: once torn the stub cannot be reattached (the pass is used).
 *  - `detach`: a torn stub falls away from the ticket instead of hanging off it.
 *  - `craftLabel` / `siteLabel`: relabel two printed fields.
 *  - `tearOnClick`: a click anywhere on the ticket tears the stub (no flip).
 *  - `showSideSwitch`: hide the front/back switch under the ticket.
 */

// #region pass
// Pure: coordinates, the Moon's surface and light, stars, drag maths.
// Lifted out and run by the test.

export const clamp01 = (v: number): number => (v > 0 ? (v < 1 ? v : 1) : 0)

export const smoothstep = (a: number, b: number, x: number): number => {
  if (a === b) return x < a ? 0 : 1
  const t = clamp01((x - a) / (b - a))
  return t * t * (3 - 2 * t)
}

const finite = (v: number): number => (Number.isFinite(v) ? v : 0)

/** 0.67416 → 0°40'27"N. Seconds are rounded and carry into minutes and degrees. */
export const toDMS = (deg: number, pos: string, neg: string): string => {
  const d = finite(deg)
  let s = Math.round(Math.abs(d) * 3600)
  const D = Math.floor(s / 3600)
  s -= D * 3600
  const M = Math.floor(s / 60)
  s -= M * 60
  const pad = (n: number): string => (n < 10 ? "0" : "") + n
  return D + "°" + pad(M) + "'" + pad(s) + '"' + (d < 0 ? neg : pos)
}

export const coordsDMS = (lat: number, lon: number): string => toDMS(lat, "N", "S") + " " + toDMS(lon, "E", "W")

export const coordsDecimal = (lat: number, lon: number): string =>
  finite(lat).toFixed(5) + "°, " + finite(lon).toFixed(5) + "°"

/** Selenographic lat/lon (degrees) → unit vector, viewer-facing: x right, y down, z toward us. */
export const project = (lat: number, lon: number): number[] => {
  const a = (finite(lat) * Math.PI) / 180
  const b = (finite(lon) * Math.PI) / 180
  return [Math.cos(a) * Math.sin(b), -Math.sin(a), Math.cos(a) * Math.cos(b)]
}

/** Great-circle distance in degrees. */
export const angDist = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
  const p = project(lat1, lon1)
  const q = project(lat2, lon2)
  const d = p[0] * q[0] + p[1] * q[1] + p[2] * q[2]
  return (Math.acos(d > 1 ? 1 : d < -1 ? -1 : d) * 180) / Math.PI
}

export const hash2 = (i: number, j: number): number => {
  let h = (Math.imul(i | 0, 374761393) + Math.imul(j | 0, 668265263)) | 0
  h = Math.imul(h ^ (h >>> 13), 1274126177)
  h ^= h >>> 16
  return (h >>> 0) / 4294967296
}

export const valueNoise = (x: number, y: number): number => {
  const i = Math.floor(x)
  const j = Math.floor(y)
  const fx = x - i
  const fy = y - j
  const u = fx * fx * (3 - 2 * fx)
  const v = fy * fy * (3 - 2 * fy)
  const a = hash2(i, j)
  const b = hash2(i + 1, j)
  const c = hash2(i, j + 1)
  const d = hash2(i + 1, j + 1)
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v
}

/** The dark seas: lat, lon, radius (degrees), depth. Rough, but where they really are. */
export const MARIA: number[][] = [
  [18, -57, 26, 0.7], // Oceanus Procellarum
  [33, -16, 17, 0.85], // Imbrium
  [28, 17.5, 9.5, 0.85], // Serenitatis
  [8.5, 31, 11, 0.85], // Tranquillitatis
  [17, 59, 7, 0.9], // Crisium
  [-8, 51, 9, 0.7], // Fecunditatis
  [-15, 35, 5, 0.7], // Nectaris
  [-21, -17, 10, 0.65], // Nubium
  [-24, -39, 5, 0.75], // Humorum
  [-10, -23, 6, 0.6], // Cognitum
  [13, 4, 4, 0.6], // Vaporum
  [57, 0, 8, 0.6], // Frigoris
  [56, -30, 7, 0.55],
  [56, 28, 6, 0.5],
]

/** Bright young craters: lat, lon, radius, brightness. Tycho, Copernicus, Kepler, Aristarchus. */
export const BRIGHT: number[][] = [
  [-43.3, -11.2, 5, 0.45],
  [9.6, -20.1, 3.5, 0.35],
  [8.1, -38, 2.5, 0.3],
  [23.7, -47.4, 2.5, 0.4],
]

/** How much light the surface returns at a point, 0 → 1. */
export const albedo = (lat: number, lon: number): number => {
  let keep = 1
  for (const m of MARIA) {
    const t = angDist(lat, lon, m[0], m[1]) / m[2]
    if (t < 1) {
      const w = 1 - t * t
      keep *= 1 - m[3] * w * w
    }
  }
  let a = 0.22 + 0.66 * keep
  for (const b of BRIGHT) {
    const t = angDist(lat, lon, b[0], b[1]) / b[2]
    if (t < 1) a += b[3] * (1 - t) * (1 - t)
  }
  a += (valueNoise(lat * 0.21 + 40, lon * 0.21 + 40) - 0.5) * 0.18
  a += (valueNoise(lat * 0.9, lon * 0.9) - 0.5) * 0.08
  return clamp01(a)
}

/**
 * How far to turn the Moon so a landing site sits on the face the stub shows.
 * The stub crops the western limb, so a site west of 12°E is turned east.
 */
export const turnFor = (lon: number): number => Math.max(0, Math.min(60, 12 - finite(lon)))

/**
 * The halftone grid: every dot inside a disc of radius r at (cx, cy), spaced
 * `cell` apart on a hex lattice, the globe turned east by `turn` degrees.
 * Flat: x, y, nx, ny, nz, albedo per dot.
 */
export const moonDots = (cx: number, cy: number, r: number, cell: number, turn: number): number[] => {
  const out: number[] = []
  if (!(r > 0) || !(cell > 0)) return out
  const row = cell * 0.866
  let k = 0
  for (let y = cy - r; y <= cy + r; y += row, k++) {
    for (let x = cx - r + (k % 2 ? cell / 2 : 0); x <= cx + r; x += cell) {
      const nx = (x - cx) / r
      const ny = (y - cy) / r
      const q = nx * nx + ny * ny
      if (q >= 1) continue
      const nz = Math.sqrt(1 - q)
      const lat = (Math.asin(-ny) * 180) / Math.PI
      const lon = (Math.atan2(nx, nz) * 180) / Math.PI - finite(turn)
      out.push(x, y, nx, ny, nz, albedo(lat, lon))
    }
  }
  return out
}

/** Pointer across the ticket (0 → 1) → light direction. Left edge: crescent lit from the left; centre: full; right: lit from the right. */
export const lightFrom = (px: number, py: number): number[] => {
  const phi = ((clamp01(finite(px)) - 0.5) * 2 * 150 * Math.PI) / 180
  const v = [Math.sin(phi), (clamp01(finite(py)) - 0.5) * 0.9, Math.cos(phi)]
  const n = Math.hypot(v[0], v[1], v[2])
  return [v[0] / n, v[1] / n, v[2] / n]
}

/** Where the light rests when no one is pointing: a slow sway around a waning gibbous. */
export const idleAt = (seconds: number): number => 0.56 + Math.sin((finite(seconds) * Math.PI * 2) / 26) * 0.07

/** Dot radius for one surface point under light l. Never negative, never wider than a cell. */
export const dotRadius = (alb: number, nx: number, ny: number, nz: number, l: number[], cell: number): number => {
  const lit = smoothstep(-0.08, 0.32, nx * l[0] + ny * l[1] + nz * l[2])
  const b = clamp01(alb) * (0.07 + 0.93 * lit) * (0.7 + 0.3 * nz)
  return cell * 0.46 * Math.pow(b, 0.8)
}

/** Pointer (0 → 1) → [rotateX, rotateY] in degrees. */
export const tiltFrom = (px: number, py: number, max: number): number[] => [
  -(clamp01(finite(py)) - 0.5) * 2 * max,
  (clamp01(finite(px)) - 0.5) * 2 * max,
]

/** A drag past a fifth of the stub, or a quick flick, tears it. */
export const tearDecision = (dx: number, v: number, w: number): boolean =>
  dx > w * 0.2 || (v > 0.5 && dx > w * 0.05)

/** The stub follows the finger freely at first, then stiffens like paper. */
export const resist = (dx: number, w: number): number => {
  const d = Math.max(0, finite(dx))
  const lim = Math.max(1, w) * 0.12
  return d < lim ? d : lim + (d - lim) * 0.22
}

export const mulberry = (seed: number): (() => number) => {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** n stars in a box: x, y, radius, twinkles (0/1), delay (s). Same seed, same sky. */
export const starField = (seed: number, n: number, x0: number, x1: number, y0: number, y1: number): number[][] => {
  const rnd = mulberry(seed)
  const out: number[][] = []
  for (let i = 0; i < n; i++) {
    const big = rnd() < 0.12
    out.push([
      x0 + rnd() * (x1 - x0),
      y0 + rnd() * (y1 - y0),
      big ? 0.9 + rnd() * 0.8 : 0.3 + rnd() * 0.5,
      big || rnd() < 0.1 ? 1 : 0,
      Math.round(rnd() * 40) / 10,
    ])
  }
  return out
}
// #endregion

export type Side = "front" | "back"

export type LunarBoardingPassProps = {
  /** Headline on both faces. */
  title?: string
  /** Class of travel: the front's corner and the back's header. */
  tier?: string
  /** The front's date. */
  date?: string
  /** Over the Moon. `\n` breaks a line. */
  welcome?: string
  /** Fine print beside the stub. `\n` breaks a line. */
  eyebrow?: string
  /** The two words floating in the art. */
  words?: [string, string]
  /** Two lines of fine print along the front's foot. */
  notes?: [string, string]
  passenger?: string
  from?: string
  to?: string
  craft?: string
  dateCode?: string
  gate?: string
  group?: string
  seat?: string
  boardingTime?: string
  /** Landing site name. */
  site?: string
  /** Landing site, selenographic degrees. Printed on both faces and marked on the Moon. */
  lat?: number
  lon?: number
  seq?: string
  featuring?: string
  /** The big thin line on the back. */
  headline?: string
  /** What the stamp says when the stub comes off. */
  stamp?: string
  /** Labels for the switch under the ticket. */
  sideLabels?: [string, string]
  night?: string
  starInk?: string
  paper?: string
  paperInk?: string
  stampColor?: string
  fontCondensed?: string
  fontMono?: string
  fontDisplay?: string
  defaultSide?: Side
  onSideChange?: (side: Side) => void
  defaultTorn?: boolean
  onTear?: (torn: boolean) => void
  /** Integration: once torn, the stub stays torn (no reattach). */
  lockTorn?: boolean
  /** Integration: a torn stub separates and falls away from the ticket. */
  detach?: boolean
  /** Integration: label for the craft field (original "Spacecraft number"). */
  craftLabel?: string
  /** Integration: label for the site field (original "Landing site"). */
  siteLabel?: string
  /** Integration: a click anywhere on the ticket tears the stub instead of flipping it. */
  tearOnClick?: boolean
  /** Integration: show the front/back switch under the ticket (original: always). */
  showSideSwitch?: boolean
  /** Largest tilt in degrees. `0` holds it flat. */
  tilt?: number
  /** The height follows the 1000 : 330 ticket. */
  maxWidth?: number | string
  className?: string
}

const VIEW_W = 1000
const VIEW_H = 330
/** Perforation on the back, as a fraction of the width. */
const CUT = 0.774
/** The Moon in the front stub (226 wide): centre and radius in stub fractions. */
const MOON = { x: 53 / 226, y: 201 / 330, r: 128 / 226 }

const CONDENSED =
  '"Oswald", "Bebas Neue", "Avenir Next Condensed", "Helvetica Neue", "Arial Narrow", "Roboto Condensed", "Liberation Sans Narrow", "DejaVu Sans Condensed", sans-serif'
const MONO = '"Courier Prime", "IBM Plex Mono", "Courier New", ui-monospace, monospace'
const DISPLAY = '"Futura", "Century Gothic", "Avenir Next", "Josefin Sans", "Quicksand", ui-sans-serif, sans-serif'

const pts = (a: number[][]): string => a.map((p) => p[0] + "," + p[1]).join(" ")

const STARS = starField(1969, 120, 240, 990, 10, 320)

const CSS = [
  ".lbp{position:relative;width:100%;margin:0 auto}",
  ".lbp-stage{position:relative;width:100%;perspective:1800px;touch-action:pan-y}",
  ".lbp-tilt,.lbp-flip{position:absolute;inset:0;transform-style:preserve-3d}",
  ".lbp-tilt{transform:rotateX(var(--rx,0deg)) rotateY(var(--ry,0deg));transition:transform .6s cubic-bezier(.2,.8,.2,1)}",
  ".lbp-flip{cursor:pointer;transition:transform 1.05s cubic-bezier(.65,-0.2,.25,1.2)}",
  ".lbp-face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;",
  "filter:drop-shadow(0 1.4cqw 1.8cqw rgba(0,0,0,.2)) drop-shadow(0 .25cqw .35cqw rgba(0,0,0,.14))}",
  ".lbp-back{transform:rotateY(180deg)}",
  ".lbp-night{position:absolute;inset:0;overflow:hidden;border-radius:.35cqw;background:var(--lbp-night);color:var(--lbp-star);",
  "box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--lbp-star) 9%,transparent)}",
  ".lbp-layer{position:absolute;inset:0;width:100%;height:100%;pointer-events:none}",
  ".lbp-grain{opacity:.16;mix-blend-mode:screen}",
  ".lbp-piece .lbp-grain{opacity:.3;mix-blend-mode:multiply}",
  ".lbp-glow{background:radial-gradient(circle at var(--mx,50%) var(--my,40%),color-mix(in srgb,var(--lbp-star) 12%,transparent),transparent 42%)}",
  ".lbp-piece{position:absolute;top:0;bottom:0;overflow:hidden;color:var(--lbp-ink);",
  "background:linear-gradient(162deg,color-mix(in srgb,var(--lbp-paper) 82%,#fff) 0%,var(--lbp-paper) 48%,color-mix(in srgb,var(--lbp-paper) 88%,#000) 100%)}",
  ".lbp-main{left:0;width:77.4%;border-radius:.35cqw 0 0 .35cqw;padding:2.3cqw 2.6cqw 2.1cqw;display:flex;flex-direction:column;",
  "-webkit-mask:radial-gradient(circle at 100% 50%,#0000 .2cqw,#000 .24cqw) 0 0/100% .86cqw repeat-y;",
  "mask:radial-gradient(circle at 100% 50%,#0000 .2cqw,#000 .24cqw) 0 0/100% .86cqw repeat-y}",
  ".lbp-stub{left:77.4%;width:22.6%;border-radius:0 .35cqw .35cqw 0;padding:2.3cqw 1.9cqw 2.1cqw;display:flex;flex-direction:column;",
  "font:inherit;text-align:left;border:0;margin:0;cursor:grab;touch-action:pan-y;transform-origin:0 100%;",
  "transition:transform .75s cubic-bezier(.2,.9,.25,1.25);",
  "-webkit-mask:radial-gradient(circle at 0 50%,#0000 .2cqw,#000 .24cqw) 0 0/100% .86cqw repeat-y;",
  "mask:radial-gradient(circle at 0 50%,#0000 .2cqw,#000 .24cqw) 0 0/100% .86cqw repeat-y}",
  ".lbp-stub:active{cursor:grabbing}",
  ".lbp-stub:focus-visible{outline:2px solid var(--lbp-stamp);outline-offset:-4px}",
  ".lbp-stub.is-torn{transform:translate(2.4cqw,1.1cqw) rotate(4deg);cursor:pointer}",
  ".lbp-stub.is-torn.is-detached{transform:translate(14cqw,9cqw) rotate(17deg);opacity:0;cursor:default;pointer-events:none;transition:transform 1.1s cubic-bezier(.3,.6,.4,1),opacity .5s ease .55s}",
  ".lbp-foil{background:linear-gradient(115deg,transparent calc(var(--mx,50%) - 24%),rgba(255,255,255,.62) var(--mx,50%),transparent calc(var(--mx,50%) + 24%)) no-repeat;mix-blend-mode:soft-light}",
  ".lbp-main .lbp-foil{background-size:129.2% 100%;background-position:0 0}",
  ".lbp-stub .lbp-foil{background-size:442.5% 100%;background-position:100% 0}",
  ".lbp-c{font-family:var(--lbp-cond);font-weight:700;font-stretch:condensed;text-transform:uppercase;line-height:1;letter-spacing:.01em}",
  ".lbp-m{font-family:var(--lbp-mono);text-transform:uppercase;line-height:1.05;letter-spacing:.03em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}",
  ".lbp-d{font-family:var(--lbp-disp);font-weight:300;text-transform:uppercase;letter-spacing:.16em;line-height:1;white-space:nowrap}",
  ".lbp-l{display:block;font-family:var(--lbp-cond);font-weight:600;font-stretch:condensed;text-transform:uppercase;font-size:.6cqw;letter-spacing:.07em;line-height:1;opacity:.82;margin-bottom:.45cqw;white-space:nowrap}",
  ".lbp-at{position:absolute;white-space:nowrap}",
  ".lbp-pre{white-space:pre-line}",
  ".lbp-head{display:flex;align-items:baseline;justify-content:space-between;gap:1.5cqw;padding-bottom:1cqw;border-bottom:1px solid var(--lbp-rule)}",
  ".lbp-grid{display:grid;grid-template-columns:1.08fr 1fr .78fr;border-bottom:1px solid var(--lbp-rule)}",
  ".lbp-cell{padding:1cqw 1.2cqw 1cqw 0;min-width:0}",
  ".lbp-cell+.lbp-cell,.lbp-grid>:nth-child(5),.lbp-grid>:nth-child(6){border-left:1px solid var(--lbp-rule);padding-left:1.2cqw}",
  ".lbp-grid>:nth-child(4){border-left:0;padding-left:0}",
  ".lbp-grid>:nth-child(5),.lbp-grid>:nth-child(6){border-top:1px solid var(--lbp-rule)}",
  ".lbp-row{display:flex;gap:2.4cqw}",
  ".lbp-foot{flex:1;display:flex;align-items:center;gap:2cqw;padding-top:1.1cqw}",
  ".lbp-sf{margin-top:1.45cqw;min-width:0}",
  ".lbp-stamp{position:absolute;left:33%;top:52%;padding:.35cqw;border:.2cqw solid var(--lbp-stamp);border-radius:.45cqw;color:var(--lbp-stamp);",
  "opacity:0;transform:rotate(-9deg);pointer-events:none;mix-blend-mode:multiply}",
  ".lbp-stamp>span{display:block;padding:.45cqw 1.1cqw;border:.08cqw solid var(--lbp-stamp);border-radius:.25cqw;text-align:center}",
  ".lbp-main.is-torn .lbp-stamp{opacity:.86;animation:lbp-stamp .5s cubic-bezier(.3,1.6,.5,1) both}",
  "@keyframes lbp-stamp{0%{opacity:0;transform:rotate(-4deg) scale(1.9)}100%{opacity:.86;transform:rotate(-9deg) scale(1)}}",
  ".lbp-hint{position:absolute;left:77.4%;bottom:1.6cqw;transform:translateX(-50%) rotate(180deg);writing-mode:vertical-rl;font-family:var(--lbp-cond);",
  "font-size:.5cqw;letter-spacing:.3em;text-transform:uppercase;color:var(--lbp-ink);opacity:.45;pointer-events:none;white-space:nowrap;transition:opacity .3s}",
  ".lbp-back.is-torn .lbp-hint{opacity:0}",
  ".lbp-printed .lbp-v{animation:lbp-type .8s steps(14,end) both}",
  "@keyframes lbp-type{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}",
  ".lbp-tw{animation:lbp-tw 3.4s ease-in-out infinite}",
  "@keyframes lbp-tw{0%,100%{opacity:1}50%{opacity:.2}}",
  ".lbp-ship{transition:transform .9s cubic-bezier(.2,.8,.2,1)}",
  ".lbp-rocket:hover .lbp-ship{transform:translateX(14px)}",
  ".lbp-flame{opacity:0;transform-box:fill-box;transform-origin:100% 50%;transform:scaleX(.2);transition:opacity .25s,transform .35s}",
  ".lbp-rocket:hover .lbp-flame{opacity:1;transform:scaleX(1);animation:lbp-flick .09s steps(2) infinite alternate}",
  "@keyframes lbp-flick{to{transform:scaleX(1.18) scaleY(1.06)}}",
  ".lbp-note{opacity:0}",
  ".lbp-clarinet:hover .lbp-note{animation:lbp-note 2.2s ease-out infinite}",
  "@keyframes lbp-note{0%{opacity:0;transform:translate(0,0) scale(.5)}18%{opacity:1}100%{opacity:0;transform:translate(var(--tx),var(--ty)) rotate(-16deg) scale(1.1)}}",
  ".lbp-body{transform-box:fill-box;transform-origin:85% 50%;transition:transform .5s}",
  ".lbp-clarinet:hover .lbp-body{transform:rotate(-1.2deg)}",
  "@media (prefers-reduced-motion: reduce){.lbp-tilt,.lbp-flip,.lbp-stub,.lbp-ship,.lbp-body{transition-duration:.01ms}",
  ".lbp-stub.is-detached{transition-duration:.01ms}.lbp-tw,.lbp-flame,.lbp-v,.lbp-stamp,.lbp-note{animation:none!important}.lbp-rocket:hover .lbp-flame{transform:none}}",
].join("")

function Star({ size }: { size: string }) {
  const p: number[][] = []
  for (let i = 0; i < 16; i++) {
    const a = (i * Math.PI) / 8 - Math.PI / 2
    const r = i % 2 ? 0.34 : 1
    p.push([Math.round((12 + Math.cos(a) * r * 11) * 100) / 100, Math.round((12 + Math.sin(a) * r * 11) * 100) / 100])
  }
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} aria-hidden="true" style={{ display: "inline-block", maxWidth: "none", verticalAlign: "-0.1em" }}>
      <polygon points={pts(p)} fill="currentColor" />
    </svg>
  )
}

/** A Saturn V, nose to the right, engraved in white. Stages to scale, more or less. */
function Rocket({ ink, night, font }: { ink: string; night: string; font: string }) {
  const y = 214
  const R1 = 21
  const R3 = 14
  const R5 = 8.2
  const seam = (x: number, h: number) => <line key={x} x1={x} x2={x} y1={y - h} y2={y + h} stroke={night} strokeWidth={0.7} />
  const truss: number[][] = []
  for (let x = 907, k = 0; x <= 934; x += 4.5, k++) truss.push([x, y + (k % 2 ? 2.4 : -2.4)])
  return (
    <g className="lbp-rocket">
      <rect x={320} y={y - 42} width={650} height={84} fill="transparent" />
      <g className="lbp-ship">
        <g className="lbp-flame">
          <polygon points={pts([[402, y - 19], [366, y - 13], [318, y], [366, y + 13], [402, y + 19]])} fill={ink} opacity={0.92} />
          <polygon points={pts([[402, y - 10], [378, y - 6], [350, y], [378, y + 6], [402, y + 10]])} fill={night} opacity={0.55} />
        </g>
        {[-12, 12, 0].map((o) => (
          <polygon key={o} points={pts([[419, y + o - 5], [419, y + o + 5], [402, y + o + 8.5], [402, y + o - 8.5]])} fill={ink} stroke={night} strokeWidth={0.8} />
        ))}
        <polygon points={pts([[410, y - R1 - 12], [424, y - R1 - 12], [454, y - R1], [419, y - R1]])} fill={ink} stroke={night} strokeWidth={0.6} />
        <polygon points={pts([[410, y + R1 + 12], [424, y + R1 + 12], [454, y + R1], [419, y + R1]])} fill={ink} stroke={night} strokeWidth={0.6} />
        {/* S-IC, interstage, S-II */}
        <rect x={418} y={y - R1} width={304} height={R1 * 2} fill={ink} />
        <rect x={418} y={y - R1} width={30} height={R1} fill={night} />
        <rect x={564} y={y} width={30} height={R1} fill={night} />
        <rect x={448} y={y - R1 + 3} width={116} height={2} fill={night} />
        <rect x={448} y={y + R1 - 5} width={116} height={2} fill={night} />
        <text x={474} y={y + 2.8} fontSize={7.5} letterSpacing={1.9} fill={night} fontFamily={font} fontWeight={700}>
          UNITED STATES
        </text>
        <rect x={704} y={y - R1} width={12} height={R1 * 2} fill={night} />
        {[448, 500, 548, 564, 594, 605, 617, 642, 667, 692].map((x) => seam(x, R1))}
        {/* interstage taper, S-IVB, instrument unit */}
        <polygon points={pts([[722, y - R1], [746, y - R3], [746, y + R3], [722, y + R1]])} fill={ink} />
        <rect x={746} y={y - R3} width={79} height={R3 * 2} fill={ink} />
        <rect x={746} y={y - R3} width={22} height={R3} fill={night} />
        <rect x={798} y={y - R3} width={6} height={R3 * 2} fill={night} />
        {[734, 768, 784, 821, 825].map((x) => seam(x, x < 746 ? 17.5 : R3))}
        {/* adapter, service module, command module */}
        <polygon points={pts([[825, y - R3], [861, y - R5], [861, y + R5], [825, y + R3]])} fill={ink} />
        <path d={"M825 " + (y - R3) + " L861 " + y + " M825 " + (y + R3) + " L861 " + y} stroke={night} strokeWidth={0.6} />
        <rect x={861} y={y - R5} width={31} height={R5 * 2} fill={ink} />
        <rect x={871} y={y - R5} width={8} height={4} fill={night} />
        {[861, 876, 892].map((x) => seam(x, R5))}
        <polygon points={pts([[892, y - R5], [907, y - 2], [907, y + 2], [892, y + R5]])} fill={ink} />
        {/* launch escape tower */}
        <polyline points={pts(truss)} fill="none" stroke={ink} strokeWidth={0.9} />
        <path d={"M907 " + (y - 2.4) + " H934 M907 " + (y + 2.4) + " H934"} stroke={ink} strokeWidth={0.8} />
        <rect x={934} y={y - 2.3} width={16} height={4.6} fill={ink} />
        <polygon points={pts([[950, y - 2.3], [958, y], [950, y + 2.3]])} fill={ink} />
        <polygon points={pts([[942, y - 2.3], [946, y - 4.6], [947, y - 2.3]])} fill={ink} />
        <polygon points={pts([[942, y + 2.3], [946, y + 4.6], [947, y + 2.3]])} fill={ink} />
        <path
          d={
            "M418 " + (y - R1) + " H722 L746 " + (y - R3) + " H825 L861 " + (y - R5) + " H892 L907 " + (y - 2) + " V" + (y + 2) +
            " L892 " + (y + R5) + " H861 L825 " + (y + R3) + " H746 L722 " + (y + R1) + " H418 Z"
          }
          fill="none"
          stroke={ink}
          strokeWidth={1}
        />
      </g>
    </g>
  )
}

/** A B♭ clarinet, bell to the left, keywork in black. Point at it and it plays. */
function Clarinet({ ink, night }: { ink: string; night: string }) {
  const y = 96
  const holes = [392, 418, 446, 474, 502, 530, 610, 640, 668, 696, 724]
  const rings = [446, 474, 502, 640, 668, 696]
  const pads = [404, 460, 488, 520, 620, 654, 702, 738]
  const notes = [
    { x: 300, d: 0, tx: "-34px", ty: "-52px" },
    { x: 310, d: 0.75, tx: "-12px", ty: "-64px" },
    { x: 296, d: 1.5, tx: "-48px", ty: "-30px" },
  ]
  return (
    <g className="lbp-clarinet">
      <rect x={260} y={y - 60} width={630} height={90} fill="transparent" />
      {notes.map((n, i) => (
        <g key={i} className="lbp-note" style={{ animationDelay: n.d + "s", ["--tx" as string]: n.tx, ["--ty" as string]: n.ty } as React.CSSProperties}>
          <g transform={"translate(" + n.x + " " + (y - 14) + ")"}>
            <ellipse cx={0} cy={0} rx={3.6} ry={2.6} transform="rotate(-20)" fill={ink} />
            <path d={i === 1 ? "M3.2 -1 V-15 L13 -18 V-4" : "M3.2 -1 V-15 Q9 -12 9.5 -6"} fill="none" stroke={ink} strokeWidth={1.2} />
            {i === 1 && <ellipse cx={9.8} cy={-3} rx={3.6} ry={2.6} transform="rotate(-20 9.8 -3)" fill={ink} />}
          </g>
        </g>
      ))}
      <g className="lbp-body">
        <path d={"M300 " + (y - 22) + " Q322 " + (y - 10) + " 353 " + (y - 8.5) + " L353 " + (y + 8.5) + " Q322 " + (y + 10) + " 300 " + (y + 22) + " Z"} fill={ink} />
        <rect x={297} y={y - 22.5} width={4} height={45} fill={ink} stroke={night} strokeWidth={0.6} />
        <rect x={352} y={y - 10} width={6} height={20} fill={ink} stroke={night} strokeWidth={0.6} />
        <rect x={358} y={y - 8.5} width={217} height={17} fill={ink} />
        <rect x={575} y={y - 10} width={5} height={20} fill={ink} stroke={night} strokeWidth={0.6} />
        <rect x={580} y={y - 10} width={5} height={20} fill={ink} stroke={night} strokeWidth={0.6} />
        <rect x={585} y={y - 8} width={185} height={16} fill={ink} />
        <rect x={770} y={y - 9.5} width={6} height={19} fill={ink} stroke={night} strokeWidth={0.6} />
        <rect x={776} y={y - 9.5} width={42} height={19} rx={2} fill={ink} stroke={night} strokeWidth={0.4} />
        <rect x={818} y={y - 9} width={4} height={18} fill={ink} stroke={night} strokeWidth={0.6} />
        <path d={"M822 " + (y - 8) + " L864 " + (y - 6) + " Q878 " + (y - 5) + " 882 " + (y + 1) + " L882 " + (y + 3) + " L822 " + (y + 8) + " Z"} fill={ink} />
        <path d={"M842 " + (y + 7.4) + " L885 " + (y + 3.4) + " L885 " + (y + 5) + " L842 " + (y + 9) + " Z"} fill={ink} stroke={night} strokeWidth={0.5} />
        <rect x={836} y={y - 7.9} width={4} height={16.2} fill={night} stroke={ink} strokeWidth={0.6} />
        <rect x={852} y={y - 7.2} width={4} height={14.6} fill={night} stroke={ink} strokeWidth={0.6} />
        {/* turned shading along the underside */}
        <path d={"M358 " + (y + 5.2) + " H770 M358 " + (y + 6.8) + " H770"} stroke={night} strokeWidth={0.5} opacity={0.45} />
        {/* keywork */}
        <path d={"M384 " + (y - 5) + " H564 M598 " + (y - 5) + " H758 M360 " + (y + 5.6) + " H386"} stroke={night} strokeWidth={0.8} />
        {holes.map((x) => (
          <circle key={"h" + x} cx={x} cy={y} r={2.2} fill={night} />
        ))}
        {rings.map((x) => (
          <circle key={"r" + x} cx={x} cy={y} r={4.3} fill="none" stroke={night} strokeWidth={0.9} />
        ))}
        {pads.map((x) => (
          <ellipse key={"p" + x} cx={x} cy={y - 5} rx={3.3} ry={1.9} fill={night} />
        ))}
        <ellipse cx={370} cy={y + 5.6} rx={3.3} ry={1.9} fill={night} />
        <path d={"M748 " + (y - 8) + " L764 " + (y - 11.5) + " L778 " + (y - 9.5)} fill="none" stroke={ink} strokeWidth={1.1} />
      </g>
    </g>
  )
}

function Grain({ id }: { id: string }) {
  return (
    <svg className="lbp-layer lbp-grain" aria-hidden="true" style={{ maxWidth: "none" }}>
      <filter id={id}>
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter={"url(#" + id + ")"} />
    </svg>
  )
}

function Field({ label, value, size, d }: { label: string; value: string; size: number; d?: number }) {
  return (
    <span style={{ display: "block", minWidth: 0 }}>
      <span className="lbp-l">{label}</span>
      <span className="lbp-m lbp-v" style={{ display: "block", fontSize: size + "cqw", animationDelay: (d || 0) + "s" }}>
        {value}
      </span>
    </span>
  )
}

export default function LunarBoardingPass({
  title = "Fly me to the moon",
  tier = "VIP",
  date = "20 July '69",
  welcome = "Welcome\naboard",
  eyebrow = "The 1st station of\nthe space tour",
  words = ["Space", "Jazz"],
  notes = ["太空爵士・宇宙巡演", "首站—静海基地"],
  passenger = "Neil Armstrong",
  from = "Earth",
  to = "Moon",
  craft = "1969-059A",
  dateCode = "20JUL69",
  gate = "F3",
  group = "C",
  seat = "21J",
  boardingTime = "UTC2000",
  site = "Tranquility Base",
  lat = 0.67416,
  lon = 23.47314,
  seq = "SEQ 060 MFDBAN  974294U89",
  featuring = "Featuring all stars crew",
  headline = "Space Jazz",
  stamp = "Boarded",
  sideLabels = ["VIP pass", "Boarding pass"],
  night = "#0b0b0c",
  starInk = "#f1f0eb",
  paper = "#c9c9c6",
  paperInk = "#1b1b1b",
  stampColor = "#a3362a",
  fontCondensed = CONDENSED,
  fontMono = MONO,
  fontDisplay = DISPLAY,
  defaultSide = "front",
  onSideChange,
  defaultTorn = false,
  onTear,
  lockTorn = false,
  detach = false,
  craftLabel = "Spacecraft number",
  siteLabel = "Landing site",
  tearOnClick = false,
  showSideSwitch = true,
  tilt = 6,
  maxWidth = 960,
  className = "",
}: LunarBoardingPassProps) {
  const uid = React.useId().replace(/[^a-zA-Z0-9]/g, "")
  const [turns, setTurns] = React.useState(defaultSide === "back" ? 1 : 0)
  const side: Side = turns % 2 ? "back" : "front"
  const [printed, setPrinted] = React.useState(defaultSide === "back")
  const [torn, setTorn] = React.useState(defaultTorn)
  const [reduced, setReduced] = React.useState(false)

  const stageRef = React.useRef<HTMLDivElement>(null)
  const tiltRef = React.useRef<HTMLDivElement>(null)
  const moonRef = React.useRef<HTMLCanvasElement>(null)
  const stubRef = React.useRef<HTMLButtonElement>(null)
  const pointer = React.useRef<number[] | null>(null)
  const sideRef = React.useRef(side)
  sideRef.current = side
  const redraw = React.useRef<() => void>(() => {})
  const drag = React.useRef<{ x: number; t: number; dx: number; v: number; moved: boolean } | null>(null)
  const swallowClick = React.useRef(false)
  const cbs = React.useRef({ onSideChange, onTear })
  cbs.current = { onSideChange, onTear }

  React.useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)")
    const onMq = () => setReduced(mq.matches)
    onMq()
    mq.addEventListener("change", onMq)
    return () => mq.removeEventListener("change", onMq)
  }, [])

  const firstSide = React.useRef(true)
  React.useEffect(() => {
    if (firstSide.current) {
      firstSide.current = false
      return
    }
    if (side === "back") setPrinted(true)
    cbs.current.onSideChange?.(side)
  }, [side])

  const firstTear = React.useRef(true)
  React.useEffect(() => {
    if (firstTear.current) {
      firstTear.current = false
      return
    }
    cbs.current.onTear?.(torn)
  }, [torn])

  // The Moon: a halftone redrawn from a cached lattice whenever the light moves.
  React.useEffect(() => {
    const canvas = moonRef.current
    const ctx = canvas && canvas.getContext("2d")
    if (!canvas || !ctx) return
    let dots: number[] = []
    let cell = 1
    let W = 0
    let H = 0
    let cx = 0
    let cy = 0
    let R = 0
    let dpr = 1
    const turn = turnFor(lon)
    const here = project(lat, lon + turn)
    let light = lightFrom(idleAt(0), 0.38)
    let raf = 0
    let visible = true

    const draw = (pulse: number) => {
      if (!W) return
      ctx.clearRect(0, 0, W, H)
      ctx.fillStyle = starInk
      ctx.beginPath()
      for (let i = 0; i < dots.length; i += 6) {
        const r = dotRadius(dots[i + 5], dots[i + 2], dots[i + 3], dots[i + 4], light, cell)
        if (r < 0.3) continue
        ctx.moveTo(dots[i] + r, dots[i + 1])
        ctx.arc(dots[i], dots[i + 1], r, 0, Math.PI * 2)
      }
      ctx.fill()
      if (here[2] > 0.05) {
        const mx = cx + R * here[0]
        const my = cy + R * here[1]
        const s = R * 0.034
        ctx.lineWidth = 3.2 * dpr
        ctx.strokeStyle = night
        ctx.beginPath()
        ctx.arc(mx, my, s, 0, Math.PI * 2)
        ctx.stroke()
        ctx.lineWidth = 1.2 * dpr
        ctx.strokeStyle = starInk
        ctx.stroke()
        ctx.fillStyle = starInk
        ctx.beginPath()
        ctx.arc(mx, my, 1.2 * dpr, 0, Math.PI * 2)
        ctx.fill()
        if (pulse > 0) {
          ctx.globalAlpha = 1 - pulse
          ctx.beginPath()
          ctx.arc(mx, my, s + R * 0.1 * pulse, 0, Math.PI * 2)
          ctx.stroke()
          ctx.globalAlpha = 1
        }
      }
    }

    const build = () => {
      dpr = Math.min(2, window.devicePixelRatio || 1)
      W = Math.round(canvas.clientWidth * dpr)
      H = Math.round(canvas.clientHeight * dpr)
      if (!W || !H) return
      canvas.width = W
      canvas.height = H
      R = W * MOON.r
      cx = W * MOON.x
      cy = H * MOON.y
      cell = Math.max(2.1 * dpr, R / 36)
      dots = moonDots(cx, cy, R, cell, turn)
      draw(0)
    }

    const target = (t: number) => {
      const p = pointer.current
      return p ? lightFrom(p[0], p[1]) : lightFrom(idleAt(t), 0.38)
    }

    const tick = (now: number) => {
      raf = requestAnimationFrame(tick)
      if (sideRef.current !== "front") return
      const to = target(now / 1000)
      for (let k = 0; k < 3; k++) light[k] += (to[k] - light[k]) * 0.09
      const n = Math.hypot(light[0], light[1], light[2]) || 1
      light = [light[0] / n, light[1] / n, light[2] / n]
      draw(((now / 1000) % 2.4) / 2.4)
    }
    const start = () => {
      if (!raf && visible && !reduced) raf = requestAnimationFrame(tick)
    }
    const stop = () => {
      cancelAnimationFrame(raf)
      raf = 0
    }

    // Reduced motion: no drift and no pulse, but the light still follows the
    // pointer, because that motion is the reader's own.
    redraw.current = () => {
      if (raf) return
      light = target(0)
      draw(0)
    }

    build()
    const observer = new ResizeObserver(build)
    observer.observe(canvas)
    const io = new IntersectionObserver(([e]) => {
      visible = e.isIntersecting
      if (visible) start()
      else stop()
    })
    io.observe(canvas)
    start()
    return () => {
      stop()
      observer.disconnect()
      io.disconnect()
      redraw.current = () => {}
    }
  }, [lat, lon, night, starInk, reduced])

  const flip = () => setTurns((t) => t + 1)
  const show = (s: Side) => {
    if (s !== side) flip()
  }

  const onMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = stageRef.current
    const t = tiltRef.current
    if (!el || !t) return
    const r = el.getBoundingClientRect()
    const px = clamp01((e.clientX - r.left) / r.width)
    const py = clamp01((e.clientY - r.top) / r.height)
    t.style.setProperty("--mx", (px * 100).toFixed(1) + "%")
    t.style.setProperty("--my", (py * 100).toFixed(1) + "%")
    if (tilt && !reduced && e.pointerType === "mouse") {
      const a = tiltFrom(px, py, tilt)
      t.style.setProperty("--rx", a[0].toFixed(2) + "deg")
      t.style.setProperty("--ry", a[1].toFixed(2) + "deg")
    }
    pointer.current = [px, py]
    redraw.current()
  }
  const onLeave = () => {
    const t = tiltRef.current
    if (t) {
      t.style.setProperty("--rx", "0deg")
      t.style.setProperty("--ry", "0deg")
    }
    pointer.current = null
    redraw.current()
  }

  const stubDown = (e: React.PointerEvent<HTMLButtonElement>) => {
    if (torn || e.button !== 0) return
    drag.current = { x: e.clientX, t: performance.now(), dx: 0, v: 0, moved: false }
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  const stubMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = drag.current
    const el = stubRef.current
    if (!d || !el) return
    const now = performance.now()
    const dx = Math.max(0, e.clientX - d.x)
    d.v = (dx - d.dx) / Math.max(1, now - d.t)
    d.t = now
    d.dx = dx
    if (dx > 4) d.moved = true
    const w = el.offsetWidth
    const shown = resist(dx, w)
    el.style.transition = "none"
    el.style.transform = "translateX(" + shown.toFixed(1) + "px) rotate(" + ((shown / Math.max(1, w)) * 7).toFixed(2) + "deg)"
  }
  const stubUp = () => {
    const d = drag.current
    const el = stubRef.current
    drag.current = null
    if (!d || !el) return
    el.style.transition = ""
    el.style.transform = ""
    if (d.moved) {
      swallowClick.current = true
      if (tearDecision(d.dx, d.v, el.offsetWidth)) setTorn(true)
    }
  }
  const stubClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    if (swallowClick.current) {
      swallowClick.current = false
      return
    }
    if (lockTorn && torn) return
    setTorn((v) => (lockTorn ? true : !v))
  }

  const dms = coordsDMS(lat, lon)
  const dec = coordsDecimal(lat, lon)
  const front = side === "front"
  const vars = {
    "--lbp-night": night,
    "--lbp-star": starInk,
    "--lbp-paper": paper,
    "--lbp-ink": paperInk,
    "--lbp-rule": "color-mix(in srgb, " + paperInk + " 55%, transparent)",
    "--lbp-stamp": stampColor,
    "--lbp-cond": fontCondensed,
    "--lbp-mono": fontMono,
    "--lbp-disp": fontDisplay,
  } as React.CSSProperties
  const at = (x: number, y: number): React.CSSProperties => ({ left: x / 10 + "%", top: (y / VIEW_H) * 100 + "%" })

  return (
    <div className={("lbp " + className).trim()} style={{ ...vars, maxWidth }}>
      <style>{CSS}</style>
      <div
        ref={stageRef}
        className="lbp-stage"
        style={{ aspectRatio: VIEW_W + " / " + VIEW_H, containerType: "inline-size" }}
        onPointerMove={onMove}
        onPointerLeave={onLeave}
      >
        <div ref={tiltRef} className="lbp-tilt">
          <div
            className="lbp-flip"
            style={{ transform: "rotateY(" + turns * 180 + "deg)" }}
            onClick={tearOnClick ? () => setTorn(true) : flip}
          >
            {/* ---------------- front: VIP ---------------- */}
            <div className="lbp-face" aria-hidden={!front}>
              <div className="lbp-night">
                <div className="lbp-layer" style={{ width: "22.6%" }}>
                  <canvas ref={moonRef} className="lbp-layer" style={{ maxWidth: "none" }} aria-hidden="true" />
                </div>
                <svg className="lbp-layer" viewBox={"0 0 " + VIEW_W + " " + VIEW_H} style={{ maxWidth: "none", pointerEvents: "auto" }} aria-hidden="true">
                  {STARS.map((s, i) => (
                    <circle key={i} cx={s[0]} cy={s[1]} r={s[2]} fill={starInk} className={s[3] ? "lbp-tw" : undefined} style={s[3] ? { animationDelay: s[4] + "s" } : undefined} />
                  ))}
                  <line x1={226} x2={226} y1={0} y2={VIEW_H} stroke={starInk} strokeWidth={1} strokeDasharray="3 3.5" opacity={0.75} />
                  <Clarinet ink={starInk} night={night} />
                  <Rocket ink={starInk} night={night} font={fontCondensed} />
                </svg>
                <Grain id={uid + "gf"} />
                <div className="lbp-layer lbp-glow" />

                <div className="lbp-at lbp-c" style={{ ...at(22, 23), fontSize: "2.7cqw", display: "flex", alignItems: "center", gap: ".55cqw" }}>
                  <Star size="0.92em" />
                  {tier}
                </div>
                <div className="lbp-at lbp-c lbp-pre" style={{ left: "2.4%", bottom: "6.5%", fontSize: "2.15cqw", lineHeight: 0.98, textShadow: "0 0 .5cqw " + night + ", 0 0 1.2cqw " + night }}>
                  {welcome}
                </div>
                <div className="lbp-at lbp-c lbp-pre" style={{ ...at(256, 22), fontSize: ".8cqw", lineHeight: 1.2 }}>
                  {eyebrow}
                </div>
                <div className="lbp-at lbp-c" style={{ ...at(590, 22), transform: "translateX(-50%)", fontSize: "2.75cqw" }}>
                  {title}
                </div>
                <div className="lbp-at lbp-c" style={{ right: "2.8%", top: (22 / VIEW_H) * 100 + "%", fontSize: "2.75cqw" }}>
                  {date}
                </div>
                <div className="lbp-at lbp-d" style={{ right: "6%", top: "33%", fontSize: "2.35cqw", fontWeight: 400 }}>
                  {words[0]}
                </div>
                <div className="lbp-at lbp-d" style={{ ...at(268, 142), fontSize: "2.35cqw", fontWeight: 400 }}>
                  {words[1]}
                </div>
                <div className="lbp-at lbp-c" style={{ ...at(256, 296), fontSize: ".85cqw" }}>
                  {notes[0]}
                </div>
                <div className="lbp-at lbp-c" style={{ ...at(452, 296), fontSize: ".85cqw" }}>
                  {notes[1]}
                </div>
                <div className="lbp-at lbp-c" style={{ ...at(650, 296), fontSize: ".85cqw" }}>
                  {site}
                </div>
                <div className="lbp-at lbp-c" style={{ right: "2.8%", top: (296 / VIEW_H) * 100 + "%", fontSize: ".85cqw" }}>
                  [{dms}]
                </div>
              </div>
            </div>

            {/* ---------------- back: boarding pass ---------------- */}
            <div className={"lbp-face lbp-back" + (printed ? " lbp-printed" : "") + (torn ? " is-torn" : "")} aria-hidden={front}>
              <div className={"lbp-piece lbp-main" + (torn ? " is-torn" : "")}>
                <Grain id={uid + "gm"} />
                <div className="lbp-layer lbp-foil" />
                <div className="lbp-head">
                  <span className="lbp-c" style={{ fontSize: "1.65cqw" }}>Boarding pass</span>
                  <span className="lbp-c" style={{ fontSize: "2.75cqw" }}>{title}</span>
                  <span className="lbp-c" style={{ fontSize: "2.3cqw" }}>{tier}</span>
                </div>
                <div className="lbp-grid">
                  <div className="lbp-cell">
                    <Field label="Passenger name" value={passenger} size={1.45} d={0.1} />
                  </div>
                  <div className="lbp-cell">
                    <Field label={craftLabel} value={craft} size={1.45} d={0.25} />
                  </div>
                  <div className="lbp-cell">
                    <Field label="Date" value={dateCode} size={1.45} d={0.4} />
                  </div>
                  <div className="lbp-cell lbp-row">
                    <Field label="From" value={from} size={1.3} d={0.55} />
                    <Field label="To" value={to} size={1.3} d={0.65} />
                  </div>
                  <div className="lbp-cell lbp-row" style={{ gap: "1.6cqw" }}>
                    <Field label="Gate" value={gate} size={2.25} d={0.75} />
                    <Field label="Group" value={group} size={2.25} d={0.85} />
                    <Field label="Seat" value={seat} size={2.25} d={0.95} />
                  </div>
                  <div className="lbp-cell">
                    <Field label="Boarding time" value={boardingTime} size={1.45} d={1.05} />
                  </div>
                </div>
                <div className="lbp-foot">
                  <div style={{ minWidth: 0, flex: "0 0 38%" }}>
                    <span className="lbp-l">{siteLabel}</span>
                    <div className="lbp-m lbp-v" style={{ fontSize: "1.4cqw", animationDelay: "1.15s" }}>{site}</div>
                    <div className="lbp-m lbp-v" style={{ fontSize: "1.4cqw", marginTop: ".3cqw", animationDelay: "1.25s" }}>{dec}</div>
                    <span className="lbp-l" style={{ marginTop: ".7cqw", marginBottom: 0, letterSpacing: ".04em" }}>{seq}</span>
                  </div>
                  <div style={{ flex: 1, minWidth: 0, textAlign: "center" }}>
                    <div className="lbp-c" style={{ fontSize: "1.2cqw", marginBottom: ".9cqw" }}>{featuring}</div>
                    <div className="lbp-d" style={{ fontSize: "4.3cqw" }}>{headline}</div>
                  </div>
                </div>
                <div className="lbp-stamp" aria-hidden="true">
                  <span>
                    <span className="lbp-c" style={{ display: "block", fontSize: "2.2cqw", letterSpacing: ".18em" }}>{stamp}</span>
                    <span className="lbp-m" style={{ display: "block", fontSize: ".75cqw", marginTop: ".35cqw" }}>
                      {dateCode} · {gate} · {seat}
                    </span>
                  </span>
                </div>
              </div>
              <button
                ref={stubRef}
                type="button"
                className={"lbp-piece lbp-stub" + (torn ? " is-torn" : "") + (torn && detach ? " is-detached" : "")}
                tabIndex={front ? -1 : 0}
                aria-pressed={torn}
                aria-label={torn ? (lockTorn ? "Stub torn off" : "Reattach the stub") : "Tear off the stub"}
                onPointerDown={stubDown}
                onPointerMove={stubMove}
                onPointerUp={stubUp}
                onPointerCancel={stubUp}
                onClick={stubClick}
              >
                <Grain id={uid + "gs"} />
                <span className="lbp-layer lbp-foil" />
                <span className="lbp-c" style={{ display: "block", fontSize: "1.65cqw", paddingBottom: "1cqw", borderBottom: "1px solid var(--lbp-rule)" }}>
                  Boarding pass
                </span>
                <span className="lbp-sf" style={{ display: "block" }}>
                  <Field label="Passenger name" value={passenger} size={1.25} d={0.3} />
                </span>
                <span className="lbp-sf lbp-row" style={{ display: "flex", gap: "2cqw" }}>
                  <Field label="From" value={from} size={1.2} d={0.45} />
                  <Field label="To" value={to} size={1.2} d={0.55} />
                </span>
                <span className="lbp-sf" style={{ display: "block" }}>
                  <Field label={craftLabel} value={craft} size={1.2} d={0.65} />
                </span>
                <span className="lbp-sf lbp-row" style={{ display: "flex", gap: "1.3cqw" }}>
                  <Field label="Gate" value={gate} size={1.85} d={0.75} />
                  <Field label="Group" value={group} size={1.85} d={0.85} />
                  <Field label="Seat" value={seat} size={1.85} d={0.95} />
                </span>
                <span className="lbp-sf lbp-row" style={{ display: "flex", gap: "1.3cqw" }}>
                  <Field label="Date" value={dateCode} size={1.2} d={1.05} />
                  <Field label="Boarding time" value={boardingTime} size={1.2} d={1.15} />
                </span>
              </button>
              <span className="lbp-hint" aria-hidden="true">Tear here</span>
            </div>
          </div>
        </div>
      </div>

      {showSideSwitch && (
      <div className="mt-5 flex items-center justify-center gap-6" role="group" aria-label="Ticket side">
        {(["front", "back"] as Side[]).map((s, i) => (
          <button
            key={s}
            type="button"
            aria-pressed={side === s}
            onClick={() => show(s)}
            className={
              "group flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.24em] transition-colors " +
              (side === s ? "text-foreground" : "text-muted-foreground hover:text-foreground")
            }
          >
            <span className={"h-px transition-all duration-500 motion-reduce:transition-none " + (side === s ? "w-6 bg-current" : "w-2 bg-current opacity-50")} />
            <span>0{i + 1}</span>
            <span>{sideLabels[i]}</span>
          </button>
        ))}
      </div>
      )}
      <p className="sr-only" aria-live="polite">
        {front
          ? tier + " pass. " + title + ", " + date + ". " + site + ", " + dms + "."
          : "Boarding pass for " + passenger + ", " + from + " to " + to + ". Gate " + gate + ", group " + group + ", seat " + seat + ", " + boardingTime + "." + (torn ? " Stub torn off: " + stamp + "." : "")}
      </p>
    </div>
  )
}
