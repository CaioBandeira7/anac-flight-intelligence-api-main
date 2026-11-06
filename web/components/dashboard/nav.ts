import { BookOpenText, Bot, BrainCircuit, LayoutDashboard, Plane, Route, TowerControl, type LucideIcon } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  description: string;
  /** What the module will contain — shown while it is not built yet. */
  planned?: string[];
}

export const NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    description: "The state of Brazilian aviation at a glance.",
  },
  {
    href: "/dashboard/airports",
    label: "Airports Intelligence",
    icon: TowerControl,
    description: "Aircraft movements per aerodrome.",
  },
  {
    href: "/dashboard/routes",
    label: "Routes Explorer",
    icon: Route,
    description: "Origin–destination flows and load factor.",
  },
  {
    href: "/dashboard/airlines",
    label: "Airlines Analytics",
    icon: Plane,
    description: "Market share and network strategy by carrier.",
    planned: ["Market share over time", "Fleet and network deployment", "Carrier comparison"],
  },
  {
    href: "/dashboard/ml-studio",
    label: "ML Studio",
    icon: BrainCircuit,
    description: "Models and their evaluation.",
  },
  {
    href: "/dashboard/methodology",
    label: "Data & Methodology",
    icon: BookOpenText,
    description: "Datasets, modules and what to keep in mind.",
  },
  {
    href: "/dashboard/analyst",
    label: "AI Aviation Analyst",
    icon: Bot,
    description: "Questions in plain language, answered only from these data.",
  },
];

export const navByHref = (href: string) => NAV.find((n) => n.href === href);
