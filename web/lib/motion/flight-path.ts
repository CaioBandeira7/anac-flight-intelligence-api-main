/**
 * Single source of truth for how the airliner moves across the screen.
 *
 * Both experiences — the scroll-driven ScrollFlyIn and the click-driven
 * takeoff — feed a normalized progress value (0 → 1) into `flightFrame`.
 * There is one motion system; only the driver of `progress` changes.
 */
import { clamp, lerp, progressIn, smoothstep } from "@/lib/utils";

export type FlightMode = "scroll" | "takeoff";

export interface Viewport {
  width: number;
  height: number;
}

export interface FlightFrame {
  /** translateX in px of a full-width, vertically centred flight lane */
  x: number;
  scale: number;
  opacity: number;
  /** horizontal motion blur in px (rendered as a trailing ghost, no filter) */
  blur: number;
  /** rendered plane width in px; 0 = the image's natural size (reference behaviour) */
  planeWidth: number;
}

/** Natural size of the reference jet (/images/jet-reference.webp). */
export const PLANE_NATURAL_WIDTH = 2000;
export const PLANE_ASPECT = 2000 / 1157;

/** Reference artwork (top-view jet), served locally, and a vector fallback. */
export const REFERENCE_PLANE_URL = "/images/jet-reference.webp";
export const LOCAL_PLANE_SRC = "/images/jet-topview.svg";

export function takeoffPlaneWidth() {
  // Same natural size as the scroll pass, so both flights read as one plane.
  return PLANE_NATURAL_WIDTH;
}

export function flightFrame(progress: number, vp: Viewport, mode: FlightMode): FlightFrame {
  const p = clamp(progress);

  if (mode === "scroll") {
    // Exactly the reference ScrollFlyIn:
    //   x       = useTransform(p, [0.1, 0.8], [-5·screenWidth, 2.5·screenWidth])
    //   opacity = useTransform(p, [0.1, 0.25, 0.7, 0.8], [0, 1, 1, 0])
    // Straight horizontal pass, vertically centred, image at natural size.
    const x = lerp(-5 * vp.width, 2.5 * vp.width, progressIn(p, 0.1, 0.8));
    const opacity =
      p < 0.1 ? 0 : p < 0.25 ? progressIn(p, 0.1, 0.25) : p <= 0.7 ? 1 : 1 - progressIn(p, 0.7, 0.8);
    return { x, scale: 1, opacity, blur: 0, planeWidth: 0 };
  }

  // Takeoff: the same straight, centred pass, compressed into the click timeline.
  // A slight scale-up gives depth; no rotation (top view).
  const w = takeoffPlaneWidth();
  const t = 0.5 - Math.cos(Math.PI * p) / 2; // easeInOutSine
  const x = lerp(-w * 1.05, vp.width + w * 0.1, t);
  const scale = lerp(0.92, 1.12, smoothstep(0, 1, p));
  const opacity = smoothstep(0, 0.06, p);
  const blur = Math.max(0, Math.sin(Math.PI * p) * 2.2 - 0.4);
  return { x, scale, opacity, blur, planeWidth: w };
}

/**
 * Global takeoff timeline (0 → 1). Every layer of the scene derives its state
 * from this single value, so the transition is one continuous sequence.
 */
export const TAKEOFF_TIMELINE = {
  durationMs: 3400,
  reducedDurationMs: 450,
  text: [0, 0.14] as const, // hero copy fades out
  plane: [0.06, 0.84] as const, // airliner crosses
  clouds: [0, 0.9] as const, // clouds accelerate / camera climbs
  darken: [0.42, 0.9] as const, // atmosphere → navy
  hud: [0.66, 0.96] as const, // Flight Intelligence UI appears
};

export const planeProgressFromTimeline = (t: number) =>
  progressIn(t, TAKEOFF_TIMELINE.plane[0], TAKEOFF_TIMELINE.plane[1]);

export const ARRIVAL_KEY = "fi:arrival";
export const DASHBOARD_HREF = "/dashboard";
