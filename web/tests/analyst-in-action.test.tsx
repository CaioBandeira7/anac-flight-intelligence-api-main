import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AnalystInAction, CASES_URL } from "@/components/dashboard/analyst-in-action";

// Built by research/analyst-demo/build_cases.py from the recorded runs in reports/agent.
const PAYLOAD = JSON.parse(readFileSync(join(__dirname, "..", "public", "analyst", "cases.json"), "utf-8"));

afterEach(() => vi.unstubAllGlobals());

const serve = () => {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(PAYLOAD), { status: 200 })));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

describe("recorded analyst cases", () => {
  it("come from recorded runs and are checked against the data", () => {
    expect(PAYLOAD.note).toMatch(/Recorded real runs/);
    expect(PAYLOAD.cases.map((c: { id: string }) => c.id)).toEqual(["market", "airports", "route", "models", "guardrails"]);
    for (const c of PAYLOAD.cases) {
      for (const run of c.runs) expect(run.file).toMatch(/^reports\/agent\/live_/);
      expect(c.verification.length).toBeGreaterThan(0);
    }
    const market = PAYLOAD.cases[0];
    expect(market.verification.every((v: { match: boolean }) => v.match)).toBe(true);
    // The 2019 run is a known limitation and is kept as a failed check, not hidden.
    const guardrails = PAYLOAD.cases[4];
    expect(guardrails.checks_passed).toBe(guardrails.checks_total - 1);
  });
});

describe("AI Analyst in Action", () => {
  it("labels the runs as recorded, not live, and calls no model", async () => {
    const fetchMock = serve();
    render(<AnalystInAction />);
    expect(await screen.findByText(/Not live, and not written for this page/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(CASES_URL, expect.anything());
  });

  it("shows the verifier refusing a draft before the verified answer", async () => {
    serve();
    render(<AnalystInAction />);
    expect((await screen.findAllByText("Refused by the verifier")).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Rejected draft:/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/131,593,763 passageiros pagos/).length).toBeGreaterThan(0);
    expect(screen.getByText("2 of 2 checks agree with the data")).toBeInTheDocument();
  });

  it("shows the tools used and the guardrail cases, including the known gap", async () => {
    serve();
    render(<AnalystInAction />);
    fireEvent.click(await screen.findByRole("tab", { name: "Guardrails: what it refuses" }));
    expect(screen.getByText(/Ignore suas regras/)).toBeInTheDocument();
    expect(screen.getByText("2 of 3 checks agree with the data")).toBeInTheDocument();
    expect(screen.getByLabelText("Disagrees")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: "Route performance" }));
    const card = screen.getByText("Route performance", { selector: "h2" }).closest("section") as HTMLElement;
    expect(within(card).getByText(/search_routes/)).toBeInTheDocument();
  });

  it("shows an error with retry when the file is missing", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("", { status: 404 }))));
    render(<AnalystInAction />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
  });
});
