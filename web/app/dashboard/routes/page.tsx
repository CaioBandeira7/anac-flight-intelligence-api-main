import type { Metadata } from "next";
import { RoutesView } from "@/components/dashboard/analytics-views";

export const metadata: Metadata = { title: "Routes Explorer" };

export default function Page() {
  return <RoutesView />;
}
