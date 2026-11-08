import localFont from "next/font/local";

/**
 * The boarding pass is set in condensed caps, a typewriter mono and a
 * geometric display face. Served locally (no network at build or runtime).
 */
export const ticketCondensed = localFont({
  src: [
    { path: "../../app/fonts/oswald-latin-500-normal.woff2", weight: "500" },
    { path: "../../app/fonts/oswald-latin-600-normal.woff2", weight: "600" },
    { path: "../../app/fonts/oswald-latin-700-normal.woff2", weight: "700" },
  ],
  variable: "--font-ticket-condensed",
  display: "swap",
});

export const ticketMono = localFont({
  src: [{ path: "../../app/fonts/courier-prime-latin-400-normal.woff2", weight: "400" }],
  variable: "--font-ticket-mono",
  display: "swap",
});

export const ticketDisplay = localFont({
  src: [
    { path: "../../app/fonts/josefin-sans-latin-300-normal.woff2", weight: "300" },
    { path: "../../app/fonts/josefin-sans-latin-400-normal.woff2", weight: "400" },
  ],
  variable: "--font-ticket-display",
  display: "swap",
});
