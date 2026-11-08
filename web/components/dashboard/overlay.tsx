"use client";

import { useEffect, useLayoutEffect, useState, type CSSProperties, type ReactNode, type RefObject } from "react";
import { createPortal } from "react-dom";

/**
 * Popovers render here, inside the themed shell but outside every card. Glass cards
 * use backdrop-filter, which would clip a dropdown and trap `position: fixed`.
 */
export const OVERLAY_ID = "dashboard-overlays";

/** Popovers open only after a user action, so the document always exists when this renders. */
export function Overlay({ children }: { children: ReactNode }) {
  if (typeof document === "undefined") return null;
  return createPortal(children, document.getElementById(OVERLAY_ID) ?? document.body);
}

const useIsoLayoutEffect = typeof window === "undefined" ? useEffect : useLayoutEffect;

/**
 * Fixed position next to `anchor`, kept in place on scroll and resize. Opens upwards
 * when there is more room above, and never leaves the viewport sideways.
 */
export function useAnchoredStyle(
  anchor: RefObject<HTMLElement | null>,
  open: boolean,
  { width, maxHeight = 360, align = "start" }: { width?: number; maxHeight?: number; align?: "start" | "end" } = {},
): CSSProperties {
  const [style, setStyle] = useState<CSSProperties>({ position: "fixed", visibility: "hidden" });
  useIsoLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const el = anchor.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const viewportW = window.innerWidth;
      const viewportH = window.innerHeight;
      const w = Math.min(width ?? Math.max(rect.width, 280), viewportW - 16);
      const preferred = align === "end" ? rect.right - w : rect.left;
      const left = Math.max(8, Math.min(preferred, viewportW - w - 8));
      const below = viewportH - rect.bottom - 12;
      const above = rect.top - 12;
      const up = below < Math.min(maxHeight, 240) && above > below;
      const height = Math.max(160, Math.min(maxHeight, up ? above : below));
      setStyle({
        position: "fixed",
        left,
        width: w,
        maxHeight: height,
        ...(up ? { bottom: viewportH - rect.top + 6 } : { top: rect.bottom + 6 }),
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [anchor, open, width, maxHeight, align]);
  return style;
}

/** Closes on a pointer press outside every given element. */
export function useOutsidePress(refs: RefObject<HTMLElement | null>[], open: boolean, onOutside: () => void) {
  useEffect(() => {
    if (!open) return;
    const onDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (refs.some((ref) => ref.current?.contains(target))) return;
      onOutside();
    };
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, [refs, open, onOutside]);
}

/** Same surface as the glass cards, for floating panels. */
export const POPOVER_SURFACE =
  "z-[60] overflow-auto rounded-2xl border border-line-strong bg-glass-strong text-ink shadow-2xl shadow-black/30 backdrop-blur-2xl";
