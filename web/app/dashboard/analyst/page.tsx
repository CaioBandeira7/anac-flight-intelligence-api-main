import type { Metadata } from "next";
import { AnalystView } from "@/components/dashboard/data-views";

export const metadata: Metadata = { title: "AI Aviation Analyst" };

export default function Page() {
  return <AnalystView />;
}
