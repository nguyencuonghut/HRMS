import type { RouteLocationRaw } from "vue-router";

import type { useAuthStore } from "@/stores/auth";

type AuthStore = ReturnType<typeof useAuthStore>;

export function getDefaultAuthorizedRoute(auth: AuthStore): RouteLocationRaw {
  const candidates: Array<{
    name: string;
    permission?: string;
    anyPermissions?: string[];
  }> = [
    {
      name: "dashboard-overview",
      permission: "reports:view",
      anyPermissions: ["employees:view"],
    },
    {
      name: "reports",
      permission: "reports:view",
      anyPermissions: [
        "employees:view",
        "leaves:view",
        "insurance:view",
        "contracts:view",
        "recruitment:view",
        "training:view",
        "rewards:view",
        "disciplines:view",
        "performance:view",
        "reports:view",
      ],
    },
    { name: "insurance", permission: "insurance:view" },
    { name: "salary", permission: "insurance:view" },
    { name: "export-center", permission: "reports:view" },
    { name: "employees", permission: "employees:view" },
    { name: "contracts", permission: "contracts:view" },
    { name: "leaves", permission: "leaves:view" },
    { name: "performance", permission: "performance:view" },
    { name: "jr-list", permission: "recruitment:view" },
    { name: "training", permission: "training:view" },
    { name: "rewards", anyPermissions: ["rewards:view", "disciplines:view"] },
    { name: "catalog", permission: "catalog:view" },
    { name: "settings", permission: "settings:view" },
  ];

  const firstAllowed = candidates.find((candidate) => {
    if (candidate.permission && !auth.hasPermission(candidate.permission)) {
      return false;
    }
    if (
      candidate.anyPermissions &&
      !candidate.anyPermissions.some((permission) => auth.hasPermission(permission))
    ) {
      return false;
    }
    return true;
  });

  return firstAllowed ? { name: firstAllowed.name } : { name: "forbidden" };
}
