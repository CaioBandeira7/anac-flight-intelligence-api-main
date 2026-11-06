import { AlertTriangle, Inbox, RotateCw } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { LiquidGlassCard } from "@/components/ui/liquid-weather-glass";

export function DemoBadge({ className }: { className?: string }) {
  return (
    <span
      title="Demonstration data — not real ANAC figures"
      className={cn(
        "inline-flex items-center rounded-md border border-demo/35 bg-demo/10 px-1.5 py-0.5 font-mono text-[10px] font-medium uppercase tracking-[0.14em] text-demo",
        className,
      )}
    >
      Demo
    </span>
  );
}

export function Card({
  title,
  subtitle,
  action,
  children,
  className,
  demo,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  demo?: boolean;
}) {
  return (
    <LiquidGlassCard
      as="section"
      draggable={false}
      distortion={false}
      blurIntensity="xl"
      borderRadius="20px"
      shadowIntensity="xs"
      glowIntensity="none"
      className={cn("min-w-0 border border-line bg-glass p-5 sm:p-6", className)}
    >
      {(title || action) && (
        <header className="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 text-[15px] font-semibold tracking-[-0.01em] text-ink">
              {title}
              {demo && <DemoBadge />}
            </h2>
            {subtitle && <p className="mt-1 text-[13px] text-muted">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </LiquidGlassCard>
  );
}

export function PageHeader({ title, description, meta }: { title: string; description?: string; meta?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-[clamp(1.6rem,2.6vw,2.15rem)] font-semibold tracking-[-0.03em] text-ink">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-[14.5px] text-muted">{description}</p>}
      </div>
      {meta}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("skeleton rounded-lg", className)} />;
}

export function ErrorState({
  error,
  onRetry,
  hint = "Check that the backend is running, then try again.",
}: {
  error: Error;
  onRetry: () => void;
  hint?: string;
}) {
  return (
    <div role="alert" className="flex flex-col items-start gap-4 rounded-2xl border border-danger/30 bg-glass p-6 backdrop-blur-xl">
      <div className="flex items-center gap-3 text-ink">
        <AlertTriangle className="size-5 text-danger" aria-hidden />
        <p className="font-medium">Couldn&apos;t load this data</p>
      </div>
      <p className="text-sm text-muted">{error.message.replace(/\.$/, "")}. {hint}</p>
      <Button variant="secondary" size="sm" onClick={onRetry}>
        <RotateCw aria-hidden /> Retry
      </Button>
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-dashed border-line-strong bg-glass px-4 py-6 text-sm text-muted backdrop-blur-xl">
      <Inbox className="size-4 shrink-0" aria-hidden /> {message}
    </div>
  );
}

export function DataTable({
  caption,
  columns,
  rows,
  alignRight = [],
}: {
  caption: string;
  columns: string[];
  rows: string[][];
  alignRight?: number[];
}) {
  return (
    <div className="scrollbar-thin max-h-[520px] overflow-auto rounded-xl border border-line bg-glass-strong backdrop-blur-xl">
      <table className="w-full text-left text-[13px]">
        <caption className="sr-only">{caption}</caption>
        <thead className="sticky top-0 bg-surface text-xs text-muted">
          <tr>
            {columns.map((column, index) => (
              <th key={column} scope="col" className={cn("px-3 py-2.5 font-medium", alignRight.includes(index) && "text-right")}>
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, index) => (
                <td key={index} className={cn("px-3 py-2 text-ink-2", alignRight.includes(index) && "text-right tabular-nums")}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
