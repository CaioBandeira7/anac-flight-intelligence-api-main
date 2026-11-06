import { describe, expect, it, vi } from "vitest";
import { ApiDataProvider, createDataProvider, MockDataProvider } from "@/lib/data";
import { normalise } from "@/lib/data/api-provider";

const fixed = () => new Date("2026-01-01T00:00:00Z");

describe("MockDataProvider", () => {
  const p = new MockDataProvider({ latencyMs: 0, now: fixed });

  it("flags every response as DEMO", async () => {
    const all = await Promise.all([p.health(), p.getOverview(), p.getAirports(), p.getRoutes(), p.getModels(), p.getDatasets()]);
    for (const r of all) {
      expect(r.meta.source).toBe("DEMO");
      expect(r.meta.isDemo).toBe(true);
    }
  });

  it("never invents ML performance metrics", async () => {
    const { data } = await p.getModels();
    expect(data.length).toBeGreaterThan(0);
    for (const m of data) {
      expect(m.metrics).toBeNull();
      expect(m.status).toBe("not_trained");
      expect(m.lastTrainedAt).toBeNull();
    }
  });

  it("is deterministic for the same seed", async () => {
    const a = await new MockDataProvider({ latencyMs: 0, now: fixed }).getOverview();
    const b = await new MockDataProvider({ latencyMs: 0, now: fixed }).getOverview();
    expect(a).toEqual(b);
  });

  it("returns 24 ordered months and sorted rankings", async () => {
    const { data } = await p.getOverview();
    expect(data.monthly).toHaveLength(24);
    expect([...data.monthly.map((m) => m.month)].sort()).toEqual(data.monthly.map((m) => m.month));
    const pax = data.topRoutes.map((r) => r.passengers);
    expect([...pax].sort((x, y) => y - x)).toEqual(pax);
  });
});

describe("createDataProvider", () => {
  it("defaults to DEMO data", () => {
    expect(createDataProvider({}).kind).toBe("DEMO");
  });
  it("uses the API when configured", () => {
    const p = createDataProvider({ NEXT_PUBLIC_DATA_SOURCE: "api", NEXT_PUBLIC_API_URL: "http://x" });
    expect(p).toBeInstanceOf(ApiDataProvider);
  });
});

describe("ApiDataProvider", () => {
  it("normalises bare payloads as non-demo API data", () => {
    const r = normalise<{ ok: boolean }>({ ok: true });
    expect(r.meta.source).toBe("API");
    expect(r.meta.isDemo).toBe(false);
  });

  it("respects an isDemo flag sent by the backend", () => {
    expect(normalise({ data: [], meta: { isDemo: true } }).meta.isDemo).toBe(true);
  });

  it("calls /health and surfaces HTTP errors", async () => {
    const fetchImpl = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))
      .mockResolvedValueOnce(new Response("nope", { status: 503 }));
    const api = new ApiDataProvider({ baseUrl: "http://api.test/", fetchImpl });
    await api.health();
    expect(fetchImpl).toHaveBeenCalledWith("http://api.test/health", expect.anything());
    await expect(api.getOverview()).rejects.toMatchObject({ status: 503, endpoint: "/v2/overview" });
  });
});
