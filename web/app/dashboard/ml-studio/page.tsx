import type { Metadata } from "next";
import { MlStudioView } from "@/components/dashboard/data-views";

export const metadata: Metadata = { title: "ML Studio" };

export default function Page() {
  return <MlStudioView />;
}
