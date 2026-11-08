import type { Metadata } from "next";
import { AirportsView } from "@/components/dashboard/analytics-views";

export const metadata: Metadata = { title: "Airports Intelligence" };

export default function Page() {
  return <AirportsView />;
}
