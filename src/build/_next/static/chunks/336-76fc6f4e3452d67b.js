"use strict";(self.webpackChunk_N_E=self.webpackChunk_N_E||[]).push([[336],{8516:function(e,s,t){t.d(s,{JT:function(){return d},ZP:function(){return u},am:function(){return m}});var l=t(7437),r=t(2265),a=t(4307),n=t(4630),i=t(9124),o=t(2871),c=t(408);let d=(0,r.createContext)(),m=e=>{let{children:s}=e,[t,a]=(0,r.useState)(null);return(0,r.useEffect)(()=>{let e=localStorage.getItem("profile");console.debug("restored profile:",e),a(e?JSON.parse(e):null)},[]),(0,l.jsx)(d.Provider,{value:{profile:t,setProfile:e=>{localStorage.setItem("profile",JSON.stringify(e)),console.debug("saved profile to localStorage:",JSON.stringify(e)),a(e)}},children:s})};function u(e){let{selectedProfile:s,setSelectedProfile:t}=e,{profiles:r,error:d,isLoading:m}=(0,c.nw)();return m?(0,l.jsx)("div",{children:"Loading profiles..."}):d?(0,l.jsx)("div",{children:"Error!"}):0===r.length?(0,l.jsx)("div",{children:"No profiles found."}):(0,l.jsxs)(a.Ri,{value:s,onChange:t,children:[(0,l.jsx)(n.__,{className:"mt-2 block text-sm font-medium leading-6 text-gray-900",children:"Profile"}),s&&!r.map(e=>e.name).includes(s.name)&&(0,l.jsx)("div",{children:"Profile is missing."}),(0,l.jsxs)("div",{className:"relative mt-2 mb-2",children:[(0,l.jsx)(a.Y4,{className:"relative w-full cursor-default rounded-md bg-white py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6",children:(0,l.jsxs)("span",{className:"flex items-center",children:[(0,l.jsx)("span",{className:"ml-3 block truncate",children:s?s.name:""}),(0,l.jsxs)("span",{className:"ml-2 text-slate-400 text-sm font-light",children:["@",s?s.host?s.host:"localhost":""]}),(0,l.jsx)("span",{className:"pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2",children:(0,l.jsx)(i.Z,{className:"h-5 w-5 text-gray-400","aria-hidden":"true"})})]})}),(0,l.jsx)(a.O_,{className:"absolute z-10 mt-1 max-h-60 overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm w-[var(--button-width)]",anchor:"bottom",children:r.map(e=>(0,l.jsxs)(a.wt,{value:e,className:"group flex gap-2 bg-white data-[focus]:bg-blue-500 data-[focus]:text-white relative cursor-default select-none py-2 pl-1 pr-9 text-gray-900",children:[(0,l.jsx)("div",{className:"flex",children:(0,l.jsx)("span",{className:"ml-3 block truncate font-normal data-[selected]:font-semibold",children:e.name})}),(0,l.jsxs)("span",{className:"ml-1 text-slate-400 text-sm font-light data-[selected]:text-gray-100",children:["@",e.host?e.host:"localhost"]}),(0,l.jsx)("span",{className:"invisible group-data-[selected]:visible absolute inset-y-0 right-0 flex items-center pr-4 group-data-[focus]:text-white text-blue-600",children:(0,l.jsx)(o.Z,{className:"size-5"})})]},e.name))})]})]})}},1888:function(e,s,t){t.d(s,{Z:function(){return p}});var l=t(7437),r=t(2265),a=t(4307),n=t(4630),i=t(5926),o=t(2530),c=t(9124),d=t(2871),m=t(408),u=t(3175);function x(){for(var e=arguments.length,s=Array(e),t=0;t<e;t++)s[t]=arguments[t];return s.filter(Boolean).join(" ")}let h=["STOPPED","EXPIRED"];function f(e){let{selectedService:s,setSelectedService:t,profile:f,image:g}=e,{services:p,error:b,isLoading:j}=(0,m.Su)(f,g);return b?(0,l.jsx)("div",{className:"rounded-md bg-red-50 border-red-100 ring-1 ring-red-300 p-4 mt-2 mb-4",children:(0,l.jsxs)("div",{className:"flex",children:[(0,l.jsx)("div",{className:"flex-shrink-0",children:(0,l.jsx)(u.Z,{"aria-hidden":"true",className:"size-5 text-red-500"})}),(0,l.jsxs)("div",{className:"ml-3",children:[(0,l.jsx)("h3",{className:"text-sm font-medium text-red-800",children:"Failed to fetch services"}),(0,l.jsx)("div",{className:"mt-2 font-light text-sm text-red-800",children:(0,l.jsx)("p",{children:"We ran into an issue while fetching the services available for this profile."})})]})]})}):j?(0,l.jsx)("div",{className:"animate-pulse rounded-md bg-gray-100 p-4 mt-2 mb-4 h-72"}):0===p.length?(0,l.jsx)("div",{className:"rounded-md bg-yellow-50 border-yellow-100 ring-1 ring-yellow-300 p-4 mt-2 mb-4",children:(0,l.jsxs)("div",{className:"flex",children:[(0,l.jsx)("div",{className:"flex-shrink-0",children:(0,l.jsx)(o.Z,{"aria-hidden":"true",className:"h-5 w-5 text-yellow-400"})}),(0,l.jsxs)("div",{className:"ml-3",children:[(0,l.jsx)("h3",{className:"text-sm font-medium text-yellow-800",children:"No services available"}),(0,l.jsx)("div",{className:"mt-2 font-light text-sm text-yellow-800",children:(0,l.jsx)("p",{children:"Click on the button below to create a new service under the selected profile."})})]})]})}):(0,l.jsx)(a.Ri,{value:s,onChange:t,children:e=>{let{open:t}=e;return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)(n.__,{className:"pt-2 block text-sm font-medium leading-6 text-gray-900",children:"Services"}),(0,l.jsxs)("div",{className:"relative mt-2",children:[(0,l.jsxs)(a.Y4,{className:"relative w-full cursor-default rounded-md bg-white py-1.5 pl-3 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6",children:[(0,l.jsxs)("span",{className:"flex items-center",children:[s&&(0,l.jsx)("span",{"aria-label":"HEALTHY"===s.status?"Online":"Offline",className:x(h.includes(s.status)?"bg-gray-200":"HEALTHY"===s.status?"bg-green-500":"TIMEOUT"===s.status||"FAILED"===s.status?"bg-red-500":"SUBMITTED"===s.status?"bg-yellow-500":"STARTING"===s.status||"PENDING"===s.status?"animate-pulse bg-green-500":"bg-transparent border border-gray-300","inline-block h-2 w-2 flex-shrink-0 rounded-full")}),(0,l.jsx)("span",{className:"ml-3 block truncate",children:s?s.name:""})]}),(0,l.jsx)("span",{className:"pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2",children:(0,l.jsx)(c.Z,{className:"h-5 w-5 text-gray-400","aria-hidden":"true"})})]}),(0,l.jsx)(i.u,{show:t,as:r.Fragment,leave:"transition ease-in duration-100",leaveFrom:"opacity-100",leaveTo:"opacity-0",children:(0,l.jsx)(a.O_,{className:"absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm",children:p.map(e=>(0,l.jsx)(a.wt,{className:e=>{let{focus:s}=e;return x(s?"bg-blue-500 text-white":"text-gray-900","relative cursor-default select-none py-2 pl-3 pr-9")},value:e,children:s=>{let{selected:t,focus:r}=s;return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsxs)("div",{className:"flex items-center",children:[(0,l.jsx)("span",{className:x(h.includes(e.status)?"bg-gray-200":"HEALTHY"===e.status?"bg-green-500":"TIMEOUT"===e.status||"FAILED"===e.status?"bg-red-500":"SUBMITTED"===e.status?"bg-yellow-500":"STARTING"===e.status||"PENDING"===e.status?"animate-pulse bg-green-500":"bg-transparent border border-gray-300","inline-block h-2 w-2 flex-shrink-0 rounded-full"),"aria-hidden":"true"}),(0,l.jsxs)("span",{className:x(t?"font-semibold":"font-normal","ml-3 block truncate"),children:[e.name,(0,l.jsxs)("span",{className:"sr-only",children:[" ","is"," ","HEALTHY"===e.status?"online":"offline"]})]})]}),t?(0,l.jsx)("span",{className:x(r?"text-white":"text-blue-600","absolute inset-y-0 right-0 flex items-center pr-4"),children:(0,l.jsx)(d.Z,{className:"h-5 w-5","aria-hidden":"true"})}):null]})}},e.id))})})]})]})}})}var g=t(2828);function p(e){let{selectedService:s,setSelectedService:t,profile:r,image:a,children:n}=e;return(0,l.jsxs)("div",{children:[(0,l.jsx)(f,{selectedService:s,setSelectedService:t,profile:r,image:a}),(0,l.jsx)(g.Z,{service:s,setSelectedService:t,profile:r,image:a}),n]})}},2819:function(e,s,t){t.d(s,{Z:function(){return Z}});var l=t(7437),r=t(2265);t(9376);var a=t(5926),n=t(4405),i=t(2828),o=t(2530);function c(e){let{header:s,message:t}=e;return(0,l.jsx)("div",{className:"border-l-4 border-yellow-400 bg-yellow-50 p-4",children:(0,l.jsxs)("div",{className:"flex",children:[(0,l.jsx)("div",{className:"flex-shrink-0",children:(0,l.jsx)(o.Z,{className:"h-5 w-5 text-yellow-400","aria-hidden":"true"})}),(0,l.jsx)("div",{className:"ml-3",children:(0,l.jsxs)("p",{className:"text-sm text-yellow-700",children:[s+" ",(0,l.jsx)("div",{className:"font-light text-yellow-700 hover:text-yellow-600",children:t})]})})]})})}var d=t(1677);function m(e){let{header:s,message:t}=e;return(0,l.jsx)("div",{className:"border-l-4 border-blue-400 bg-blue-50 p-4",children:(0,l.jsxs)("div",{className:"flex",children:[(0,l.jsx)("div",{className:"flex-shrink-0",children:(0,l.jsx)(d.Z,{className:"h-5 w-5 text-blue-400","aria-hidden":"true"})}),(0,l.jsx)("div",{className:"ml-3",children:(0,l.jsxs)("div",{className:"text-sm text-blue-600",children:[s+" ",(0,l.jsx)("div",{className:"font-light text-blue-600 hover:text-blue-500",children:t})]})})]})})}var u=t(7472),x=t(4307),h=t(4630),f=t(9124),g=t(2871);function p(){for(var e=arguments.length,s=Array(e),t=0;t<e;t++)s[t]=arguments[t];return s.filter(Boolean).join(" ")}function b(e){let{models:s,setRepoId:t,disabled:n}=e,[i,o]=(0,r.useState)(null),c=s.filter((e,s,t)=>t.map(e=>e.repo_id).indexOf(e.repo_id)===s);return((0,r.useEffect)(()=>{i&&t(i.repo_id)},[i,t]),(0,r.useEffect)(()=>{s&&s.length>0?o(s[0]):o(null)},[s]),null===i)?(0,l.jsx)(l.Fragment,{}):(0,l.jsx)(u.g,{disabled:n,children:(0,l.jsx)(x.Ri,{value:i,onChange:function(e){console.debug("handleRepoChange:",e),o(e)},children:e=>{let{open:s}=e;return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)(h.__,{className:"block text-sm font-medium leading-6 text-gray-900",children:"Model"}),(0,l.jsxs)("div",{className:"relative mt-2",children:[(0,l.jsxs)(x.Y4,{className:p(n?"bg-gray-100 ring-gray-300 ring-1":"bg-white focus:outline-none focus:ring-2 focus:ring-blue-500","relative w-full cursor-default rounded-md py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 sm:text-sm sm:leading-6"),children:[(0,l.jsx)("span",{className:"flex items-center",children:(0,l.jsx)("span",{className:"ml-2 mr-2 block truncate",children:i.repo_id})}),!n&&(0,l.jsx)("span",{className:"pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2",children:(0,l.jsx)(f.Z,{className:"h-5 w-5 text-gray-400","aria-hidden":"true"})})]}),(0,l.jsx)(a.u,{show:s,as:r.Fragment,leave:"transition ease-in duration-100",leaveFrom:"opacity-100",leaveTo:"opacity-0",children:(0,l.jsx)(x.O_,{className:"absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm",children:c.map(e=>(0,l.jsx)(x.wt,{className:e=>{let{focus:s}=e;return p(s?"bg-blue-500 text-white":"text-gray-900","relative cursor-default select-none py-2 pl-1 pr-9")},value:e,children:s=>{let{selected:t,focus:r}=s;return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)("div",{className:"flex items-center",children:(0,l.jsx)("span",{className:p(t?"font-semibold":"font-normal","ml-3 block truncate"),children:e.repo_id})}),t?(0,l.jsx)("span",{className:p(r?"text-white":"text-blue-600","absolute inset-y-0 right-0 flex items-center pr-4"),children:(0,l.jsx)(g.Z,{className:"h-5 w-5","aria-hidden":"true"})}):null]})}},e.revision))})})]})]})}})})}function j(){for(var e=arguments.length,s=Array(e),t=0;t<e;t++)s[t]=arguments[t];return s.filter(Boolean).join(" ")}function v(e){let{models:s,repoId:t,setModel:n,disabled:i}=e,[o,c]=(0,r.useState)(null),d=s.filter(e=>e.repo_id===t);return((0,r.useEffect)(()=>{let e=s.filter(e=>e.repo_id===t);e&&e.length>0?c(e[0]):c(null)},[s,t]),(0,r.useEffect)(()=>{o&&n(o)},[o,n]),null===o)?(0,l.jsx)(l.Fragment,{}):(0,l.jsx)(u.g,{disabled:i,children:(0,l.jsx)(x.Ri,{value:o,onChange:function(e){console.debug("handleRevisionChange:",e),c(e)},children:e=>{let{open:s}=e;return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)(h.__,{className:"block text-sm font-medium leading-6 text-gray-900",children:"Revision"}),(0,l.jsxs)("div",{className:"relative mt-2",children:[(0,l.jsxs)(x.Y4,{className:j(i?"bg-gray-100 ring-gray-300 ring-1":"bg-white focus:outline-none focus:ring-2 focus:ring-blue-500","relative w-full cursor-default rounded-md py-1.5 pl-1 pr-10 text-left text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 sm:text-sm sm:leading-6"),children:[(0,l.jsx)("span",{className:"flex items-center",children:(0,l.jsx)("span",{className:"ml-2 mr-2 block truncate",children:o.revision})}),!i&&(0,l.jsx)("span",{className:"pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2",children:(0,l.jsx)(f.Z,{className:"h-5 w-5 text-gray-400","aria-hidden":"true"})})]}),(0,l.jsx)(a.u,{show:s,as:r.Fragment,leave:"transition ease-in duration-100",leaveFrom:"opacity-100",leaveTo:"opacity-0",children:(0,l.jsx)(x.O_,{className:"absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm",children:d.map(e=>(0,l.jsx)(x.wt,{className:e=>{let{focus:s}=e;return j(s?"bg-blue-500 text-white":"text-gray-900","relative cursor-default select-none py-2 pl-1 pr-9")},value:e,children:s=>{let{selected:t,focus:r}=s;return(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)("div",{className:"flex items-center",children:(0,l.jsx)("span",{className:j(t?"font-semibold":"font-normal","ml-3 block truncate"),children:e.revision})}),t?(0,l.jsx)("span",{className:j(r?"text-white":"text-blue-600","absolute inset-y-0 right-0 flex items-center pr-4"),children:(0,l.jsx)(g.Z,{className:"h-5 w-5","aria-hidden":"true"})}):null]})}},e.revision))})})]})]})}})})}var y=t(6824);let N=e=>{if(""===e)return"";let[s,t,l]=e.split(":").map(e=>Number.parseInt(e));return 60*s+t},w=e=>Math.min(Math.max(Math.ceil(e/36),1),4);function k(e){let{models:s,services:t,setModel:a,jobOptions:n,setJobOptions:i,setValidationErrors:o,disabled:d,profile:u,children:x}=e,[h,f]=r.useState(null);return u?(0,l.jsxs)("div",{className:"max-w-2xl space-y-6 md:col-span-2",children:[(0,l.jsx)("fieldset",{children:(0,l.jsx)(y.Z,{type:"text",label:"Name",help:"Give your service a name (or use our wonderful suggestion).",value:n.name,setValue:e=>{i(s=>({...s,name:e}))},validate:e=>(function(e,s){if(s.map(e=>e.name).includes(e)){let e={message:"Name is already in use by another service.",ok:!1};return o(s=>({...s,name:e})),e}return o(e=>({...e,name:null})),{ok:!0}})(e,t),disabled:d})}),(0,l.jsx)("fieldset",{children:(0,l.jsx)(b,{models:s,repoId:h,setRepoId:f,disabled:d})}),(0,l.jsx)("fieldset",{children:(0,l.jsx)(v,{models:s,repoId:h,setModel:a,disabled:d})}),"slurm"===u.type?(0,l.jsxs)(l.Fragment,{children:[(0,l.jsxs)("fieldset",{children:[(0,l.jsx)("legend",{className:"text-sm font-semibold leading-6 text-gray-900",children:"Time"}),(0,l.jsx)("p",{className:"mt-1 text-sm leading-6 text-gray-600",children:"How long would you like to run this model?"}),(0,l.jsx)("div",{className:"mt-3 space-y-3",children:(0,l.jsx)(y.Z,{type:"number",units:"minutes",disabled:d,value:N(n.time),setValue:e=>{i({...n,time:""===e?e:"00:".concat(String(e).padStart(2,"0"),":00")})},validate:function(e){let s=Number(String(e).trim());if(Number.isInteger(s)&&""!==s){if(s<1){let e={message:"Time should be greater than or equal to 1.",ok:!1};return o(s=>({...s,time:e})),e}if(s>180){let e={message:"Time should be less than 180.",ok:!1};return o(s=>({...s,time:e})),e}}else{let e={message:"Time should be a valid positive integer.",ok:!1};return o(s=>({...s,time:e})),e}return o(e=>({...e,time:null})),{ok:!0}}})})]}),(0,l.jsxs)("fieldset",{children:[(0,l.jsx)("legend",{className:"text-sm font-semibold leading-6 text-gray-900",children:"Resources"}),(0,l.jsx)("p",{className:"mt-1 text-sm leading-6 text-gray-600",children:"Request resources for the model."}),(0,l.jsx)("div",{className:"mt-2 text-sm font-medium inline-flex",children:(0,l.jsx)(c,{header:"Warning",message:"Changing the settings below may cause your service to fail or over utilize resources."})}),(0,l.jsxs)("div",{className:"mt-6 space-y-3",children:[(0,l.jsx)(y.Z,{type:"number",disabled:d,label:"CPU",units:"cores",value:n.ntasks_per_node,setValue:e=>{console.debug("setCPUCores:",e),i(s=>({...s,ntasks_per_node:e}))},validate:function(e){let s=Number(String(e).trim());if(Number.isInteger(s)){if(s<8){let e={message:"CPU cores should be greater than or equal to 8.",ok:!1};return o(s=>({...s,cpus:e})),e}if(s>128){let e={message:"CPU cores should be less than 128.",ok:!1};return o(s=>({...s,cpus:e})),e}}else{let e={message:"CPU cores should be a valid integer.",ok:!1};return o(s=>({...s,cpus:e})),e}return o(e=>({...e,cpus:null})),{ok:!0}}}),(0,l.jsx)(y.Z,{type:"number",disabled:d,label:"Memory",units:"GB",value:n.mem,setValue:e=>{i(s=>({...s,mem:e,gres:s.gres>0?w(e):0}))},validate:function(e){let s=Number(String(e).trim());if(Number.isInteger(s)){if(s<8){let e={message:"Memory should be a greater than or equal to 8 GB.",ok:!1};return o(s=>({...s,meme:e})),e}if(s>256){let e={message:"Memory should be less than 256.",ok:!1};return o(s=>({...s,meme:e})),e}}else{let e={message:"Memory should be a valid integer.",ok:!1};return o(s=>({...s,meme:e})),e}return{ok:!0}}}),(0,l.jsxs)("div",{className:"relative flex gap-x-3",children:[(0,l.jsx)("div",{className:"flex h-6 items-center",children:(0,l.jsx)("input",{id:"gpu-checkbox",name:"gpu-checkbox",type:"checkbox",disabled:d,checked:n.gres>0,onChange:()=>{console.log("onChange:",n.gres),n.gres>0?i(e=>({...e,gres:0})):i(e=>({...e,gres:w(e.mem)}))},className:"h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-500 disabled:bg-gray-100"})}),(0,l.jsxs)("div",{className:"text-sm leading-6",children:[(0,l.jsx)("label",{htmlFor:"offers",className:"font-medium text-gray-900",children:"Accelerate"}),(0,l.jsx)("p",{className:"text-gray-500",children:"Use GPUs to accelerate inference. Recommended for most models."})]})]})]})]})]}):(0,l.jsx)(l.Fragment,{children:(0,l.jsxs)("fieldset",{children:[(0,l.jsx)("legend",{className:"text-sm font-semibold leading-6 text-gray-900",children:"Resources"}),(0,l.jsx)("p",{className:"mt-1 text-sm leading-6 text-gray-600",children:"Request resources for the model."}),(0,l.jsx)("div",{className:"mt-2 text-sm font-medium inline-flex",children:(0,l.jsx)(m,{header:"Note",message:"Services running locally can utilize all CPU, memory and GPU resources made available through the container provider and will run until stopped."})}),(0,l.jsx)("div",{className:"mt-6 space-y-3",children:(0,l.jsxs)("div",{className:"relative flex gap-x-3",children:[(0,l.jsx)("div",{className:"flex h-6 items-center",children:(0,l.jsx)("input",{id:"gpu-checkbox",name:"gpu-checkbox",type:"checkbox",disabled:d,checked:n.gres>0,onChange:()=>{console.log("onChange:",n.gres),n.gres>0?i(e=>({...e,gres:0})):i(e=>({...e,gres:1}))},className:"h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-500 disabled:bg-gray-100"})}),(0,l.jsxs)("div",{className:"text-sm leading-6",children:[(0,l.jsx)("label",{htmlFor:"offers",className:"font-medium text-gray-900",children:"Accelerate"}),(0,l.jsx)("p",{className:"text-gray-500",children:"Use GPUs to accelerate inference. Recommended for most models."})]})]})})]})}),x]}):(0,l.jsx)(l.Fragment,{})}var _=t(1586),E=t(6332);function T(e){let{error:s,onClick:t}=e;return(0,l.jsx)("div",{className:"rounded-md bg-red-50 p-4 mb-4",children:(0,l.jsxs)("div",{className:"flex",children:[(0,l.jsx)("div",{className:"shrink-0",children:(0,l.jsx)(_.Z,{"aria-hidden":"true",className:"h-5 w-5 text-red-400"})}),(0,l.jsxs)("div",{className:"ml-3",children:[(0,l.jsx)("h3",{className:"text-sm font-medium text-red-800",children:"Failed to launch service."}),(0,l.jsx)("div",{className:"mt-2 text-sm text-red-700",children:(0,l.jsx)("ul",{role:"list",className:"list-disc space-y-1 pl-5",children:(0,l.jsx)("li",{children:s.message})})})]}),(0,l.jsx)("div",{className:"ml-auto pl-3",children:(0,l.jsx)("div",{className:"-mx-1.5 -my-1.5",children:(0,l.jsxs)("button",{type:"button",onClick:t,className:"inline-flex rounded-md bg-red-50 p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50",children:[(0,l.jsx)("span",{className:"sr-only",children:"Dismiss"}),(0,l.jsx)(E.Z,{"aria-hidden":"true",className:"h-5 w-5"})]})})})]})})}var S=t(3347),C=t(408);let F=function(){let e=arguments.length>0&&void 0!==arguments[0]?arguments[0]:0;return new Promise(s=>setTimeout(s,e))};function P(){return"blackfish-".concat(1e4+Math.floor(11e3*Math.random()))}function Z(e){let{open:s,setOpen:t,defaultContainerOptions:o,containerOptions:c,setContainerOptions:d,launchSuccess:m,setLaunchSuccess:u,isLaunching:x,setIsLaunching:h,launchError:f,setLaunchError:g,validationErrors:p,setValidationErrors:b,selectedService:j,setSelectedService:v,profile:y,image:N,children:w}=e,_=r.useMemo(()=>({name:P(),time:"00:30:00",ntasks_per_node:8,mem:16,gres:1,partition:null,constraint:null}),[]),{services:E,servicesIsLoading:Z,servicesError:D,mutate:I}=(0,C.Su)(y,N),{models:O,modelsIsLoading:M,modelsError:U}=(0,C.bP)(y,N),[A,R]=r.useState({..._,name:P()}),[L,G]=(0,r.useState)(null);(0,r.useEffect)(()=>{O&&O.length>0&&G(O[0])},[O]),(0,r.useEffect)(()=>{s&&(R({..._,name:P()}),d({...o}),u(!1),h(!1),g(null),b({}))},[s,d,_,o,u,g,h,b]);let z=(0,r.useRef)(null),H=async()=>{console.debug("start service button clicked"),h(!0),g(null);let e=await (0,S.UY)(N,L,A,c,y);if(!e.ok){let s=Error("A service request failed with message:",await e.text());console.error(s),h(!1),g(s);return}let s=await e.json();console.debug("created service: ",s.id);for(let e=0;e<3;e+=1){await F(5e3);try{let e=await (0,S.uv)(s.id);console.debug("found service:",e),v(e),await I(),h(!1),u(!0);break}catch(s){if(2===e){let e=Error("Maximum wait time (".concat(15," seconds) exceeded."));console.error(e),h(!1),g(e)}else console.debug("service details not found: re-trying in ".concat(5," seconds (attempts left: ").concat(3-e,")."))}}};return Z||M?(0,l.jsx)("div",{children:"Loading..."}):D||U?(0,l.jsx)("div",{children:"Error!"}):(0,l.jsx)(a.u,{show:s,as:r.Fragment,children:(0,l.jsxs)(n.Vq,{as:"div",className:"relative z-10",initialFocus:z,onClose:()=>{t(!1)},children:[(0,l.jsx)(a.x,{as:r.Fragment,enter:"ease-out duration-300",enterFrom:"opacity-0",enterTo:"opacity-100",leave:"ease-in duration-200",leaveFrom:"opacity-100",leaveTo:"opacity-0",children:(0,l.jsx)("div",{className:"fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"})}),(0,l.jsx)("div",{className:"fixed inset-0 z-10 w-screen overflow-y-auto",children:(0,l.jsx)("div",{className:"flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0",children:(0,l.jsx)(a.x,{as:r.Fragment,enter:"ease-out duration-300",enterFrom:"opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95",enterTo:"opacity-100 translate-y-0 sm:scale-100",leave:"ease-in duration-200",leaveFrom:"opacity-100 translate-y-0 sm:scale-100",leaveTo:"opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95",children:(0,l.jsxs)(n.EM,{className:"relative transform overflow-hidden rounded-lg bg-white px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-4xl sm:p-6 sm:pl-6",children:[(0,l.jsx)("div",{children:(0,l.jsxs)("div",{children:[(0,l.jsx)(n.$N,{as:"h3",className:"text-base font-semibold leading-6 text-gray-900"}),f&&(0,l.jsx)(T,{error:f,onClick:()=>g(null)}),(0,l.jsx)("form",{className:"mt-2",children:(0,l.jsx)("div",{className:"space-y-4",children:(0,l.jsxs)("div",{className:"grid grid-cols-1 gap-x-12 gap-y-10 border-b border-gray-900/10 pb-12 md:grid-cols-3",children:[(0,l.jsxs)("div",{children:[(0,l.jsx)("h2",{className:"text-base font-semibold leading-7 text-gray-900",children:"Summary"}),x?(0,l.jsx)("div",{className:"flex justify-center items-center h-48",children:(0,l.jsxs)("span",{className:"relative flex h-5 w-5",children:[(0,l.jsx)("span",{className:"animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"}),(0,l.jsx)("span",{className:"relative inline-flex rounded-full h-5 w-5 bg-blue-500"})]})}):(0,l.jsx)(i.Z,{service:m?j:{model:L?L.repo_id:null,name:A.name,status:null,created_at:null,updated_at:null,host:y?"local"===y.type?"localhost":y.host:null,port:null,ntasks_per_node:y?"local"===y.type?null:A.ntasks_per_node:null,mem:y?"local"===y.type?null:A.mem:null,gres:A.gres},setSelectedService:v,profile:y,image:N})]}),(0,l.jsx)(k,{models:O,services:E,setModel:G,jobOptions:A,setJobOptions:R,setValidationErrors:b,disabled:x||f||m,profile:y,children:w})]})})})]})}),m?(0,l.jsx)("div",{className:"mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3",children:(0,l.jsx)("button",{type:"button",className:"mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:col-span-2 sm:mt-0",onClick:()=>{t(!1)},ref:z,children:"Close"})}):(0,l.jsxs)("div",{className:"mt-5 sm:mt-6 sm:grid sm:grid-flow-row-dense sm:grid-cols-2 sm:gap-3",children:[(0,l.jsx)("button",{type:"button",className:"inline-flex w-full justify-center rounded-md bg-blue-500 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 sm:col-start-2 disabled:bg-blue-200",onClick:H,disabled:!Object.values(p).every(e=>null===e)||x,children:"Launch"}),(0,l.jsx)("button",{type:"button",className:"mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:col-start-1 sm:mt-0",onClick:()=>t(!1),ref:z,children:"Cancel"})]})]})})})})]})})}},6824:function(e,s,t){t.d(s,{Z:function(){return n}});var l=t(7437),r=t(2265),a=t(5402);function n(e){let{label:s,help:t,units:n,placeholder:i,value:o,setValue:c,validate:d,type:m,disabled:u}=e,x=r.useMemo(()=>d(o),[o]),[h,f]=r.useState(x.ok),[g,p]=r.useState(x.message||"");return(0,l.jsxs)("div",{children:[(0,l.jsx)("label",{htmlFor:"email",className:"block text-sm font-medium leading-6 text-gray-900",children:s}),t&&(0,l.jsx)("p",{className:"mt-1 text-sm leading-6 text-gray-600",children:t}),(0,l.jsxs)("div",{className:"relative mt-2 rounded-md shadow-sm",children:[(0,l.jsx)("input",{type:m,disabled:u,className:function(){for(var e=arguments.length,s=Array(e),t=0;t<e;t++)s[t]=arguments[t];return s.filter(Boolean).join(" ")}(h?"ring-blue-400 focus:ring-blue-500":"text-red-600 ring-red-300 placeholder:text-red-300 focus:ring-red-600","block w-full rounded-md border-0 py-1.5 pr-10 ring-inset focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6 disabled:bg-gray-100 disabled:ring-1 disabled:ring-gray-300 ring-1"),placeholder:i,value:o,onChange:e=>{c(e.target.value);let s=d(e.target.value);s.ok?(f(!0),p(null)):(f(!1),p(s.message))},"aria-invalid":"true","aria-describedby":"email-error"}),h&&(0,l.jsx)("span",{className:"pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 font-light italic text-sm text-slate-500",children:n}),!h&&(0,l.jsx)("div",{className:"pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3",children:(0,l.jsx)(a.Z,{className:"h-5 w-5 text-red-600","aria-hidden":"true"})})]}),!h&&(0,l.jsx)("p",{className:"mt-2 text-sm text-red-600",id:"email-error",children:g})]})}},2828:function(e,s,t){t.d(s,{Z:function(){return p}});var l=t(7437),r=t(2265),a=t(9055),n=t(3365),i=t(322),o=t(8059),c=t(1331),d=t(8159),m=t(3354),u=t(3347),x=t(408);let h=[null,void 0,"STOPPED","TIMEOUT","EXPIRED","FAILED"],f=(e,s)=>{let t=Math.abs(s-e),l=t%1e3,r=(t=(t-l)/1e3)%60,a=(t=(t-r)/60)%60,n=(t=(t-a)/60)%24,i=(t-n)/24;return i>0?"".concat(i," days ").concat(a," min"):n>0?"".concat(n," hr ").concat(a," min"):a>0?"".concat(a," min ").concat(r," sec"):"".concat(r," sec")},g=e=>{let{refTime:s}=e,[t,a]=r.useState(new Date),n=()=>setTimeout(()=>{a(new Date),n()},3e4);return n(),(0,l.jsx)("div",{children:f(s,t)})};function p(e){let{service:s,setSelectedService:t,profile:f,image:p}=e,b=s?!h.includes(s.status):null,{services:j,mutate:v}=(0,x.Su)(f,p),[y,N]=r.useState(!1),w=async()=>{console.debug("stop button clicked: ",s.id),N(!0);try{await (0,u.Pp)(s.id),t({...s,status:"STOPPED"}),await v()}catch(e){console.error("An error occurred while stopping a service:",e)}N(!1)},k=e=>1===j.length?null:0===j.map(e=>e.id).indexOf(e.id)?j[1]:j[0],_=async()=>{console.debug("delete button clicked: ",s.id),N(!0);let e=k(s);try{await (0,u.wo)(s.id),console.debug("setting service:",e),t(e),await v()}catch(e){console.log("An error occurred while deleting a service:",e)}N(!1)};return s?(0,l.jsx)("div",{className:" flex flex-row justify-start",children:(0,l.jsxs)("div",{className:"grow flex flex-col justify-center mt-2 mb-0",children:[(0,l.jsxs)("div",{className:"mt-2 ml-1 font-light text-sm sm:flex sm:flex-col",children:[(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex justify-start items-center",children:[(0,l.jsx)(a.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"Model "}),s.model]}),(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex justify-start items-center capitalize",children:[(0,l.jsx)(n.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"Status "}),y?(0,l.jsx)("div",{className:"bg-gray-300 rounded-md h-4 w-28 animate-pulse"}):(0,l.jsx)("div",{className:"STARTING"===s.status?"animate-pulse":"",children:s.status?s.status.toLowerCase():"-"})]}),(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex items-center",children:[(0,l.jsx)(i.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"Time "}),s.created_at&&b?(0,l.jsx)(g,{refTime:new Date(s.created_at),currentTime:new Date}):"-"]}),(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex items-center",children:[(0,l.jsx)(o.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"Host "}),s.host&&b?s.port?"".concat(s.host,":").concat(s.port):s.host:"-"]}),(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex items-center",children:[(0,l.jsx)(c.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"Cores "}),s.ntasks_per_node||"-"]}),(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex items-center",children:[(0,l.jsx)(d.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"Memory "}),s.mem||"-"]}),(0,l.jsxs)("div",{className:"mb-1 ml-0 inline-flex items-center",children:[(0,l.jsx)(m.Z,{className:"h-6 w-6 text-gray-600 mr-1"}),(0,l.jsx)("div",{className:"grow font-medium text-sm mr-1",children:"GPU "}),s.gres?s.gres>0?"\uD83D\uDD25".repeat(s.gres):"\uD83E\uDDCA":"-"]})]}),s.updated_at?(0,l.jsxs)("div",{className:"grow text-center mt-2 font-light text-xs mb-4",children:["Last updated",(0,l.jsx)(g,{refTime:new Date(s.updated_at),currentTime:new Date})]}):(0,l.jsx)("div",{className:"grow text-center mt-2 font-light text-xs mb-2",children:(0,l.jsx)("div",{})}),b&&(0,l.jsx)("div",{className:"mb-1",children:(0,l.jsx)("button",{type:"button",className:"w-full flex flex-row justify-center gap-x-2 rounded-md bg-transparent px-3.5 py-1.5 text-sm font-regular shadow-sm hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 border",onClick:w,children:"Stop"})}),"PENDING"===s.status&&(0,l.jsx)("div",{className:"mb-1",children:(0,l.jsx)("button",{type:"button",className:"w-full flex flex-row justify-center gap-x-2 rounded-md bg-transparent px-3.5 py-1.5 text-sm font-regular shadow-sm hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 border",onClick:w,children:"Cancel"})}),!b&&(0,l.jsx)("div",{className:"mb-1",children:(0,l.jsx)("button",{type:"button",className:"w-full flex flex-row justify-center gap-x-2 rounded-md bg-transparent px-3.5 py-1.5 text-sm font-regular shadow-sm hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 border",onClick:_,children:"Delete"})})]})}):(0,l.jsx)("div",{children:"No service selected."})}},9657:function(e,s,t){t.d(s,{Z:function(){return l}});function l(){return"http://".concat("localhost",":").concat("8000","/api")}},408:function(e,s,t){t.d(s,{Su:function(){return n},bP:function(){return a},nw:function(){return i},of:function(){return o}});var l=t(3861),r=t(3347);let a=(e,s)=>{let{data:t,error:a,isLoading:n}=(0,l.ZP)("models?profile=".concat(e?e.name:"default","&image=").concat(s),r.fm);return{models:t,error:a,isLoading:n}},n=(e,s)=>{let{data:t,error:a,isLoading:n,mutate:i}=(0,l.ZP)("services?profile=".concat(e?e.name:"default","&image=").concat(s.replace("-","_")),r.Qz,{refreshInterval:1e4}),o=["HEALTHY","STARTING","PENDING","SUBMITTED","STOPPED","EXPIRED","TIMEOUT","FAILED"];return{services:t?[...t].sort((e,s)=>{let t=o.indexOf(e.status)-o.indexOf(s.status);return 0!==t?t:new Date(s.created_at)-new Date(e.created_at)}):[],error:a,isLoading:n,mutate:i}},i=()=>{let{data:e,error:s,isLoading:t,mutate:a}=(0,l.ZP)("profiles",r.lU);return{profiles:e,error:s,isLoading:t,mutate:a}},o=e=>{let{data:s,error:t,isLoading:a,mutate:n}=(0,l.ZP)(e?"files?path=".concat(e):null,r.uB);return{files:s,error:t,isLoading:a,refresh:n}}},3347:function(e,s,t){t.d(s,{Pp:function(){return m},Qz:function(){return n},UY:function(){return o},fm:function(){return a},lU:function(){return i},uB:function(){return r},uv:function(){return d},wo:function(){return u}});let l=(0,t(9657).Z)();async function r(e){let s=await fetch("".concat(l,"/").concat(e));if(!s.ok){let e=Error("Failed to fetch files.");throw e.status=s.status,console.error(e),e}return s.json()}async function a(e){let s=await fetch("".concat(l,"/").concat(e,"&refresh=true"));if(!s.ok){let e=Error("Failed to fetch models.");throw e.status=s.status,console.error(e),e}return(await s.json()).map(e=>({repo_id:e.repo,revision:e.revision,profile:e.profile,image:e.image,model_dir:e.model_dir}))}async function n(e){let s=await fetch("".concat(l,"/").concat(e));if(!s.ok){let e=Error("Failed to fetch services.");throw e.status=s.status,console.error(e),e}return await s.json()}async function i(){let e=await fetch("".concat(l,"/profiles"));if(!e.ok){console.log("Failed to fetch profiles.");let s=Error("Failed to fetch profiles.");throw s.status=e.status,console.log(s),s}return await e.json()}async function o(e,s,t,r,a){let n;if("slurm"===a.type)n={name:t.name,image:e.replace("-","_"),model:s.repo_id,profile:a.name,job_type:"slurm",host:a.host,user:a.user,job_options:t,container_options:{...r,revision:s.revision,model_dir:"speech-recognition"===e?c(s.model_dir):s.model_dir}};else if("local"===a.type){let i=await fetch("".concat(l,"/ports"));if(!i.ok){let e=Error("Unable to find available local port");throw e.status=i.status,e}let o=await i.json();n={name:t.name,image:e.replace("-","_"),model:s.repo_id,profile:a.name,job_type:"local",host:"localhost",job_options:{},container_options:{...r,revision:s.revision,model_dir:"speech-recognition"===e?c(s.model_dir):s.model_dir,port:o}}}else throw Error("Unsupported job profile type: ".concat(a.type));return console.debug("body:",n),await fetch("".concat(l,"/services"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(n)})}function c(e){let s=e.split("/"),t=s.length;return s.slice(0,t-1).join("/")}async function d(e){let s=await fetch("".concat(l,"/services/").concat(e),{method:"GET",headers:{"Content-Type":"application/json"},mode:"cors"});if(!s.ok)throw Error("Failed to get service details.");return s.json()}async function m(e){let s=JSON.stringify({delay:0}),t=await fetch("".concat(l,"/services/").concat(e,"/stop"),{method:"PUT",headers:{"Content-Type":"application/json"},mode:"cors",body:s});if(!t.ok)throw Error("Failed to stop the service");return t.json()}async function u(e){let s=JSON.stringify({force:!1});if(!(await fetch("".concat(l,"/services/").concat(e),{method:"DELETE",headers:{"Content-Type":"application/json"},mode:"cors",body:s})).ok)throw Error("Failed to delete the service")}}}]);