import type { Metadata } from "next";
import { DataProviderRoot } from "@/components/data-provider";
import { DashboardShell } from "@/components/dashboard/shell";
import { ThemeProvider } from "@/components/theme-provider";

export const metadata: Metadata = {
  title: "Dashboard",
};

export default function DashboardLayout({ children }: LayoutProps<"/dashboard">) {
  return (
    <ThemeProvider>
      <DataProviderRoot>
        <DashboardShell>{children}</DashboardShell>
      </DataProviderRoot>
    </ThemeProvider>
  );
}
