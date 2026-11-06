"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { createDataProvider, type FlightDataProvider } from "@/lib/data";

const DataContext = createContext<FlightDataProvider | null>(null);

export function DataProviderRoot({ children, provider }: { children: ReactNode; provider?: FlightDataProvider }) {
  const [value] = useState(() => provider ?? createDataProvider());
  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useDataProvider(): FlightDataProvider {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error("useDataProvider must be used inside <DataProviderRoot>");
  return ctx;
}
