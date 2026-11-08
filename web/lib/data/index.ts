import { ApiDataProvider } from "./api-provider";
import type { FlightDataProvider } from "./contracts";
import { MockDataProvider } from "./mock-provider";

export * from "./contracts";
export * from "./periods";
export * from "./search";
export * from "./definitions";
export { MockDataProvider } from "./mock-provider";
export { ApiDataProvider } from "./api-provider";

export interface ProviderEnv {
  NEXT_PUBLIC_DATA_SOURCE?: string;
  NEXT_PUBLIC_API_URL?: string;
}

/** Picks the provider from env. Defaults to DEMO data; never silently mixes sources. */
export function createDataProvider(
  env: ProviderEnv = {
    NEXT_PUBLIC_DATA_SOURCE: process.env.NEXT_PUBLIC_DATA_SOURCE,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
): FlightDataProvider {
  const source = (env.NEXT_PUBLIC_DATA_SOURCE ?? "mock").toLowerCase();
  if (source === "api") {
    return new ApiDataProvider({ baseUrl: env.NEXT_PUBLIC_API_URL || "http://localhost:8000" });
  }
  return new MockDataProvider();
}
