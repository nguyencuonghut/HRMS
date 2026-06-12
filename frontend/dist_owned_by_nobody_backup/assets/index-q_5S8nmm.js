import{B as k,q as s,aF as I,n as S,ad as b,z as v,y as C,A as m,o as l,f as B,h as K,H as h,F as y,E as V,ag as f,af as z,ah as E,ai as u,v as R,aL as $,c as p,g as L,a as g}from"./index-C3KpH1wY.js";import{R as O,a as w,f as P}from"./index-aFOqnJmW.js";import{s as F}from"./index-DrrpA3yD.js";import{a as D}from"./index-G5pdG3x2.js";var W={root:function(t){var n=t.instance,a=t.props;return["p-tab",{"p-tab-active":n.active,"p-disabled":a.disabled}]}},_=k.extend({name:"tab",classes:W}),H={name:"BaseTab",extends:w,props:{value:{type:[String,Number],default:void 0},disabled:{type:Boolean,default:!1},as:{type:[String,Object],default:"BUTTON"},asChild:{type:Boolean,default:!1}},style:_,provide:function(){return{$pcTab:this,$parentInstance:this}}},U={name:"Tab",extends:H,inheritAttrs:!1,inject:["$pcTabs","$pcTabList"],methods:{onFocus:function(){this.$pcTabs.selectOnFocus&&this.changeActiveValue()},onClick:function(){this.changeActiveValue()},onKeydown:function(t){switch(t.code){case"ArrowRight":this.onArrowRightKey(t);break;case"ArrowLeft":this.onArrowLeftKey(t);break;case"Home":this.onHomeKey(t);break;case"End":this.onEndKey(t);break;case"PageDown":this.onPageDownKey(t);break;case"PageUp":this.onPageUpKey(t);break;case"Enter":case"NumpadEnter":case"Space":this.onEnterKey(t);break}},onArrowRightKey:function(t){var n=this.findNextTab(t.currentTarget);n?this.changeFocusedTab(t,n):this.onHomeKey(t),t.preventDefault()},onArrowLeftKey:function(t){var n=this.findPrevTab(t.currentTarget);n?this.changeFocusedTab(t,n):this.onEndKey(t),t.preventDefault()},onHomeKey:function(t){var n=this.findFirstTab();this.changeFocusedTab(t,n),t.preventDefault()},onEndKey:function(t){var n=this.findLastTab();this.changeFocusedTab(t,n),t.preventDefault()},onPageDownKey:function(t){this.scrollInView(this.findLastTab()),t.preventDefault()},onPageUpKey:function(t){this.scrollInView(this.findFirstTab()),t.preventDefault()},onEnterKey:function(t){this.changeActiveValue()},findNextTab:function(t){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,a=n?t:t.nextElementSibling;return a?b(a,"data-p-disabled")||b(a,"data-pc-section")==="activebar"?this.findNextTab(a):v(a,'[data-pc-name="tab"]'):null},findPrevTab:function(t){var n=arguments.length>1&&arguments[1]!==void 0?arguments[1]:!1,a=n?t:t.previousElementSibling;return a?b(a,"data-p-disabled")||b(a,"data-pc-section")==="activebar"?this.findPrevTab(a):v(a,'[data-pc-name="tab"]'):null},findFirstTab:function(){return this.findNextTab(this.$pcTabList.$refs.tabs.firstElementChild,!0)},findLastTab:function(){return this.findPrevTab(this.$pcTabList.$refs.tabs.lastElementChild,!0)},changeActiveValue:function(){this.$pcTabs.updateValue(this.value)},changeFocusedTab:function(t,n){S(n),this.scrollInView(n)},scrollInView:function(t){var n;t==null||(n=t.scrollIntoView)===null||n===void 0||n.call(t,{block:"nearest"})}},computed:{active:function(){var t;return I((t=this.$pcTabs)===null||t===void 0?void 0:t.d_value,this.value)},id:function(){var t;return"".concat((t=this.$pcTabs)===null||t===void 0?void 0:t.$id,"_tab_").concat(this.value)},ariaControls:function(){var t;return"".concat((t=this.$pcTabs)===null||t===void 0?void 0:t.$id,"_tabpanel_").concat(this.value)},attrs:function(){return s(this.asAttrs,this.a11yAttrs,this.ptmi("root",this.ptParams))},asAttrs:function(){return this.as==="BUTTON"?{type:"button",disabled:this.disabled}:void 0},a11yAttrs:function(){return{id:this.id,tabindex:this.active?this.$pcTabs.tabindex:-1,role:"tab","aria-selected":this.active,"aria-controls":this.ariaControls,"data-pc-name":"tab","data-p-disabled":this.disabled,"data-p-active":this.active,onFocus:this.onFocus,onKeydown:this.onKeydown}},ptParams:function(){return{context:{active:this.active}}},dataP:function(){return P({active:this.active})}},directives:{ripple:O}};function M(e,t,n,a,r,i){var o=C("ripple");return e.asChild?h(e.$slots,"default",{key:1,dataP:i.dataP,class:V(e.cx("root")),active:i.active,a11yAttrs:i.a11yAttrs,onClick:i.onClick}):m((l(),B(y(e.as),s({key:0,class:e.cx("root"),"data-p":i.dataP,onClick:i.onClick},i.attrs),{default:K(function(){return[h(e.$slots,"default")]}),_:3},16,["class","data-p","onClick"])),[[o]])}U.render=M;var j={root:"p-tablist",content:"p-tablist-content p-tablist-viewport",tabList:"p-tablist-tab-list",activeBar:"p-tablist-active-bar",prevButton:"p-tablist-prev-button p-tablist-nav-button",nextButton:"p-tablist-next-button p-tablist-nav-button"},q=k.extend({name:"tablist",classes:j}),Q={name:"BaseTabList",extends:w,props:{},style:q,provide:function(){return{$pcTabList:this,$parentInstance:this}}},G={name:"TabList",extends:Q,inheritAttrs:!1,inject:["$pcTabs"],data:function(){return{isPrevButtonEnabled:!1,isNextButtonEnabled:!0}},resizeObserver:void 0,inkBarObserver:void 0,watch:{showNavigators:function(t){t?this.bindResizeObserver():this.unbindResizeObserver()},activeValue:{flush:"post",handler:function(){this.updateInkBar(),this.bindInkBarObserver()}}},mounted:function(){var t=this;setTimeout(function(){t.updateInkBar(),t.bindInkBarObserver()},150),this.showNavigators&&(this.updateButtonState(),this.bindResizeObserver())},updated:function(){this.showNavigators&&this.updateButtonState()},beforeUnmount:function(){this.unbindResizeObserver(),this.unbindInkBarObserver()},methods:{onScroll:function(t){this.showNavigators&&this.updateButtonState(),t.preventDefault()},onPrevButtonClick:function(){var t=this.$refs.content,n=this.getVisibleButtonWidths(),a=f(t)-n,r=Math.abs(t.scrollLeft),i=a*.8,o=r-i,d=Math.max(o,0);t.scrollLeft=$(t)?-1*d:d},onNextButtonClick:function(){var t=this.$refs.content,n=this.getVisibleButtonWidths(),a=f(t)-n,r=Math.abs(t.scrollLeft),i=a*.8,o=r+i,d=t.scrollWidth-a,c=Math.min(o,d);t.scrollLeft=$(t)?-1*c:c},bindResizeObserver:function(){var t=this;this.resizeObserver=new ResizeObserver(function(){return t.updateButtonState()}),this.resizeObserver.observe(this.$refs.list)},unbindResizeObserver:function(){var t;(t=this.resizeObserver)===null||t===void 0||t.unobserve(this.$refs.list),this.resizeObserver=void 0},bindInkBarObserver:function(){var t=this;this.unbindInkBarObserver();var n=this.$refs.content,a=v(n,'[data-pc-name="tab"][data-p-active="true"]');a&&(this.inkBarObserver=new ResizeObserver(function(){return t.updateInkBar()}),this.inkBarObserver.observe(a))},unbindInkBarObserver:function(){var t;(t=this.inkBarObserver)===null||t===void 0||t.disconnect(),this.inkBarObserver=void 0},updateInkBar:function(){var t=this.$refs,n=t.content,a=t.inkbar,r=t.tabs;if(a){var i=v(n,'[data-pc-name="tab"][data-p-active="true"]');this.$pcTabs.isVertical()?(a.style.height=E(i)+"px",a.style.top=u(i).top-u(r).top+"px"):(a.style.width=R(i)+"px",a.style.left=u(i).left-u(r).left+"px")}},updateButtonState:function(){var t=this.$refs,n=t.list,a=t.content,r=a.scrollTop,i=a.scrollWidth,o=a.scrollHeight,d=a.offsetWidth,c=a.offsetHeight,T=Math.abs(a.scrollLeft),x=[f(a),z(a)],N=x[0],A=x[1];this.$pcTabs.isVertical()?(this.isPrevButtonEnabled=r!==0,this.isNextButtonEnabled=n.offsetHeight>=c&&parseInt(r)!==o-A):(this.isPrevButtonEnabled=T!==0,this.isNextButtonEnabled=n.offsetWidth>=d&&parseInt(T)!==i-N)},getVisibleButtonWidths:function(){var t=this.$refs,n=t.prevButton,a=t.nextButton,r=0;return this.showNavigators&&(r=((n==null?void 0:n.offsetWidth)||0)+((a==null?void 0:a.offsetWidth)||0)),r}},computed:{templates:function(){return this.$pcTabs.$slots},activeValue:function(){return this.$pcTabs.d_value},showNavigators:function(){return this.$pcTabs.showNavigators},prevButtonAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria.previous:void 0},nextButtonAriaLabel:function(){return this.$primevue.config.locale.aria?this.$primevue.config.locale.aria.next:void 0},dataP:function(){return P({scrollable:this.$pcTabs.scrollable})}},components:{ChevronLeftIcon:F,ChevronRightIcon:D},directives:{ripple:O}},J=["data-p"],X=["aria-label","tabindex"],Y=["data-p"],Z=["aria-orientation"],tt=["aria-label","tabindex"];function et(e,t,n,a,r,i){var o=C("ripple");return l(),p("div",s({ref:"list",class:e.cx("root"),"data-p":i.dataP},e.ptmi("root")),[i.showNavigators&&r.isPrevButtonEnabled?m((l(),p("button",s({key:0,ref:"prevButton",type:"button",class:e.cx("prevButton"),"aria-label":i.prevButtonAriaLabel,tabindex:i.$pcTabs.tabindex,onClick:t[0]||(t[0]=function(){return i.onPrevButtonClick&&i.onPrevButtonClick.apply(i,arguments)})},e.ptm("prevButton"),{"data-pc-group-section":"navigator"}),[(l(),B(y(i.templates.previcon||"ChevronLeftIcon"),s({"aria-hidden":"true"},e.ptm("prevIcon")),null,16))],16,X)),[[o]]):L("",!0),g("div",s({ref:"content",class:e.cx("content"),onScroll:t[1]||(t[1]=function(){return i.onScroll&&i.onScroll.apply(i,arguments)}),"data-p":i.dataP},e.ptm("content")),[g("div",s({ref:"tabs",class:e.cx("tabList"),role:"tablist","aria-orientation":i.$pcTabs.orientation||"horizontal"},e.ptm("tabList")),[h(e.$slots,"default"),g("span",s({ref:"inkbar",class:e.cx("activeBar"),role:"presentation","aria-hidden":"true"},e.ptm("activeBar")),null,16)],16,Z)],16,Y),i.showNavigators&&r.isNextButtonEnabled?m((l(),p("button",s({key:1,ref:"nextButton",type:"button",class:e.cx("nextButton"),"aria-label":i.nextButtonAriaLabel,tabindex:i.$pcTabs.tabindex,onClick:t[2]||(t[2]=function(){return i.onNextButtonClick&&i.onNextButtonClick.apply(i,arguments)})},e.ptm("nextButton"),{"data-pc-group-section":"navigator"}),[(l(),B(y(i.templates.nexticon||"ChevronRightIcon"),s({"aria-hidden":"true"},e.ptm("nextIcon")),null,16))],16,tt)),[[o]]):L("",!0)],16,J)}G.render=et;var at=`
    .p-tabs {
        display: flex;
        flex-direction: column;
    }

    .p-tablist {
        display: flex;
        position: relative;
        overflow: hidden;
        background: dt('tabs.tablist.background');
    }

    .p-tablist-viewport {
        overflow-x: auto;
        overflow-y: hidden;
        scroll-behavior: smooth;
        scrollbar-width: none;
        overscroll-behavior: contain auto;
    }

    .p-tablist-viewport::-webkit-scrollbar {
        display: none;
    }

    .p-tablist-tab-list {
        position: relative;
        display: flex;
        border-style: solid;
        border-color: dt('tabs.tablist.border.color');
        border-width: dt('tabs.tablist.border.width');
    }

    .p-tablist-content {
        flex-grow: 1;
    }

    .p-tablist-nav-button {
        all: unset;
        position: absolute !important;
        flex-shrink: 0;
        inset-block-start: 0;
        z-index: 2;
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: dt('tabs.nav.button.background');
        color: dt('tabs.nav.button.color');
        width: dt('tabs.nav.button.width');
        transition:
            color dt('tabs.transition.duration'),
            outline-color dt('tabs.transition.duration'),
            box-shadow dt('tabs.transition.duration');
        box-shadow: dt('tabs.nav.button.shadow');
        outline-color: transparent;
        cursor: pointer;
    }

    .p-tablist-nav-button:focus-visible {
        z-index: 1;
        box-shadow: dt('tabs.nav.button.focus.ring.shadow');
        outline: dt('tabs.nav.button.focus.ring.width') dt('tabs.nav.button.focus.ring.style') dt('tabs.nav.button.focus.ring.color');
        outline-offset: dt('tabs.nav.button.focus.ring.offset');
    }

    .p-tablist-nav-button:hover {
        color: dt('tabs.nav.button.hover.color');
    }

    .p-tablist-prev-button {
        inset-inline-start: 0;
    }

    .p-tablist-next-button {
        inset-inline-end: 0;
    }

    .p-tablist-prev-button:dir(rtl),
    .p-tablist-next-button:dir(rtl) {
        transform: rotate(180deg);
    }

    .p-tab {
        flex-shrink: 0;
        cursor: pointer;
        user-select: none;
        position: relative;
        border-style: solid;
        white-space: nowrap;
        gap: dt('tabs.tab.gap');
        background: dt('tabs.tab.background');
        border-width: dt('tabs.tab.border.width');
        border-color: dt('tabs.tab.border.color');
        color: dt('tabs.tab.color');
        padding: dt('tabs.tab.padding');
        font-weight: dt('tabs.tab.font.weight');
        transition:
            background dt('tabs.transition.duration'),
            border-color dt('tabs.transition.duration'),
            color dt('tabs.transition.duration'),
            outline-color dt('tabs.transition.duration'),
            box-shadow dt('tabs.transition.duration');
        margin: dt('tabs.tab.margin');
        outline-color: transparent;
    }

    .p-tab:not(.p-disabled):focus-visible {
        z-index: 1;
        box-shadow: dt('tabs.tab.focus.ring.shadow');
        outline: dt('tabs.tab.focus.ring.width') dt('tabs.tab.focus.ring.style') dt('tabs.tab.focus.ring.color');
        outline-offset: dt('tabs.tab.focus.ring.offset');
    }

    .p-tab:not(.p-tab-active):not(.p-disabled):hover {
        background: dt('tabs.tab.hover.background');
        border-color: dt('tabs.tab.hover.border.color');
        color: dt('tabs.tab.hover.color');
    }

    .p-tab-active {
        background: dt('tabs.tab.active.background');
        border-color: dt('tabs.tab.active.border.color');
        color: dt('tabs.tab.active.color');
    }

    .p-tabpanels {
        background: dt('tabs.tabpanel.background');
        color: dt('tabs.tabpanel.color');
        padding: dt('tabs.tabpanel.padding');
        outline: 0 none;
    }

    .p-tabpanel:focus-visible {
        box-shadow: dt('tabs.tabpanel.focus.ring.shadow');
        outline: dt('tabs.tabpanel.focus.ring.width') dt('tabs.tabpanel.focus.ring.style') dt('tabs.tabpanel.focus.ring.color');
        outline-offset: dt('tabs.tabpanel.focus.ring.offset');
    }

    .p-tablist-active-bar {
        z-index: 1;
        display: block;
        position: absolute;
        inset-block-end: dt('tabs.active.bar.bottom');
        height: dt('tabs.active.bar.height');
        background: dt('tabs.active.bar.background');
        transition: 250ms cubic-bezier(0.35, 0, 0.25, 1);
    }
`,nt={root:function(t){var n=t.props;return["p-tabs p-component",{"p-tabs-scrollable":n.scrollable}]}},it=k.extend({name:"tabs",style:at,classes:nt}),rt={name:"BaseTabs",extends:w,props:{value:{type:[String,Number],default:void 0},lazy:{type:Boolean,default:!1},scrollable:{type:Boolean,default:!1},showNavigators:{type:Boolean,default:!0},tabindex:{type:Number,default:0},selectOnFocus:{type:Boolean,default:!1}},style:it,provide:function(){return{$pcTabs:this,$parentInstance:this}}},st={name:"Tabs",extends:rt,inheritAttrs:!1,emits:["update:value"],data:function(){return{d_value:this.value}},watch:{value:function(t){this.d_value=t}},methods:{updateValue:function(t){this.d_value!==t&&(this.d_value=t,this.$emit("update:value",t))},isVertical:function(){return this.orientation==="vertical"}}};function ot(e,t,n,a,r,i){return l(),p("div",s({class:e.cx("root")},e.ptmi("root")),[h(e.$slots,"default")],16)}st.render=ot;export{U as a,st as b,G as s};
