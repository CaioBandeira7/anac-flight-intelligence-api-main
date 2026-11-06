"use client";

/**
 * ScrollFlyIn (originally `hero-section-3.tsx`), integrated into
 * ANAC Flight Intelligence.
 *
 * The plane and its motion are the reference's, unchanged:
 *  - tall wrapper (h-[200vh]) + sticky h-screen stage, text in the middle;
 *  - `useScroll({ offset: ["start end", "end start"] })`;
 *  - x: [0.1, 0.8] → [-5·screenWidth, 2.5·screenWidth];
 *  - opacity: [0.1, 0.25, 0.7, 0.8] → [0, 1, 1, 0];
 *  - full-size lane (absolute, top-0 left-0, h-full w-full, items-center),
 *    image at natural size (`w-auto h-auto max-w-none`), above the text (z-20).
 *
 * Fixes required by the integration:
 *  - `window.innerWidth` is no longer read during render (SSR/hydration safe):
 *    screen width lives in a motion value and follows resizes.
 *  - The reference image loads by default; if it fails, a LOCAL top-view jet
 *    is used (no dependency on an external host).
 *  - The stage clips horizontally (`overflow-x: clip`) → no horizontal scrollbar.
 *  - `prefers-reduced-motion`: the plane is shown at rest, no travel.
 *
 * The same math (lib/motion/flight-path.ts) drives the click-triggered
 * takeoff through <FlyingPlane mode="takeoff"/> — one motion system.
 */
import * as React from "react";
import { motion, useReducedMotion, useScroll, useTransform, type MotionValue } from "framer-motion";
import { cn } from "@/lib/utils";
import {
  flightFrame,
  LOCAL_PLANE_SRC,
  REFERENCE_PLANE_URL,
  type FlightMode,
} from "@/lib/motion/flight-path";
import { useViewportMotion } from "@/hooks/use-viewport";

export { LOCAL_PLANE_SRC, REFERENCE_PLANE_URL };

function PlaneImage({
  src,
  alt,
  fallbackSrc,
  width,
}: {
  src: string;
  alt: string;
  fallbackSrc: string;
  width?: MotionValue<number>;
}) {
  const img = (
    // eslint-disable-next-line @next/next/no-img-element -- remote reference artwork with local fallback
    <img
      src={src}
      alt={alt}
      draggable={false}
      decoding="async"
      className={cn("h-auto max-w-none select-none", width ? "w-full" : "w-auto")}
      onError={(e) => {
        if (!e.currentTarget.src.endsWith(fallbackSrc)) e.currentTarget.src = fallbackSrc;
      }}
    />
  );
  return width ? <motion.div style={{ width }}>{img}</motion.div> : img;
}

interface FlyingPlaneProps {
  progress: MotionValue<number>;
  mode: FlightMode;
  imageUrl?: string;
  imageAlt?: string;
  fallbackSrc?: string;
  className?: string;
  /** Faint trailing ghost proportional to speed (cheap motion blur). */
  motionTrail?: boolean;
}

/** A full-size, vertically centred flight lane, translated along x. */
export function FlyingPlane({
  progress,
  mode,
  imageUrl = REFERENCE_PLANE_URL,
  imageAlt = "",
  fallbackSrc = LOCAL_PLANE_SRC,
  className,
  motionTrail = false,
}: FlyingPlaneProps) {
  const { width, height } = useViewportMotion();
  const frame = useTransform(() =>
    flightFrame(progress.get(), { width: width.get(), height: height.get() }, mode),
  );
  const x = useTransform(frame, (f) => f.x);
  const scale = useTransform(frame, (f) => f.scale);
  const opacity = useTransform(frame, (f) => f.opacity);
  const planeWidth = useTransform(frame, (f) => f.planeWidth);
  const trailX = useTransform(frame, (f) => -f.blur * 14);
  const trailOpacity = useTransform(frame, (f) => Math.min(0.35, f.blur * 0.14));
  const sized = mode === "takeoff" ? planeWidth : undefined;

  return (
    <motion.div
      aria-hidden={imageAlt ? undefined : true}
      style={{ x, opacity }}
      className={cn(
        "pointer-events-none absolute left-0 top-0 z-20 flex h-full w-full items-center will-change-transform",
        className,
      )}
    >
      <motion.div className="relative" style={{ scale }}>
        {motionTrail && (
          <motion.div className="absolute inset-0" style={{ x: trailX, opacity: trailOpacity }}>
            <PlaneImage src={imageUrl} alt="" fallbackSrc={fallbackSrc} width={sized} />
          </motion.div>
        )}
        <PlaneImage src={imageUrl} alt={imageAlt} fallbackSrc={fallbackSrc} width={sized} />
      </motion.div>
    </motion.div>
  );
}

interface ScrollFlyInProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  imageUrl?: string;
  imageAlt?: string;
  fallbackSrc?: string;
  stageClassName?: string;
}

const ScrollFlyIn = React.forwardRef<HTMLDivElement, ScrollFlyInProps>(
  (
    {
      children,
      imageUrl = REFERENCE_PLANE_URL,
      imageAlt = "Animated image",
      fallbackSrc = LOCAL_PLANE_SRC,
      className,
      stageClassName,
      ...props
    },
    ref,
  ) => {
    const targetRef = React.useRef<HTMLDivElement>(null);
    React.useImperativeHandle(ref, () => targetRef.current as HTMLDivElement);
    const reduceMotion = useReducedMotion();

    const { scrollYProgress } = useScroll({
      target: targetRef,
      offset: ["start end", "end start"],
    });

    return (
      <div ref={targetRef} className={cn("relative h-[200vh]", className)} {...props}>
        <div
          className={cn(
            "sticky top-0 flex h-screen items-center justify-center [overflow-x:clip]",
            stageClassName,
          )}
        >
          {/* Static text content */}
          <div className="z-10 w-full text-center">{children}</div>

          {/* Animated image (plane) */}
          {reduceMotion ? (
            <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-[6%] z-20 flex justify-center opacity-90">
              <PlaneImage src={imageUrl} alt="" fallbackSrc={fallbackSrc} />
            </div>
          ) : (
            <FlyingPlane
              progress={scrollYProgress}
              mode="scroll"
              imageUrl={imageUrl}
              imageAlt={imageAlt}
              fallbackSrc={fallbackSrc}
            />
          )}
        </div>
      </div>
    );
  },
);

ScrollFlyIn.displayName = "ScrollFlyIn";

export { ScrollFlyIn };
