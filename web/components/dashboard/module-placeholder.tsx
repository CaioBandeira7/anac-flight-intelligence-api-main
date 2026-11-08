import Link from "next/link";
import { ArrowLeft, Check } from "lucide-react";
import { navByHref } from "./nav";
import { Card, PageHeader } from "./ui";

export function ModulePlaceholder({ href }: { href: string }) {
  const item = navByHref(href);
  if (!item) return null;
  return (
    <>
      <PageHeader title={item.label} description={item.description} />
      <Card className="relative overflow-hidden">
        <div className="hud-grid pointer-events-none absolute inset-0 opacity-60" aria-hidden />
        <div className="relative max-w-xl py-6">
          <span className="grid size-12 place-items-center rounded-2xl bg-blue/15 text-cyan">
            <item.icon className="size-6" strokeWidth={1.5} aria-hidden />
          </span>
          <h2 className="mt-5 text-xl font-semibold tracking-[-0.02em] text-ink">Scheduled for the next delivery</h2>
          <p className="mt-2 text-[14.5px] text-muted">
            This module is wired into navigation and the data layer. Its views are built in the next iteration.
          </p>
          {item.planned && (
            <ul className="mt-6 space-y-2.5">
              {item.planned.map((p) => (
                <li key={p} className="flex items-center gap-3 text-[14px] text-ink-2">
                  <Check className="size-4 text-cyan" aria-hidden /> {p}
                </li>
              ))}
            </ul>
          )}
          <Link href="/dashboard" className="mt-8 inline-flex items-center gap-2 text-sm text-cyan hover:underline">
            <ArrowLeft className="size-4" aria-hidden /> Back to Overview
          </Link>
        </div>
      </Card>
    </>
  );
}
