import type { Metadata } from "next";
import { AirlinesView } from "@/components/dashboard/analytics-views";

export const metadata: Metadata = { title: "Airlines Analytics" };

export default function Page() {
  return <AirlinesView />;
}
