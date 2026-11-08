import type { Metadata } from "next";
import { AnalystView } from "@/components/dashboard/analyst";

export const metadata: Metadata = { title: "AI Aviation Analyst" };

export default function Page() {
  return <AnalystView />;
}
