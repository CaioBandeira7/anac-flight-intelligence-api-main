import { describe, expect, it } from "vitest";
import { flightFrame, planeProgressFromTimeline } from "@/lib/motion/flight-path";

const viewports = [
  { width: 375, height: 812 },
  { width: 1440, height: 900 },
  { width: 2560, height: 1080 },
];

describe("flightFrame — scroll mode (reference ScrollFlyIn)", () => {
  it.each(viewports)("uses the reference x range [-5w, 2.5w] over [0.1, 0.8] at %o", (vp) => {
    expect(flightFrame(0, vp, "scroll").x).toBe(-5 * vp.width);
    expect(flightFrame(0.1, vp, "scroll").x).toBe(-5 * vp.width);
    expect(flightFrame(0.8, vp, "scroll").x).toBe(2.5 * vp.width);
    expect(flightFrame(0.45, vp, "scroll").x).toBeCloseTo(-1.25 * vp.width);
  });

  it("keeps the reference opacity keyframes [0.1,0.25,0.7,0.8] → [0,1,1,0]", () => {
    const vp = viewports[1];
    expect(flightFrame(0.05, vp, "scroll").opacity).toBe(0);
    expect(flightFrame(0.1, vp, "scroll").opacity).toBe(0);
    expect(flightFrame(0.25, vp, "scroll").opacity).toBe(1);
    expect(flightFrame(0.5, vp, "scroll").opacity).toBe(1);
    expect(flightFrame(0.7, vp, "scroll").opacity).toBe(1);
    expect(flightFrame(0.8, vp, "scroll").opacity).toBe(0);
  });

  it("is a straight pass at natural size", () => {
    const f = flightFrame(0.5, viewports[1], "scroll");
    expect(f.scale).toBe(1);
    expect(f.planeWidth).toBe(0);
  });

  it("never yields NaN and clamps out-of-range progress", () => {
    for (const p of [-1, 0, 0.33, 1, 2]) {
      const f = flightFrame(p, viewports[0], "scroll");
      Object.values(f).forEach((v) => expect(Number.isFinite(v)).toBe(true));
    }
  });
});

describe("flightFrame — takeoff mode", () => {
  it.each(viewports)("crosses left → right, starting and ending off-screen at %o", (vp) => {
    let lastX = -Infinity;
    for (let i = 0; i <= 20; i++) {
      const f = flightFrame(i / 20, vp, "takeoff");
      expect(f.x).toBeGreaterThanOrEqual(lastX);
      lastX = f.x;
    }
    const start = flightFrame(0, vp, "takeoff");
    const end = flightFrame(1, vp, "takeoff");
    expect(start.x + start.planeWidth * start.scale).toBeLessThanOrEqual(0);
    expect(end.x - (end.planeWidth * (end.scale - 1)) / 2).toBeGreaterThanOrEqual(vp.width * 0.99);
  });

  it("adds depth with a subtle scale and light blur only", () => {
    const vp = viewports[1];
    expect(flightFrame(1, vp, "takeoff").scale).toBeGreaterThan(flightFrame(0, vp, "takeoff").scale);
    for (let i = 0; i <= 10; i++) expect(flightFrame(i / 10, vp, "takeoff").blur).toBeLessThanOrEqual(2.2);
  });

  it("maps the global timeline to plane progress", () => {
    expect(planeProgressFromTimeline(0)).toBe(0);
    expect(planeProgressFromTimeline(1)).toBe(1);
  });
});
