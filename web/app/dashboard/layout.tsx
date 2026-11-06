import type { Metadata } from "next";
import { DataProviderRoot } from "@/components/data-provider";
import { DashboardShell } from "@/components/dashboard/shell";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  return (
    <DataProviderRoot>
      <DashboardShell>{children}</DashboardShell>
    </DataProviderRoot>
  );
}
