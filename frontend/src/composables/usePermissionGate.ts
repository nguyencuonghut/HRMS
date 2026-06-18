import { computed } from "vue";
import type { RouteLocationRaw } from "vue-router";
import router from "@/router";

import { useAuthStore } from "@/stores/auth";

export type PermissionModule =
  | "org"
  | "catalog"
  | "employees"
  | "contracts"
  | "leaves"
  | "insurance"
  | "salary"
  | "rewards"
  | "disciplines"
  | "training"
  | "recruitment"
  | "performance"
  | "reports"
  | "users"
  | "roles"
  | "audit_logs";

type PermissionSpec = {
  permission?: string;
  anyPermissions?: string[];
};

function normalizePermissionSpec(input: PermissionSpec): PermissionSpec {
  return {
    permission: input.permission,
    anyPermissions:
      input.anyPermissions && input.anyPermissions.length > 0
        ? input.anyPermissions
        : undefined,
  };
}

export function usePermissionGate() {
  const auth = useAuthStore();
  const permissions = computed(() => new Set(auth.user?.permissions ?? []));

  function hasPermission(permission: string): boolean {
    if (!auth.user) return false;
    if (auth.user.is_superuser || permissions.value.has("*")) return true;
    return permissions.value.has(permission);
  }

  function canAccess(spec: PermissionSpec): boolean {
    const normalized = normalizePermissionSpec(spec);
    if (normalized.permission && !hasPermission(normalized.permission)) {
      return false;
    }
    if (
      normalized.anyPermissions &&
      !normalized.anyPermissions.some((permission) => hasPermission(permission))
    ) {
      return false;
    }
    return true;
  }

  function canAccessRoute(to: RouteLocationRaw): boolean {
    const resolved = router.resolve(to);
    return canAccess({
      permission:
        typeof resolved.meta.permission === "string"
          ? resolved.meta.permission
          : undefined,
      anyPermissions: Array.isArray(resolved.meta.anyPermissions)
        ? resolved.meta.anyPermissions.filter(
            (value): value is string => typeof value === "string",
          )
        : undefined,
    });
  }

  // Action-level helpers
  function canView(module: PermissionModule): boolean {
    return hasPermission(`${module}:view`);
  }

  function canCreate(module: PermissionModule): boolean {
    return hasPermission(`${module}:create`);
  }

  function canEdit(module: PermissionModule): boolean {
    return hasPermission(`${module}:edit`);
  }

  function canDelete(module: PermissionModule): boolean {
    return hasPermission(`${module}:delete`);
  }

  function canExport(module: PermissionModule): boolean {
    return hasPermission(`${module}:export`);
  }

  return {
    hasPermission,
    canAccess,
    canAccessRoute,
    canView,
    canCreate,
    canEdit,
    canDelete,
    canExport,
  };
}
