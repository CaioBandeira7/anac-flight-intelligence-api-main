import Link from "next/link";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center bg-navy px-6 text-center">
      <div>
        <p className="font-mono text-xs uppercase tracking-[0.3em] text-cyan">404 · Off the flight plan</p>
        <h1 className="mt-4 text-3xl font-semibold text-ink">This page isn&apos;t on the radar.</h1>
        <Link href="/" className="mt-8 inline-block rounded-full bg-white px-5 py-2.5 text-sm font-medium text-navy">
          Return home
        </Link>
      </div>
    </main>
  );
}
