"use client";

import { CloudShader } from "@/components/ui/cloud-shader";
import { SKY, useTheme } from "@/components/theme-provider";

/** One full-screen CloudShader behind the whole platform. Never captures input. */
export function SkyBackground() {
  const { theme } = useTheme();
  const sky = SKY[theme];
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0">
      <CloudShader className="h-full min-h-0 w-full" count={6} maxDpr={1.25} {...sky} />
      {/* Gentle veil: keeps the sky calm behind data without hiding it */}
      <div className="absolute inset-0 bg-[var(--sky-veil)]" />
    </div>
  );
}
