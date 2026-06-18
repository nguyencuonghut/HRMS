import type { Directive } from "vue";
import { usePermissionGate } from "@/composables/usePermissionGate";

export const canDirective: Directive = {
  mounted(el: HTMLElement, binding) {
    const gate = usePermissionGate();
    const hasAccess = checkAccess(binding, gate);
    if (!hasAccess) {
      if (binding.modifiers.disable) {
        el.setAttribute("disabled", "true");
        el.classList.add("p-disabled");
        if (el.tagName === "BUTTON") {
          (el as HTMLButtonElement).disabled = true;
        }
      } else {
        el.style.display = "none";
      }
    }
  },
  updated(el: HTMLElement, binding) {
    const gate = usePermissionGate();
    const hasAccess = checkAccess(binding, gate);
    if (hasAccess) {
      if (binding.modifiers.disable) {
        el.removeAttribute("disabled");
        el.classList.remove("p-disabled");
        if (el.tagName === "BUTTON") {
          (el as HTMLButtonElement).disabled = false;
        }
      } else {
        el.style.display = "";
      }
    } else {
      if (binding.modifiers.disable) {
        el.setAttribute("disabled", "true");
        el.classList.add("p-disabled");
        if (el.tagName === "BUTTON") {
          (el as HTMLButtonElement).disabled = true;
        }
      } else {
        el.style.display = "none";
      }
    }
  },
};

function checkAccess(
  binding: any,
  gate: ReturnType<typeof usePermissionGate>,
): boolean {
  const { value, arg } = binding;

  if (typeof value === "string") {
    if (arg) {
      return gate.hasPermission(`${value}:${arg}`);
    }
    return gate.hasPermission(value);
  }

  if (Array.isArray(value)) {
    return value.some(
      (perm) => typeof perm === "string" && gate.hasPermission(perm),
    );
  }

  if (typeof value === "object" && value !== null) {
    return gate.canAccess(value);
  }

  return false;
}
export default canDirective;
