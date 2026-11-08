import { BookOpenText, Bot, BrainCircuit, CircleHelp, LayoutDashboard, Plane, Route, TowerControl, type LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
  /** main: analysis areas. support: the "Support & methodology" section. page: reachable by URL only. */
  group: "main" | "support" | "page";
  /** What the module will contain — shown while it is not built yet. */
  planned?: string[];
}

export const NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    description: "The state of Brazilian aviation at a glance.",
    group: "main",
  },
  {
    href: "/dashboard/airports",
    label: "Airports Intelligence",
    icon: TowerControl,
    description: "Aircraft movements and paid passengers per aerodrome.",
    group: "main",
  },
  {
    href: "/dashboard/routes",
    label: "Routes Explorer",
    icon: Route,
    description: "Origin–destination flows and load factor.",
    group: "main",
  },
  {
    href: "/dashboard/airlines",
    label: "Airlines Analytics",
    icon: Plane,
    description: "Paid passengers and market share by carrier.",
    group: "main",
  },
  {
    href: "/dashboard/ml-studio",
    label: "ML Studio",
    icon: BrainCircuit,
    description: "How each forecasting method scored on 2023 validation data. No forecasts are served.",
    group: "support",
  },
  {
    href: "/dashboard/methodology",
    label: "Data & Methodology",
    icon: BookOpenText,
    description: "Datasets, modules and what to keep in mind.",
    group: "support",
  },
  {
    href: "/dashboard/methodology#reading-the-data",
    label: "How to read the data",
    icon: CircleHelp,
    description: "Coverage, missing months and the caveats behind every figure.",
    group: "support",
  },
  {
    href: "/dashboard/analyst",
    label: "AI Aviation Analyst",
    icon: Bot,
    description: "Questions in plain language, answered only from these data.",
    group: "page",
  },
];

export const navByHref = (href: string) => NAV.find((n) => n.href === href);
