import type { Metadata } from "next";
import { AirportsView } from "@/components/dashboard/data-views";

export const metadata: Metadata = { title: "Airports Intelligence" };

export default function Page() {
  return <AirportsView />;
}
