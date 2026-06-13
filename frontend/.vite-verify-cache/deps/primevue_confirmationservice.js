import {
  PrimeVueConfirmSymbol
} from "./chunk-THEXJJZO.js";
import {
  ConfirmationEventBus
} from "./chunk-GUCTII6F.js";
import "./chunk-GFKAIPHP.js";
import "./chunk-YCI2X4UR.js";
import "./chunk-PZ5AY32C.js";

// node_modules/primevue/confirmationservice/index.mjs
var ConfirmationService = {
  install: function install(app) {
    var ConfirmationService2 = {
      require: function require2(options) {
        ConfirmationEventBus.emit("confirm", options);
      },
      close: function close() {
        ConfirmationEventBus.emit("close");
      }
    };
    app.config.globalProperties.$confirm = ConfirmationService2;
    app.provide(PrimeVueConfirmSymbol, ConfirmationService2);
  }
};
export {
  ConfirmationService as default
};
//# sourceMappingURL=primevue_confirmationservice.js.map
