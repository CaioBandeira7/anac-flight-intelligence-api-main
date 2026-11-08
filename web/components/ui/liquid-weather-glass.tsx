"use client";

/**
 * LiquidGlassCard — integrated from the provided `liquid-weather-glass.tsx`.
 *
 * Kept from the original: the four-layer build (bend / face / edge / content),
 * the blur, shadow and glow scales, the SVG `glass-blur` displacement filter,
 * drag and expand behaviour with the same motion parameters.
 *
 * Integration changes:
 *  - Fully typed (no `@ts-nocheck`).
 *  - Uses `framer-motion`, already a dependency (`motion/react` is the same
 *    library under its new package name), so no second animation runtime.
 *  - `draggable` defaults to `false`: analytic panels must not move by accident.
 *  - `distortion` (default true, original look) lets dense dashboards skip the
 *    SVG displacement filter, which is expensive over large surfaces.
 *  - The filter is defined once per page (not once per card) to avoid duplicate ids.
 */
import React, { useState, type MouseEvent } from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { cn } from "@/lib/utils";

type Intensity = "none" | "xs" | "sm" | "md" | "lg" | "xl" | "2xl";

export interface LiquidGlassCardProps extends Omit<HTMLMotionProps<"div">, "children" | "ref"> {
  children: React.ReactNode;
  className?: string;
  draggable?: boolean;
  expandable?: boolean;
  width?: string;
  height?: string;
  expandedWidth?: string;
  expandedHeight?: string;
  blurIntensity?: "sm" | "md" | "lg" | "xl";
  shadowIntensity?: Intensity;
  borderRadius?: string;
  glowIntensity?: Intensity;
  /** Apply the SVG displacement ("liquid bend") filter to the blur layer. */
  distortion?: boolean;
  /** Render as another element (e.g. "section") when not draggable/expandable. */
  as?: "div" | "section" | "article" | "aside" | "header" | "nav";
}

const blurClasses = {
  sm: "backdrop-blur-sm",
  md: "backdrop-blur-md",
  lg: "backdrop-blur-lg",
  xl: "backdrop-blur-xl",
} as const;

const shadowStyles: Record<Intensity, string> = {
  none: "inset 0 0 0 0 rgba(255, 255, 255, 0)",
  xs: "inset 1px 1px 1px 0 rgba(255, 255, 255, 0.3), inset -1px -1px 1px 0 rgba(255, 255, 255, 0.3)",
  sm: "inset 2px 2px 2px 0 rgba(255, 255, 255, 0.35), inset -2px -2px 2px 0 rgba(255, 255, 255, 0.35)",
  md: "inset 3px 3px 3px 0 rgba(255, 255, 255, 0.45), inset -3px -3px 3px 0 rgba(255, 255, 255, 0.45)",
  lg: "inset 4px 4px 4px 0 rgba(255, 255, 255, 0.5), inset -4px -4px 4px 0 rgba(255, 255, 255, 0.5)",
  xl: "inset 6px 6px 6px 0 rgba(255, 255, 255, 0.55), inset -6px -6px 6px 0 rgba(255, 255, 255, 0.55)",
  "2xl": "inset 8px 8px 8px 0 rgba(255, 255, 255, 0.6), inset -8px -8px 8px 0 rgba(255, 255, 255, 0.6)",
};

const glowStyles: Record<Intensity, string> = {
  none: "0 4px 4px rgba(0, 0, 0, 0.05), 0 0 12px rgba(0, 0, 0, 0.05)",
  xs: "0 4px 4px rgba(0, 0, 0, 0.15), 0 0 12px rgba(0, 0, 0, 0.08), 0 0 16px rgba(255, 255, 255, 0.05)",
  sm: "0 4px 4px rgba(0, 0, 0, 0.15), 0 0 12px rgba(0, 0, 0, 0.08), 0 0 24px rgba(255, 255, 255, 0.1)",
  md: "0 4px 4px rgba(0, 0, 0, 0.15), 0 0 12px rgba(0, 0, 0, 0.08), 0 0 32px rgba(255, 255, 255, 0.15)",
  lg: "0 4px 4px rgba(0, 0, 0, 0.15), 0 0 12px rgba(0, 0, 0, 0.08), 0 0 40px rgba(255, 255, 255, 0.2)",
  xl: "0 4px 4px rgba(0, 0, 0, 0.15), 0 0 12px rgba(0, 0, 0, 0.08), 0 0 48px rgba(255, 255, 255, 0.25)",
  "2xl": "0 4px 4px rgba(0, 0, 0, 0.15), 0 0 12px rgba(0, 0, 0, 0.08), 0 0 60px rgba(255, 255, 255, 0.3)",
};

