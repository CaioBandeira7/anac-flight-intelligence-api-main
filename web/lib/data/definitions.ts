/**
 * Short definitions shown next to measures. They restate docs/analytics.md and
 * keep measures with different scopes apart: flights, passenger flights and
 * aircraft movements are not the same count.
 */
export const DEFINITIONS = {
  paid_passengers: "Paid passengers, counted once per flight leg. A passenger who stays on board for two legs counts twice.",
  flights: "Every operated takeoff, including cargo and other flights outside the passenger scope.",
  passenger_flights: "Takeoffs in the passenger scope only: flights with seats offered, excluding positioning and recording errors.",
  seats: "Seats offered on passenger-scope flights.",
  load_factor: "Paid passengers ÷ seats offered, from the totals of the whole period. Never an average of monthly ratios.",
  market_share: "The carrier's share of all carriers' paid passengers in the selected period.",
  movements: "Takeoffs plus landings at the airport, for every operated leg, cargo included.",
  departures: "Takeoffs from the airport, for every operated leg.",
  arrivals: "Landings at the airport, for every operated leg.",
  departing_paid_passengers: "Paid passengers on passenger-scope legs leaving the airport.",
  arriving_paid_passengers: "Paid passengers on passenger-scope legs arriving at the airport.",
  international_paid_passengers: "Paid passengers on legs with a foreign origin or destination.",
} as const;

export type DefinitionKey = keyof typeof DEFINITIONS;
