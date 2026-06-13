import {
  inject
} from "./chunk-YCI2X4UR.js";

// node_modules/primevue/usetoast/index.mjs
var PrimeVueToastSymbol = Symbol();
function useToast() {
  var PrimeVueToast = inject(PrimeVueToastSymbol);
  if (!PrimeVueToast) {
    throw new Error("No PrimeVue Toast provided!");
  }
  return PrimeVueToast;
}

export {
  PrimeVueToastSymbol,
  useToast
};
//# sourceMappingURL=chunk-JMF5VQVL.js.map
