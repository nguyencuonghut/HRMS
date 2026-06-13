import {
  script as script2
} from "./chunk-B6VCNZXJ.js";
import {
  script as script3
} from "./chunk-WUIS2BHK.js";
import "./chunk-G5XFRV5E.js";
import {
  script
} from "./chunk-VKB4EPHO.js";
import "./chunk-EOSUVNFN.js";
import {
  BaseStyle
} from "./chunk-SPJMUJTG.js";
import {
  _
} from "./chunk-DRWS4XVE.js";
import "./chunk-GFKAIPHP.js";
import "./chunk-R7AX3T4B.js";
import {
  Fragment,
  createBaseVNode,
  createBlock,
  createCommentVNode,
  createElementBlock,
  createVNode,
  guardReactiveProps,
  mergeProps,
  normalizeProps,
  openBlock,
  renderList,
  resolveComponent,
  resolveDynamicComponent
} from "./chunk-YCI2X4UR.js";
import "./chunk-PZ5AY32C.js";

// node_modules/@primeuix/styles/dist/organizationchart/index.mjs
var style = "\n    .p-organizationchart-table {\n        border-spacing: 0;\n        border-collapse: separate;\n        margin: 0 auto;\n    }\n\n    .p-organizationchart-table > tbody > tr > td {\n        text-align: center;\n        vertical-align: top;\n        padding: 0 dt('organizationchart.gutter');\n    }\n\n    .p-organizationchart-node {\n        display: inline-block;\n        position: relative;\n        border: 1px solid dt('organizationchart.node.border.color');\n        background: dt('organizationchart.node.background');\n        color: dt('organizationchart.node.color');\n        padding: dt('organizationchart.node.padding');\n        border-radius: dt('organizationchart.node.border.radius');\n        transition:\n            background dt('organizationchart.transition.duration'),\n            border-color dt('organizationchart.transition.duration'),\n            color dt('organizationchart.transition.duration'),\n            box-shadow dt('organizationchart.transition.duration');\n    }\n\n    .p-organizationchart-node:has(.p-organizationchart-node-toggle-button) {\n        padding: dt('organizationchart.node.toggleable.padding');\n    }\n\n    .p-organizationchart-node.p-organizationchart-node-selectable:not(.p-organizationchart-node-selected):hover {\n        background: dt('organizationchart.node.hover.background');\n        color: dt('organizationchart.node.hover.color');\n    }\n\n    .p-organizationchart-node-selected {\n        background: dt('organizationchart.node.selected.background');\n        color: dt('organizationchart.node.selected.color');\n    }\n\n    .p-organizationchart-node-toggle-button {\n        position: absolute;\n        inset-block-end: calc(-1 * calc(dt('organizationchart.node.toggle.button.size') / 2));\n        margin-inline-start: calc(-1 * calc(dt('organizationchart.node.toggle.button.size') / 2));\n        z-index: 2;\n        inset-inline-start: 50%;\n        user-select: none;\n        cursor: pointer;\n        width: dt('organizationchart.node.toggle.button.size');\n        height: dt('organizationchart.node.toggle.button.size');\n        text-decoration: none;\n        background: dt('organizationchart.node.toggle.button.background');\n        color: dt('organizationchart.node.toggle.button.color');\n        border-radius: dt('organizationchart.node.toggle.button.border.radius');\n        border: 1px solid dt('organizationchart.node.toggle.button.border.color');\n        display: inline-flex;\n        justify-content: center;\n        align-items: center;\n        outline-color: transparent;\n        transition:\n            background dt('organizationchart.transition.duration'),\n            color dt('organizationchart.transition.duration'),\n            border-color dt('organizationchart.transition.duration'),\n            outline-color dt('organizationchart.transition.duration'),\n            box-shadow dt('organizationchart.transition.duration');\n    }\n\n    .p-organizationchart-node-toggle-button:hover {\n        background: dt('organizationchart.node.toggle.button.hover.background');\n        color: dt('organizationchart.node.toggle.button.hover.color');\n    }\n\n    .p-organizationchart-node-toggle-button:focus-visible {\n        box-shadow: dt('organizationchart.node.toggle.button.focus.ring.shadow');\n        outline: dt('organizationchart.node.toggle.button.focus.ring.width') dt('organizationchart.node.toggle.button.focus.ring.style') dt('organizationchart.node.toggle.button.focus.ring.color');\n        outline-offset: dt('organizationchart.node.toggle.button.focus.ring.offset');\n    }\n\n    .p-organizationchart-node-toggle-button-icon {\n        position: relative;\n        inset-block-start: 1px;\n    }\n\n    .p-organizationchart-connector-down {\n        margin: 0 auto;\n        height: dt('organizationchart.connector.height');\n        width: 1px;\n        background: dt('organizationchart.connector.color');\n    }\n\n    .p-organizationchart-connector-right {\n        border-radius: 0;\n    }\n\n    .p-organizationchart-connector-left {\n        border-radius: 0;\n        border-inline-end: 1px solid dt('organizationchart.connector.color');\n    }\n\n    .p-organizationchart-connector-top {\n        border-block-start: 1px solid dt('organizationchart.connector.color');\n    }\n\n    .p-organizationchart-node-selectable {\n        cursor: pointer;\n    }\n\n    .p-organizationchart-connectors :nth-child(1 of .p-organizationchart-connector-left) {\n        border-inline-end: 0 none;\n    }\n\n    .p-organizationchart-connectors :nth-last-child(1 of .p-organizationchart-connector-left) {\n        border-start-end-radius: dt('organizationchart.connector.border.radius');\n    }\n\n    .p-organizationchart-connectors :nth-child(1 of .p-organizationchart-connector-right) {\n        border-inline-start: 1px solid dt('organizationchart.connector.color');\n        border-start-start-radius: dt('organizationchart.connector.border.radius');\n    }\n";

