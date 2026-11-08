import type { Metadata } from "next";
import { MethodologyView } from "@/components/dashboard/data-views";

export const metadata: Metadata = { title: "Data & Methodology" };

export default function Page() {
  return <MethodologyView />;
}
