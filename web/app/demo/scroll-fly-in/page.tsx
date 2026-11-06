import type { Metadata } from "next";
import ScrollFlyInDemo from "@/components/demo/scroll-fly-in-demo";

export const metadata: Metadata = { title: "ScrollFlyIn demo" };

export default function Page() {
  return (
    <>
      <div className="grid h-screen place-items-center text-muted">Scroll ↓</div>
      <ScrollFlyInDemo />
      <div className="h-screen" />
    </>
  );
}
