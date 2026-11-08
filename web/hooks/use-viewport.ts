"use client";

import { useEffect, useLayoutEffect } from "react";
import { useMotionValue, type MotionValue } from "framer-motion";

const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

/** SSR-safe defaults; replaced with the real size before first paint on the client. */
export const DEFAULT_VIEWPORT = { width: 1440, height: 900 };

/**
 * Viewport size as motion values: resizes update transforms without
 * re-rendering React trees. Never touches `window` during render.
 */
export function useViewportMotion(): { width: MotionValue<number>; height: MotionValue<number> } {
  const width = useMotionValue(DEFAULT_VIEWPORT.width);
  const height = useMotionValue(DEFAULT_VIEWPORT.height);

  useIsomorphicLayoutEffect(() => {
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        // clientWidth excludes the vertical scrollbar → no horizontal overflow.
        width.set(document.documentElement.clientWidth || window.innerWidth);
        height.set(window.innerHeight);
      });
    };
    width.set(document.documentElement.clientWidth || window.innerWidth);
    height.set(window.innerHeight);
    window.addEventListener("resize", update, { passive: true });
    window.addEventListener("orientationchange", update);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", update);
      window.removeEventListener("orientationchange", update);
    };
  }, [width, height]);

  return { width, height };
}
