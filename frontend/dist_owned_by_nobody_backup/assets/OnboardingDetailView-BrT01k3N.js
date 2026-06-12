import{B as F,o as d,c as u,q as C,a,d as M,N as W,Q as X,L as Q,R as U,b as r,h as l,t as c,e as o,I as J,g as D,f as Y,j as Z,r as b,G as ee,k as N,E as se}from"./index-C3KpH1wY.js";import{a as ne,s as I}from"./index-aFOqnJmW.js";import{s as m}from"./index-9lJD5ROw.js";import{s as te}from"./index-iLXUk_U6.js";import{s as ae}from"./index-DnAaMze0.js";import{s as re}from"./index-DBrRIz6y.js";import{s as S}from"./index-BcQm2ij7.js";import{s as B}from"./index-CZpmq5U5.js";import{a as g}from"./onboardingService-QL2Rj8uG.js";import"./index-BJ5IKAj0.js";import"./index-G5pdG3x2.js";import"./index-DCkuCQnz.js";import"./index-e2aSAaeR.js";var oe=`
    .p-progressspinner {
        position: relative;
        margin: 0 auto;
        width: 100px;
        height: 100px;
        display: inline-block;
    }

    .p-progressspinner::before {
        content: '';
        display: block;
        padding-top: 100%;
    }

    .p-progressspinner-spin {
        height: 100%;
        transform-origin: center center;
        width: 100%;
        position: absolute;
        top: 0;
        bottom: 0;
        left: 0;
        right: 0;
        margin: auto;
        animation: p-progressspinner-rotate 2s linear infinite;
    }

    .p-progressspinner-circle {
        stroke-dasharray: 89, 200;
        stroke-dashoffset: 0;
        stroke: dt('progressspinner.colorOne');
        animation:
            p-progressspinner-dash 1.5s ease-in-out infinite,
            p-progressspinner-color 6s ease-in-out infinite;
        stroke-linecap: round;
    }

    @keyframes p-progressspinner-rotate {
        100% {
            transform: rotate(360deg);
        }
    }
    @keyframes p-progressspinner-dash {
        0% {
            stroke-dasharray: 1, 200;
            stroke-dashoffset: 0;
        }
        50% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -35px;
        }
        100% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -124px;
        }
    }
    @keyframes p-progressspinner-color {
        100%,
        0% {
            stroke: dt('progressspinner.color.one');
        }
        40% {
            stroke: dt('progressspinner.color.two');
        }
        66% {
            stroke: dt('progressspinner.color.three');
        }
        80%,
        90% {
            stroke: dt('progressspinner.color.four');
        }
    }
`,ie={root:"p-progressspinner",spin:"p-progressspinner-spin",circle:"p-progressspinner-circle"},le=F.extend({name:"progressspinner",style:oe,classes:ie}),de={name:"BaseProgressSpinner",extends:ne,props:{strokeWidth:{type:String,default:"2"},fill:{type:String,default:"none"},animationDuration:{type:String,default:"2s"}},style:le,provide:function(){return{$pcProgressSpinner:this,$parentInstance:this}}},P={name:"ProgressSpinner",extends:de,inheritAttrs:!1,computed:{svgStyle:function(){return{"animation-duration":this.animationDuration}}}},ue=["fill","stroke-width"];function pe(i,$,h,L,n,y){return d(),u("div",C({class:i.cx("root"),role:"progressbar"},i.ptmi("root")),[(d(),u("svg",C({class:i.cx("spin"),viewBox:"25 25 50 50",style:y.svgStyle},i.ptm("spin")),[a("circle",C({class:i.cx("circle"),cx:"50",cy:"50",r:"20",fill:i.fill,"stroke-width":i.strokeWidth,strokeMiterlimit:"10"},i.ptm("circle")),null,16,ue)],16))],16)}P.render=pe;const ce={class:"ob-detail"},he={class:"ob-breadcrumb"},me={key:0,class:"ob-loading"},ve={class:"ob-card ob-header-card"},ye={class:"ob-header-info"},fe={class:"ob-header-name"},ge={class:"ob-header-meta"},_e={key:0,class:"ob-meta-sep"},be={class:"ob-header-buddy"},ke={class:"ob-header-status"},we={class:"ob-header-pct"},xe={class:"ob-action-bar"},Ce={class:"ob-card"},Se={key:0,class:"ob-muted"},Be={key:1,class:"ob-muted"},$e={key:2,class:"ob-card ob-empty"},Ge=M({__name:"OnboardingDetailView",setup(i){const $=Z(),h=W(),L=X(),n=b(null),y=b(!1),_=b(null),k=b([]),T=[{label:"Chờ",value:"pending"},{label:"Đang làm",value:"in_progress"},{label:"Xong",value:"done"},{label:"Bỏ qua",value:"skipped"}];Q(async()=>{var e;try{const s=await U.get("/users",{params:{page_size:200}}),v=((e=s.data)==null?void 0:e.items)??s.data??[];k.value=v.map(p=>({value:p.id,label:p.full_name}))}catch{}await w()});async function w(){y.value=!0;const e=Number($.params.employee_id);try{const s=await g.getByEmployee(e);n.value=s,_.value=s.buddy_user_id}catch{n.value=null}finally{y.value=!1}}async function H(){if(n.value)try{const e=await g.update(n.value.id,{buddy_user_id:_.value});n.value=e,h.add({severity:"success",summary:"Đã cập nhật buddy",life:2e3})}catch{h.add({severity:"error",summary:"Lỗi",detail:"Không thể cập nhật buddy",life:3e3})}}async function x(e,s){if(n.value)try{const v=await g.updateItem(n.value.id,e.id,{status:s.status??e.status,assignee_user_id:s.assignee_user_id!==void 0?s.assignee_user_id:e.assignee_user_id,note:s.note!==void 0?s.note:e.note}),p=n.value.items.findIndex(t=>t.id===e.id);p>=0&&(n.value.items[p]=v),await w()}catch{h.add({severity:"error",summary:"Lỗi",detail:"Không thể cập nhật task",life:3e3})}}function K(e,s){s!==(e.note??"")&&x(e,{note:s||null})}async function R(){if(!n.value)return;const e=n.value.items.filter(s=>s.status!=="done"&&s.status!=="skipped");if(e.length!==0)try{await Promise.all(e.map(s=>g.updateItem(n.value.id,s.id,{status:"done",assignee_user_id:s.assignee_user_id,note:s.note}))),await w()}catch{h.add({severity:"error",summary:"Lỗi",detail:"Không thể cập nhật tất cả task",life:3e3})}}function q(){L.require({message:"Bạn có chắc muốn hủy checklist này?",header:"Xác nhận hủy",icon:"pi pi-exclamation-triangle",acceptLabel:"Hủy checklist",rejectLabel:"Đóng",accept:async()=>{if(n.value)try{const e=await g.update(n.value.id,{status:"cancelled"});n.value=e,h.add({severity:"info",summary:"Đã hủy checklist",life:3e3})}catch{h.add({severity:"error",summary:"Lỗi",detail:"Không thể hủy checklist",life:3e3})}}})}function V(e){return new Date(e).toLocaleDateString("vi-VN")}function z(e){return new Date(e).toLocaleString("vi-VN")}function E(e){return e==="in_progress"?"Đang thực hiện":e==="completed"?"Hoàn thành":e==="cancelled"?"Đã hủy":e}function G(e){return e==="in_progress"?"warn":e==="completed"?"success":e==="cancelled"?"danger":"secondary"}function O(e){return e==="admin"?"Hành chính":e==="it"?"IT":e==="training"?"Đào tạo":e==="specialty"?"Chuyên môn":e}function j(e){return e==="admin"?"secondary":e==="it"?"info":e==="training"?"warn":e==="specialty"?"success":"secondary"}function A(e){return e.is_overdue?"ob-row-overdue":""}return(e,s)=>{var p;const v=ee("RouterLink");return d(),u("div",ce,[a("nav",he,[r(v,{to:"/employees"},{default:l(()=>[...s[1]||(s[1]=[N("Nhân viên",-1)])]),_:1}),s[3]||(s[3]=a("i",{class:"pi pi-chevron-right"},null,-1)),r(v,{to:"/employees/onboarding"},{default:l(()=>[...s[2]||(s[2]=[N("Tiếp nhận nhân viên mới",-1)])]),_:1}),s[4]||(s[4]=a("i",{class:"pi pi-chevron-right"},null,-1)),a("span",null,c(((p=n.value)==null?void 0:p.employee_name)??"..."),1)]),y.value?(d(),u("div",me,[r(o(P),{style:{width:"40px",height:"40px"}})])):n.value?(d(),u(J,{key:1},[a("div",ve,[a("div",ye,[a("div",fe,c(n.value.employee_name),1),a("div",ge,[r(o(B),{value:n.value.employee_code,severity:"secondary"},null,8,["value"]),n.value.department_name?(d(),u("span",_e,"·")):D("",!0),a("span",null,c(n.value.department_name??""),1),s[5]||(s[5]=a("span",{class:"ob-meta-sep"},"·",-1)),a("span",null,"Vào làm: "+c(V(n.value.start_date)),1)]),a("div",be,[s[6]||(s[6]=a("span",{class:"ob-label"},"Buddy:",-1)),r(o(S),{modelValue:_.value,"onUpdate:modelValue":s[0]||(s[0]=t=>_.value=t),options:k.value,"option-label":"label","option-value":"value",placeholder:"Chưa có buddy","show-clear":"",style:{width:"220px"},onChange:H},null,8,["modelValue","options"])])]),a("div",ke,[a("div",we,c(n.value.completion_pct.toFixed(0))+"%",1),r(o(re),{value:n.value.completion_pct,style:{height:"10px",width:"200px"}},null,8,["value"]),r(o(B),{value:E(n.value.status),severity:G(n.value.status),style:{"margin-top":"0.5rem"}},null,8,["value","severity"])])]),a("div",xe,[r(o(I),{label:"Đánh dấu tất cả hoàn thành",icon:"pi pi-check-circle",severity:"success",outlined:"",disabled:n.value.status!=="in_progress",onClick:R},null,8,["disabled"]),n.value.status==="in_progress"?(d(),Y(o(I),{key:0,label:"Hủy checklist",icon:"pi pi-times",severity:"danger",outlined:"",onClick:q})):D("",!0)]),a("div",Ce,[r(o(te),{value:n.value.items,size:"small","striped-rows":"","row-class":A},{empty:l(()=>[...s[7]||(s[7]=[a("div",{class:"ob-empty"},"Không có task nào",-1)])]),default:l(()=>[r(o(m),{header:"Task","min-header-width":"200px"},{body:l(({data:t})=>[a("div",null,c(t.task_name),1)]),_:1}),r(o(m),{header:"Nhóm",style:{width:"110px"}},{body:l(({data:t})=>[r(o(B),{value:O(t.task_group),severity:j(t.task_group)},null,8,["value","severity"])]),_:1}),r(o(m),{header:"Phụ trách",style:{width:"180px"}},{body:l(({data:t})=>[r(o(S),{"model-value":t.assignee_user_id,options:k.value,"option-label":"label","option-value":"value",placeholder:"Chưa phân công","show-clear":"",style:{width:"170px"},disabled:n.value.status!=="in_progress",onChange:f=>x(t,{status:t.status,assignee_user_id:f.value})},null,8,["model-value","options","disabled","onChange"])]),_:1}),r(o(m),{header:"Hạn",style:{width:"110px"}},{body:l(({data:t})=>[a("span",{class:se(t.is_overdue?"ob-overdue":"")},c(V(t.due_date)),3)]),_:1}),r(o(m),{header:"Trạng thái",style:{width:"150px"}},{body:l(({data:t})=>[r(o(S),{"model-value":t.status,options:T,"option-label":"label","option-value":"value",style:{width:"140px"},disabled:n.value.status!=="in_progress",onChange:f=>x(t,{status:f.value})},null,8,["model-value","disabled","onChange"])]),_:1}),r(o(m),{header:"Ghi chú",style:{width:"180px"}},{body:l(({data:t})=>[r(o(ae),{"model-value":t.note??"",placeholder:"Ghi chú...",style:{width:"170px"},disabled:n.value.status!=="in_progress",onBlur:f=>K(t,f.target.value)},null,8,["model-value","disabled","onBlur"])]),_:1}),r(o(m),{header:"Hoàn thành lúc",style:{width:"150px"}},{body:l(({data:t})=>[t.completed_at?(d(),u("span",Se,c(z(t.completed_at)),1)):(d(),u("span",Be,"—"))]),_:1})]),_:1},8,["value"])])],64)):(d(),u("div",$e,"Không tìm thấy checklist cho nhân viên này."))])}}});export{Ge as default};
