import {
  inject
} from "./chunk-YCI2X4UR.js";

// node_modules/primevue/useconfirm/index.mjs
var PrimeVueConfirmSymbol = Symbol();
function useConfirm() {
  var PrimeVueConfirm = inject(PrimeVueConfirmSymbol);
  if (!PrimeVueConfirm) {
    throw new Error("No PrimeVue Confirmation provided!");
  }
  return PrimeVueConfirm;
}

export {
  PrimeVueConfirmSymbol,
  useConfirm
};
//# sourceMappingURL=chunk-THEXJJZO.js.map
