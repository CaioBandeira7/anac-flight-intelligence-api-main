import type { Metadata } from "next";
import { RoutesView } from "@/components/dashboard/data-views";

export const metadata: Metadata = { title: "Routes Explorer" };

export default function Page() {
  return <RoutesView />;
}
