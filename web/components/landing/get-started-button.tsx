"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";

interface Props {
  onLaunch: () => void;
  label?: string;
  disabled?: boolean;
  className?: string;
  tone?: "sky" | "night";
}

/**
 * Glass pill with a travelling sheen, magnetic arrow and an immediate
 * press response (ring pulse) the instant it is activated.
 */
export function GetStartedButton({ onLaunch, label = "Get Started", disabled, className, tone = "sky" }: Props) {
  const [pressed, setPressed] = useState(false);

  return (
    <motion.button
      type="button"
      disabled={disabled}
      onClick={() => {
        setPressed(true);
        onLaunch();
      }}
      whileHover={disabled ? undefined : { scale: 1.035 }}
      whileTap={{ scale: 0.965 }}
      transition={{ type: "spring", stiffness: 420, damping: 26 }}
      aria-describedby="launch-hint"
      className={cn(
        "group relative isolate inline-flex h-14 items-center gap-3 overflow-hidden rounded-full pl-8 pr-3 text-[15px] font-medium tracking-[0.01em]",
        "outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent",
        tone === "sky"
          ? "bg-white/85 text-[#0b1f3f] shadow-[0_10px_40px_-8px_rgba(13,35,71,0.45),inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-md focus-visible:ring-white"
          : "bg-white text-navy shadow-[0_10px_50px_-10px_rgba(34,211,238,0.55)] focus-visible:ring-cyan",
        "transition-[background-color,box-shadow] duration-300 hover:bg-white hover:shadow-[0_18px_60px_-10px_rgba(13,35,71,0.55),inset_0_1px_0_rgba(255,255,255,1)]",
        "disabled:cursor-default",
        className,
      )}
    >
      {/* travelling sheen */}
      <span
        aria-hidden
        className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 -skew-x-12 bg-gradient-to-r from-transparent via-white/90 to-transparent opacity-0 transition-[transform,opacity] duration-700 ease-[var(--ease-out-expo)] group-hover:translate-x-[320%] group-hover:opacity-100"
      />
      <span className="relative">{label}</span>
      <span
        aria-hidden
        className="relative grid size-9 place-items-center rounded-full bg-[#0b1f3f] text-white transition-transform duration-300 ease-[var(--ease-out-expo)] group-hover:translate-x-0.5"
      >
        <ArrowRight className="size-4 transition-transform duration-300 ease-[var(--ease-out-expo)] group-hover:translate-x-0.5" />
      </span>
      {/* press pulse */}
      {pressed && (
        <motion.span
          aria-hidden
          className="pointer-events-none absolute inset-0 rounded-full ring-2 ring-white"
          initial={{ opacity: 0.9, scale: 1 }}
          animate={{ opacity: 0, scale: 1.35 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        />
      )}
    </motion.button>
  );
}