// node_modules/primevue/organizationchart/style/index.mjs
var classes = {
  root: "p-organizationchart p-component",
  table: "p-organizationchart-table",
  node: function node(_ref) {
    var instance = _ref.instance;
    return ["p-organizationchart-node", {
      "p-organizationchart-node-selectable": instance.selectable,
      "p-organizationchart-node-selected": instance.selected
    }];
  },
  nodeToggleButton: function nodeToggleButton(_ref2) {
    var instance = _ref2.instance;
    return ["p-organizationchart-node-toggle-button", {
      "p-disabled": !instance.selectable
    }];
  },
  nodeToggleButtonIcon: "p-organizationchart-node-toggle-button-icon",
  connectors: "p-organizationchart-connectors",
  connectorDown: "p-organizationchart-connector-down",
  connectorLeft: function connectorLeft(_ref3) {
    var index = _ref3.index;
    return ["p-organizationchart-connector-left", {
      "p-organizationchart-connector-top": !(index === 0)
    }];
  },
  connectorRight: function connectorRight(_ref4) {
    var props = _ref4.props, index = _ref4.index;
    return ["p-organizationchart-connector-right", {
      "p-organizationchart-connector-top": !(index === props.node.children.length - 1)
    }];
  },
  nodeChildren: "p-organizationchart-node-children"
};
var OrganizationChartStyle = BaseStyle.extend({
  name: "organizationchart",
  style,
  classes
});

