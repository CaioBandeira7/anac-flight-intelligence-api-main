import { ScrollFlyIn } from "@/components/ui/hero-section-3";

/** Reference demo for the ScrollFlyIn component (also rendered at /demo/scroll-fly-in). */
export default function ScrollFlyInDemo() {
  return (
    <div className="w-full bg-background text-foreground">
      <ScrollFlyIn
        imageUrl="/images/jet-reference.webp"
        imageAlt="Top view of a private jet flying across the screen"
      >
        <div className="mx-auto max-w-3xl px-4 text-center">
          <p className="text-md font-semibold uppercase tracking-widest text-muted-foreground">Welcome to Airvoir</p>
          <h2 className="mt-2 text-5xl font-bold leading-tight md:text-7xl">Where journeys become unforgettable</h2>
        </div>
      </ScrollFlyIn>
    </div>
  );
}
