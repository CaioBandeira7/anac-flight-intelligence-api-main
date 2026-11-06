import type { Metadata } from "next";
import { ModulePlaceholder } from "@/components/dashboard/module-placeholder";

export const metadata: Metadata = { title: "Airlines Analytics" };

export default function Page() {
  return <ModulePlaceholder href="/dashboard/airlines" />;
}