// node_modules/primevue/organizationchart/index.mjs
var script$2 = {
  name: "BaseOrganizationChart",
  "extends": script,
  props: {
    value: {
      type: null,
      "default": null
    },
    selectionKeys: {
      type: null,
      "default": null
    },
    selectionMode: {
      type: String,
      "default": null
    },
    collapsible: {
      type: Boolean,
      "default": false
    },
    collapsedKeys: {
      type: null,
      "default": null
    }
  },
  style: OrganizationChartStyle,
  provide: function provide() {
    return {
      $pcOrganizationChart: this,
      $parentInstance: this
    };
  }
};
var script$1 = {
  name: "OrganizationChartNode",
  hostName: "OrganizationChart",
  "extends": script,
  emits: ["node-click", "node-toggle"],
  props: {
    node: {
      type: null,
      "default": null
    },
    templates: {
      type: null,
      "default": null
    },
    collapsible: {
      type: Boolean,
      "default": false
    },
    collapsedKeys: {
      type: null,
      "default": null
    },
    selectionKeys: {
      type: null,
      "default": null
    },
    selectionMode: {
      type: String,
      "default": null
    }
  },
  methods: {
    getPTOptions: function getPTOptions(key) {
      return this.ptm(key, {
        context: {
          expanded: this.expanded,
          selectable: this.selectable,
          selected: this.selected,
          toggleable: this.toggleable,
          active: this.selected
        }
      });
    },
    getNodeOptions: function getNodeOptions(lineTop, key) {
      return this.ptm(key, {
        context: {
          lineTop
        }
      });
    },
    onNodeClick: function onNodeClick(event) {
      if (_(event.target, "data-pc-section", "nodetogglebutton") || _(event.target, "data-pc-section", "nodetogglebuttonicon")) {
        return;
      }
      if (this.selectionMode) {
        this.$emit("node-click", this.node);
      }
    },
    onChildNodeClick: function onChildNodeClick(node2) {
      this.$emit("node-click", node2);
    },
    toggleNode: function toggleNode() {
      this.$emit("node-toggle", this.node);
    },
    onChildNodeToggle: function onChildNodeToggle(node2) {
      this.$emit("node-toggle", node2);
    },
    onKeydown: function onKeydown(event) {
      if (event.code === "Enter" || event.code === "NumpadEnter" || event.code === "Space") {
        this.toggleNode();
        event.preventDefault();
      }
    }
  },
  computed: {
    leaf: function leaf() {
      return this.node.leaf === false ? false : !(this.node.children && this.node.children.length);
    },
    colspan: function colspan() {
      return this.node.children && this.node.children.length ? this.node.children.length * 2 : null;
    },
    childStyle: function childStyle() {
      return {
        visibility: !this.leaf && this.expanded ? "inherit" : "hidden"
      };
    },
    expanded: function expanded() {
      return this.collapsedKeys[this.node.key] === void 0;
    },
    selectable: function selectable() {
      return this.selectionMode && this.node.selectable !== false;
    },
    selected: function selected() {
      return this.selectable && this.selectionKeys && this.selectionKeys[this.node.key] === true;
    },
    toggleable: function toggleable() {
      return this.collapsible && this.node.collapsible !== false && !this.leaf;
    }
  },
  components: {
    ChevronDownIcon: script3,
    ChevronUpIcon: script2
  }
};
var _hoisted_1 = ["colspan"];
var _hoisted_2 = ["colspan"];
var _hoisted_3 = ["colspan"];
function render$1(_ctx, _cache, $props, $setup, $data, $options) {
  var _component_OrganizationChartNode = resolveComponent("OrganizationChartNode", true);
  return openBlock(), createElementBlock("table", mergeProps({
    "class": _ctx.cx("table")
  }, _ctx.ptm("table")), [createBaseVNode("tbody", normalizeProps(guardReactiveProps(_ctx.ptm("body"))), [$props.node ? (openBlock(), createElementBlock("tr", normalizeProps(mergeProps({
    key: 0
  }, _ctx.ptm("row"))), [createBaseVNode("td", mergeProps({
    colspan: $options.colspan
  }, _ctx.ptm("cell")), [createBaseVNode("div", mergeProps({
    "class": [_ctx.cx("node"), $props.node.styleClass],
    onClick: _cache[2] || (_cache[2] = function() {
      return $options.onNodeClick && $options.onNodeClick.apply($options, arguments);
    })
  }, $options.getPTOptions("node")), [(openBlock(), createBlock(resolveDynamicComponent($props.templates[$props.node.type] || $props.templates["default"]), {
    node: $props.node
  }, null, 8, ["node"])), $options.toggleable ? (openBlock(), createElementBlock("a", mergeProps({
    key: 0,
    tabindex: "0",
    "class": _ctx.cx("nodeToggleButton"),
    onClick: _cache[0] || (_cache[0] = function() {
      return $options.toggleNode && $options.toggleNode.apply($options, arguments);
    }),
    onKeydown: _cache[1] || (_cache[1] = function() {
      return $options.onKeydown && $options.onKeydown.apply($options, arguments);
    })
  }, $options.getPTOptions("nodeToggleButton")), [$props.templates.toggleicon || $props.templates.togglericon ? (openBlock(), createBlock(resolveDynamicComponent($props.templates.toggleicon || $props.templates.togglericon), mergeProps({
    key: 0,
    expanded: $options.expanded,
    "class": _ctx.cx("nodeToggleButtonIcon")
  }, $options.getPTOptions("nodeToggleButtonIcon")), null, 16, ["expanded", "class"])) : (openBlock(), createBlock(resolveDynamicComponent($options.expanded ? "ChevronDownIcon" : "ChevronUpIcon"), mergeProps({
    key: 1,
    "class": _ctx.cx("nodeToggleButtonIcon")
  }, $options.getPTOptions("nodeToggleButtonIcon")), null, 16, ["class"]))], 16)) : createCommentVNode("", true)], 16)], 16, _hoisted_1)], 16)) : createCommentVNode("", true), createBaseVNode("tr", mergeProps({
    style: $options.childStyle,
    "class": _ctx.cx("connectors")
  }, _ctx.ptm("connectors")), [createBaseVNode("td", mergeProps({
    colspan: $options.colspan
  }, _ctx.ptm("lineCell")), [createBaseVNode("div", mergeProps({
    "class": _ctx.cx("connectorDown")
  }, _ctx.ptm("connectorDown")), null, 16)], 16, _hoisted_2)], 16), createBaseVNode("tr", mergeProps({
    style: $options.childStyle,
    "class": _ctx.cx("connectors")
  }, _ctx.ptm("connectors")), [$props.node.children && $props.node.children.length === 1 ? (openBlock(), createElementBlock("td", mergeProps({
    key: 0,
    colspan: $options.colspan
  }, _ctx.ptm("lineCell")), [createBaseVNode("div", mergeProps({
    "class": _ctx.cx("connectorDown")
  }, _ctx.ptm("connectorDown")), null, 16)], 16, _hoisted_3)) : createCommentVNode("", true), $props.node.children && $props.node.children.length > 1 ? (openBlock(true), createElementBlock(Fragment, {
    key: 1
  }, renderList($props.node.children, function(child, i) {
    return openBlock(), createElementBlock(Fragment, {
      key: child.key
    }, [createBaseVNode("td", mergeProps({
      "class": _ctx.cx("connectorLeft", {
        index: i
      })
    }, {
      ref_for: true
    }, $options.getNodeOptions(!(i === 0), "connectorLeft")), " ", 16), createBaseVNode("td", mergeProps({
      "class": _ctx.cx("connectorRight", {
        index: i
      })
    }, {
      ref_for: true
    }, $options.getNodeOptions(!(i === $props.node.children.length - 1), "connectorRight")), " ", 16)], 64);
  }), 128)) : createCommentVNode("", true)], 16), createBaseVNode("tr", mergeProps({
    style: $options.childStyle,
    "class": _ctx.cx("nodeChildren")
  }, _ctx.ptm("nodeChildren")), [(openBlock(true), createElementBlock(Fragment, null, renderList($props.node.children, function(child) {
    return openBlock(), createElementBlock("td", mergeProps({
      key: child.key,
      colspan: "2"
    }, {
      ref_for: true
    }, _ctx.ptm("nodeCell")), [createVNode(_component_OrganizationChartNode, {
      node: child,
      templates: $props.templates,
      collapsedKeys: $props.collapsedKeys,
      onNodeToggle: $options.onChildNodeToggle,
      collapsible: $props.collapsible,
      selectionMode: $props.selectionMode,
      selectionKeys: $props.selectionKeys,
      onNodeClick: $options.onChildNodeClick,
      pt: _ctx.pt,
      unstyled: _ctx.unstyled
    }, null, 8, ["node", "templates", "collapsedKeys", "onNodeToggle", "collapsible", "selectionMode", "selectionKeys", "onNodeClick", "pt", "unstyled"])], 16);
  }), 128))], 16)], 16)], 16);
}
script$1.render = render$1;
function _typeof(o) {
  "@babel/helpers - typeof";
  return _typeof = "function" == typeof Symbol && "symbol" == typeof Symbol.iterator ? function(o2) {
    return typeof o2;
  } : function(o2) {
    return o2 && "function" == typeof Symbol && o2.constructor === Symbol && o2 !== Symbol.prototype ? "symbol" : typeof o2;
  }, _typeof(o);
}
function ownKeys(e, r) {
  var t = Object.keys(e);
  if (Object.getOwnPropertySymbols) {
    var o = Object.getOwnPropertySymbols(e);
    r && (o = o.filter(function(r2) {
      return Object.getOwnPropertyDescriptor(e, r2).enumerable;
    })), t.push.apply(t, o);
  }
  return t;
}
function _objectSpread(e) {
  for (var r = 1; r < arguments.length; r++) {
    var t = null != arguments[r] ? arguments[r] : {};
    r % 2 ? ownKeys(Object(t), true).forEach(function(r2) {
      _defineProperty(e, r2, t[r2]);
    }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function(r2) {
      Object.defineProperty(e, r2, Object.getOwnPropertyDescriptor(t, r2));
    });
  }
  return e;
}
function _defineProperty(e, r, t) {
  return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: true, configurable: true, writable: true }) : e[r] = t, e;
}
function _toPropertyKey(t) {
  var i = _toPrimitive(t, "string");
  return "symbol" == _typeof(i) ? i : i + "";
}
function _toPrimitive(t, r) {
  if ("object" != _typeof(t) || !t) return t;
  var e = t[Symbol.toPrimitive];
  if (void 0 !== e) {
    var i = e.call(t, r);
    if ("object" != _typeof(i)) return i;
    throw new TypeError("@@toPrimitive must return a primitive value.");
  }
  return ("string" === r ? String : Number)(t);
}
var script4 = {
  name: "OrganizationChart",
  "extends": script$2,
  inheritAttrs: false,
  emits: ["node-unselect", "node-select", "update:selectionKeys", "node-expand", "node-collapse", "update:collapsedKeys"],
  data: function data() {
    return {
      d_collapsedKeys: this.collapsedKeys || {}
    };
  },
  watch: {
    collapsedKeys: function collapsedKeys(newValue) {
      this.d_collapsedKeys = newValue;
    }
  },
  methods: {
    onNodeClick: function onNodeClick2(node2) {
      var key = node2.key;
      if (this.selectionMode) {
        var _selectionKeys = this.selectionKeys ? _objectSpread({}, this.selectionKeys) : {};
        if (_selectionKeys[key]) {
          delete _selectionKeys[key];
          this.$emit("node-unselect", node2);
        } else {
          if (this.selectionMode === "single") {
            _selectionKeys = {};
          }
          _selectionKeys[key] = true;
          this.$emit("node-select", node2);
        }
        this.$emit("update:selectionKeys", _selectionKeys);
      }
    },
    onNodeToggle: function onNodeToggle(node2) {
      var key = node2.key;
      if (this.d_collapsedKeys[key]) {
        delete this.d_collapsedKeys[key];
        this.$emit("node-expand", node2);
      } else {
        this.d_collapsedKeys[key] = true;
        this.$emit("node-collapse", node2);
      }
      this.d_collapsedKeys = _objectSpread({}, this.d_collapsedKeys);
      this.$emit("update:collapsedKeys", this.d_collapsedKeys);
    }
  },
  components: {
    OrganizationChartNode: script$1
  }
};
function render(_ctx, _cache, $props, $setup, $data, $options) {
  var _component_OrganizationChartNode = resolveComponent("OrganizationChartNode");
  return openBlock(), createElementBlock("div", mergeProps({
    "class": _ctx.cx("root")
  }, _ctx.ptmi("root")), [createVNode(_component_OrganizationChartNode, {
    node: _ctx.value,
    templates: _ctx.$slots,
    onNodeToggle: $options.onNodeToggle,
    collapsedKeys: $data.d_collapsedKeys,
    collapsible: _ctx.collapsible,
    onNodeClick: $options.onNodeClick,
    selectionMode: _ctx.selectionMode,
    selectionKeys: _ctx.selectionKeys,
    pt: _ctx.pt,
    unstyled: _ctx.unstyled
  }, null, 8, ["node", "templates", "onNodeToggle", "collapsedKeys", "collapsible", "onNodeClick", "selectionMode", "selectionKeys", "pt", "unstyled"])], 16);
}
script4.render = render;
export {
  script4 as default
};
//# sourceMappingURL=primevue_organizationchart.js.map