/** Mount once (e.g. in a layout) for every card that uses `distortion`. */
export function GlassFilterDefs() {
  return (
    <svg className="hidden" aria-hidden>
      <defs>
        <filter id="glass-blur" x="0" y="0" width="100%" height="100%" filterUnits="objectBoundingBox">
          <feTurbulence type="fractalNoise" baseFrequency="0.003 0.007" numOctaves={1} result="turbulence" />
          <feDisplacementMap in="SourceGraphic" in2="turbulence" scale={200} xChannelSelector="R" yChannelSelector="G" />
        </filter>
      </defs>
    </svg>
  );
}

export const LiquidGlassCard = ({
  children,
  className = "",
  draggable = false,
  expandable = false,
  width,
  height,
  expandedWidth,
  expandedHeight,
  blurIntensity = "xl",
  borderRadius = "32px",
  glowIntensity = "sm",
  shadowIntensity = "md",
  distortion = true,
  as = "div",
  style,
  ...props
}: LiquidGlassCardProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleToggleExpansion = (e: MouseEvent<HTMLDivElement>) => {
    if (!expandable) return;
    // Don't toggle if clicking on interactive elements
    if ((e.target as HTMLElement).closest("a, button, input, select, textarea")) return;
    setIsExpanded((v) => !v);
  };

  const containerVariants = expandable
    ? {
        collapsed: {
          width: width || "auto",
          height: height || "auto",
          transition: { duration: 0.4, ease: [0.5, 1.5, 0.5, 1] as const },
        },
        expanded: {
          width: expandedWidth || "auto",
          height: expandedHeight || "auto",
          transition: { duration: 0.4, ease: [0.5, 1.5, 0.5, 1] as const },
        },
      }
    : undefined;

  const interactive = draggable || expandable;
  const layerStyle = { borderRadius };
  const rootStyle = {
    borderRadius,
    ...(width && !expandable ? { width } : {}),
    ...(height && !expandable ? { height } : {}),
  };

  const layers = (
    <>
      {/* Bend Layer (Backdrop blur with distortion) */}
      <div
        className={cn("pointer-events-none absolute inset-0 z-0", blurClasses[blurIntensity])}
        style={{ ...layerStyle, ...(distortion ? { filter: "url(#glass-blur)" } : {}) }}
      />
      {/* Face Layer (Main shadow and glow) */}
      <div className="pointer-events-none absolute inset-0 z-10" style={{ ...layerStyle, boxShadow: glowStyles[glowIntensity] }} />
      {/* Edge Layer (Inner highlights) */}
      <div className="pointer-events-none absolute inset-0 z-20" style={{ ...layerStyle, boxShadow: shadowStyles[shadowIntensity] }} />
      {/* Content */}
      <div className="relative z-30">{children}</div>
    </>
  );

  if (!interactive) {
    const Tag = as;
    return (
      <Tag
        className={cn("relative", className)}
        style={{ ...rootStyle, ...(style as React.CSSProperties) }}
        {...(props as React.HTMLAttributes<HTMLElement>)}
      >
        {layers}
      </Tag>
    );
  }

  return (
    <motion.div
      className={cn("relative", draggable && "cursor-grab active:cursor-grabbing", expandable && "cursor-pointer", className)}
      style={{ ...rootStyle, ...style }}
      variants={containerVariants}
      animate={expandable ? (isExpanded ? "expanded" : "collapsed") : undefined}
      onClick={expandable ? handleToggleExpansion : undefined}
      drag={draggable}
      dragConstraints={draggable ? { left: 0, right: 0, top: 0, bottom: 0 } : undefined}
      dragElastic={draggable ? 0.3 : undefined}
      dragTransition={draggable ? { bounceStiffness: 300, bounceDamping: 10, power: 0.3 } : undefined}
      whileDrag={draggable ? { scale: 1.02 } : undefined}
      whileHover={{ scale: 1.01 }}
      whileTap={{ scale: 0.98 }}
      {...props}
    >
      {layers}
    </motion.div>
  );
};

export default LiquidGlassCard;
