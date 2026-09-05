const state={chatHistory:[],isProcessing:false,currentMerchant:null,latestOptions:[],checkoutInProgress:false,currentCheckout:null};
const API_BASE="/api";

document.addEventListener("DOMContentLoaded",()=>{
    initAgentDrawer();
    initChatListeners();
    initAsciiBackground();
    if(typeof lucide!=="undefined"&&typeof lucide.createIcons==="function")lucide.createIcons();
});

function initAgentDrawer(){
    const drawer=document.getElementById("agent-drawer");
    const open=document.getElementById("open-agent-btn");
    const heroOpen=document.getElementById("hero-open-agent-btn");
    const close=document.getElementById("close-agent-btn");
    if(!drawer)return;
    const openHub=()=>{
        drawer.classList.remove("translate-x-full");
        drawer.style.transform="translateX(0)";
        document.body.style.overflow="hidden";
        setTimeout(()=>document.getElementById("chat-input")?.focus(),350);
    };
    const closeHub=()=>{
        drawer.classList.add("translate-x-full");
        drawer.style.transform="translateX(100%)";
        document.body.style.overflow="";
    };
    drawer.classList.add("translate-x-full");
    drawer.style.transform="translateX(100%)";
    open?.addEventListener("click",openHub);
    heroOpen?.addEventListener("click",openHub);
    close?.addEventListener("click",closeHub);
    document.addEventListener("keydown",e=>{
        if(e.key==="Escape")closeHub();
    });
}

function initChatListeners(){
    const form=document.getElementById("chat-form");
    const input=document.getElementById("chat-input");
    if(!form||!input)return;
    form.addEventListener("submit",async e=>{
        e.preventDefault();
        const message=input.value.trim();
        if(!message||state.isProcessing||state.checkoutInProgress)return;
        input.value="";
        await handleSendMessage(message);
    });
}

function displayValue(value){
    if(value===null||value===undefined)return"";
    if(typeof value==="string")return value;
    if(typeof value==="number"||typeof value==="boolean")return String(value);
    if(typeof value==="object"){
        if(typeof value.message==="string")return value.message;
        if(value.food_name){
            const amount=value.amount??value.total_inr;
            return amount!==undefined&&amount!==null?`Checkout created for ${value.food_name} — ₹${amount}`:`Checkout created for ${value.food_name}`;
        }
        if(value.error)return String(value.error);
        return"Action completed successfully.";
    }
    return String(value);
}

function tryParseJSON(value){
    if(typeof value!=="string")return value;
    const trimmed=value.trim();
    if(!trimmed.startsWith("{")&&!trimmed.startsWith("["))return value;
    try{return JSON.parse(trimmed)}catch{return value}
}

function isCheckoutResponse(data){
    if(!data||typeof data!=="object"||Array.isArray(data))return false;
    const orderId=data.razorpay_order_id||data.order_id;
    const key=data.razorpay_key_id||data.key_id;
    const validOrder=!!orderId;
    const validKey=!!key;
    const created=data.status==="created";
    const food=data.type==="food_checkout"&&data.success===true;
    const generic=data.type==="razorpay_checkout"&&data.success!==false;
    return validOrder&&validKey&&(created||food||generic);
}

function findAction(data,depth=0){
    if(!data||depth>8)return null;
    data=tryParseJSON(data);
    if(isCheckoutResponse(data))return data;
    if(Array.isArray(data))return data;
    if(typeof data!=="object")return null;
    const keys=["action_data","action","data","response","answer","result","message"];
    for(const key of keys){
        if(data[key]===undefined||data[key]===null)continue;
        const value=tryParseJSON(data[key]);
        if(isCheckoutResponse(value))return value;
        if(Array.isArray(value))return value;
        if(typeof value==="object"){
            const nested=findAction(value,depth+1);
            if(nested)return nested;
        }
    }
    if(Array.isArray(data.products))return data;
    return null;
}

function extractAssistantText(data){
    if(!data)return"";
    data=tryParseJSON(data);
    if(isCheckoutResponse(data)){
        const items=Array.isArray(data.item_summaries)?data.item_summaries:[];
        const amount=data.total_inr??data.amount??null;
        if(items.length&&amount!==null)return`Preparing checkout for ${items.join(", ")} — ₹${amount}`;
        if(data.food_name&&amount!==null)return`Preparing checkout for ${data.food_name} — ₹${amount}`;
        if(data.food_name)return`Preparing checkout for ${data.food_name}`;
        if(amount!==null)return`Preparing your ₹${amount} checkout.`;
        return"Preparing your checkout.";
    }
    if(typeof data==="string")return data;
    if(typeof data.text==="string")return data.text;
    if(typeof data.response==="string")return data.response;
    if(typeof data.message==="string")return data.message;
    if(typeof data.answer==="string")return data.answer;
    return"";
}

async function handleSendMessage(messageText){
    state.isProcessing=true;
    toggleInputState(true);
    appendChatMessage("user",messageText);
    state.chatHistory.push({role:"user",content:messageText});
    const typingId=appendTypingIndicator();
    try{
        const response=await fetch(`${API_BASE}/chat`,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({message:messageText,history:state.chatHistory})
        });
        removeTypingIndicator(typingId);
        if(!response.ok)throw new Error(`Server returned status code ${response.status}`);
        let data=await response.json();
        console.log("Agent response:",data);
        data=tryParseJSON(data);
        const action=findAction(data);
        if(action&&isCheckoutResponse(action)){
            const checkoutMessage=extractAssistantText(action);
            if(checkoutMessage)appendChatMessage("assistant",checkoutMessage);
            state.chatHistory.push({role:"model",content:checkoutMessage||"Checkout initiated."});
            state.currentCheckout=action;
            handleActionData(action);
            return;
        }
        const assistantText=extractAssistantText(data);
        if(assistantText){
            appendChatMessage("assistant",assistantText);
            state.chatHistory.push({role:"model",content:assistantText});
        }
        if(action)handleActionData(action);
    }catch(error){
        removeTypingIndicator(typingId);
        console.error("Chat error:",error);
        appendChatMessage("assistant",`⚠️ Error processing request: ${error.message}`);
    }finally{
        state.isProcessing=false;
        toggleInputState(false);
    }
}

function appendChatMessage(role,content){
    const chatWindow=document.getElementById("chat-window");
    if(!chatWindow)return;
    const wrapper=document.createElement("div");
    wrapper.className=`flex flex-col space-y-1 max-w-[88%] message-animate ${role==="user"?"ml-auto items-end":"items-start"}`;
    const bubble=document.createElement("div");
    bubble.className=role==="user"?"user-message":"assistant-message";
    const body=document.createElement("p");
    body.className="leading-relaxed whitespace-pre-wrap";
    body.innerText=displayValue(content);
    const tag=document.createElement("span");
    tag.className="text-[10px] text-slate-500 font-mono uppercase px-1";
    tag.innerText=role==="user"?"YOU":"SYSTEM AGENT • ACTIVE";
    bubble.appendChild(body);
    wrapper.appendChild(bubble);
    wrapper.appendChild(tag);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop=chatWindow.scrollHeight;
}

function appendImageMessage(imageUrl,title="",subtitle=""){
    if(!imageUrl)return;
    const chatWindow=document.getElementById("chat-window");
    if(!chatWindow)return;
    const wrapper=document.createElement("div");
    wrapper.className="flex flex-col space-y-1 max-w-[88%] message-animate items-start";
    const card=document.createElement("div");
    card.className="overflow-hidden rounded-2xl bg-slate-900 border border-slate-700 shadow-xl w-[240px]";
    const image=document.createElement("img");
    image.src=imageUrl;
    image.alt=title||"Checkout item";
    image.className="w-full h-36 object-cover";
    image.loading="lazy";
    image.onerror=()=>image.remove();
    card.appendChild(image);
    if(title||subtitle){
        const info=document.createElement("div");
        info.className="p-3";
        if(title){
            const heading=document.createElement("div");
            heading.className="text-sm font-bold text-white";
            heading.innerText=title;
            info.appendChild(heading);
        }
        if(subtitle){
            const small=document.createElement("div");
            small.className="text-xs text-slate-400 mt-1";
            small.innerText=subtitle;
            info.appendChild(small);
        }
        card.appendChild(info);
    }
    wrapper.appendChild(card);
    const tag=document.createElement("span");
    tag.className="text-[10px] text-slate-500 font-mono uppercase px-1";
    tag.innerText="SYSTEM AGENT • ACTIVE";
    wrapper.appendChild(tag);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop=chatWindow.scrollHeight;
}

function appendCheckoutCard(actionData){
    if(!actionData)return;
    const chatWindow=document.getElementById("chat-window");
    if(!chatWindow)return;
    const merchant=actionData.merchant||"Razorpay";
    const amount=actionData.total_inr??actionData.amount??null;
    const items=Array.isArray(actionData.item_summaries)?actionData.item_summaries:[];
    const images=Array.isArray(actionData.image_urls)?actionData.image_urls.filter(Boolean):[];
    const wrapper=document.createElement("div");
    wrapper.className="flex flex-col space-y-1 max-w-[90%] message-animate items-start";
    const card=document.createElement("div");
    card.className="bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden shadow-xl w-[270px]";
    if(images.length){
        const image=document.createElement("img");
        image.src=images[0];
        image.alt=items[0]||"Checkout item";
        image.className="w-full h-40 object-cover";
        image.loading="lazy";
        image.onerror=()=>image.remove();
        card.appendChild(image);
    }
    const content=document.createElement("div");
    content.className="p-4";
    const merchantLabel=document.createElement("div");
    merchantLabel.className="text-[9px] uppercase tracking-widest text-slate-500 font-mono";
    merchantLabel.innerText=merchant;
    content.appendChild(merchantLabel);
    const title=document.createElement("div");
    title.className="text-white font-bold text-sm mt-1";
    title.innerText=items.length?items.join(", "):actionData.food_name||"Payment checkout";
    content.appendChild(title);
    if(amount!==null){
        const price=document.createElement("div");
        price.className="text-emerald-400 text-lg font-black mt-2";
        price.innerText=`₹${amount}`;
        content.appendChild(price);
    }
    const status=document.createElement("div");
    status.className="flex items-center gap-2 mt-3 text-xs text-emerald-400";
    status.innerHTML='<span class="w-2 h-2 rounded-full bg-emerald-400"></span>Secure Razorpay checkout';
    content.appendChild(status);
    card.appendChild(content);
    wrapper.appendChild(card);
    const tag=document.createElement("span");
    tag.className="text-[10px] text-slate-500 font-mono uppercase px-1";
    tag.innerText="SYSTEM AGENT • CHECKOUT";
    wrapper.appendChild(tag);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop=chatWindow.scrollHeight;
}

function appendTypingIndicator(){
    const chatWindow=document.getElementById("chat-window");
    if(!chatWindow)return null;
    const id=`typing-${Date.now()}`;
    const wrapper=document.createElement("div");
    wrapper.id=id;
    wrapper.className="flex flex-col space-y-1 max-w-[85%] message-animate items-start";
    wrapper.innerHTML='<div class="bg-drawer-panel text-slate-400 p-3 rounded-2xl rounded-tl-none border border-drawer-border shadow-sm text-xs flex items-center space-x-2"><span class="font-mono">Agent thinking</span><span class="animate-bounce">.</span><span class="animate-bounce">.</span><span class="animate-bounce">.</span></div>';
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop=chatWindow.scrollHeight;
    return id;
}

function removeTypingIndicator(id){
    if(id)document.getElementById(id)?.remove();
}

function toggleInputState(disabled){
    const input=document.getElementById("chat-input");
    const button=document.getElementById("send-btn");
    if(input)input.disabled=disabled;
    if(button)button.disabled=disabled;
}

function handleActionData(actionData){
    if(!actionData)return;
    if(Array.isArray(actionData)){
        renderProductGrid(actionData);
        return;
    }
    if(actionData.products&&Array.isArray(actionData.products)){
        renderProductGrid(actionData.products);
    }
    if(actionData.razorpay_order_id||actionData.order_id){
        triggerRazorpayCheckout(actionData);
    }
}
function renderProductGrid(products){
    const grid=document.getElementById("product-grid");
    if(!grid)return;
    grid.innerHTML="";
    if(!Array.isArray(products)||!products.length){
        grid.innerHTML='<div class="flex flex-col items-center justify-center h-full opacity-40 py-8 text-center"><p class="text-xs font-medium text-slate-400">No products found for this query.</p></div>';
        return;
    }
    state.latestOptions=[...products];
    products.forEach((prod,index)=>{
        const card=document.createElement("div");
        card.className="product-card rounded-xl overflow-hidden shadow-lg flex flex-col justify-between p-3 space-y-3";
        const img=prod.image_url||prod.image||"";
        const name=escapeHtml(prod.name||"Product");
        const merchant=escapeHtml(prod.merchant||state.currentMerchant||"Store");
        const category=escapeHtml(prod.category||"General");
        const price=escapeHtml(String(prod.price??""));
        const productId=prod.id??prod.sku??null;
        const imageHtml=img?`<img src="${escapeHtml(img)}" alt="${name}" class="w-full h-full object-cover" loading="lazy" onerror="this.style.display='none'">`:'<div class="w-full h-full flex items-center justify-center text-slate-600 text-xl">◈</div>';
        card.innerHTML=`<div class="flex space-x-3"><div class="relative h-16 w-16 flex-shrink-0 rounded-lg overflow-hidden bg-slate-950">${imageHtml}</div><div class="flex-1 min-w-0"><div class="flex items-center justify-between gap-2"><span class="px-2 py-0.5 text-[9px] font-black uppercase rounded text-white ${getMerchantBadgeColor(prod.merchant||state.currentMerchant||"")}">${merchant}</span><span class="text-xs font-bold text-emerald-400">₹${price}</span></div><h4 class="font-bold text-slate-100 text-xs truncate mt-1" title="${name}">${name}</h4><p class="text-[10px] text-slate-500 capitalize">${category}</p></div></div><button class="buy-product-btn w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition-colors shadow flex items-center justify-center space-x-1" ${productId===null?"disabled":""}><span>${productId===null?"Unavailable":"Buy Now"}</span></button>`;
        const button=card.querySelector(".buy-product-btn");
        if(button&&productId!==null)button.addEventListener("click",()=>directCheckout(productId));
        grid.appendChild(card);
    });
}

function escapeHtml(value){
    return String(value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;");
}

function getMerchantBadgeColor(merchant=""){
    const m=merchant.toLowerCase();
    if(m.includes("zomato"))return"bg-red-600";
    if(m.includes("swiggy"))return"bg-orange-600";
    if(m.includes("pvr"))return"bg-yellow-600";
    return"bg-slate-700";
}

function directCheckout(productId){
    if(productId===null||productId===undefined||productId===""){
        appendChatMessage("assistant","❌ This option does not have a valid product ID.");
        return;
    }
    const input=document.getElementById("chat-input");
    const form=document.getElementById("chat-form");
    if(!input||!form)return;
    input.value=`Checkout product ${productId}`;
    form.dispatchEvent(new Event("submit",{bubbles:true,cancelable:true}));
}

function triggerRazorpayCheckout(actionData){
    console.log("RAZORPAY ACTION:",actionData);
    const key=actionData.razorpay_key_id||actionData.key_id;
    const orderId=actionData.razorpay_order_id||actionData.order_id;
    const amount=actionData.amount_paise||actionData.total_paise;
    if(!key){
        appendChatMessage("assistant","❌ Razorpay Key ID was not returned by the server.");
        console.error("Missing Razorpay key:",actionData);
        return;
    }
    if(!orderId){
        appendChatMessage("assistant","❌ Razorpay Order ID was not returned by the server.");
        console.error("Missing Razorpay order ID:",actionData);
        return;
    }
    if(!amount||Number(amount)<=0){
        appendChatMessage("assistant","❌ Invalid Razorpay amount.");
        console.error("Invalid Razorpay amount:",actionData);
        return;
    }
    if(typeof Razorpay==="undefined"){
        appendChatMessage("assistant","❌ Razorpay Checkout SDK is not loaded. Refresh the page and try again.");
        console.error("Razorpay SDK missing");
        return;
    }
    const options={
        key:key,
        amount:Number(amount),
        currency:actionData.currency||"INR",
        name:actionData.merchant||"Razorpay Agentic Payment Hub",
        description:actionData.food_name||((actionData.item_summaries||[]).join(", "))||"Food Order",
        order_id:orderId,
        prefill:{name:"Customer"},
        theme:{color:"#2563EB"},
        handler:async function(response){
            console.log("Razorpay payment response:",response);
            await verifyPayment(response);
        },
        modal:{
            ondismiss:function(){
                console.log("Razorpay checkout closed");
            }
        }
    };
    try{
        const rzp=new Razorpay(options);
        rzp.on("payment.failed",function(response){
            console.error("Razorpay payment failed:",response.error);
            appendChatMessage("assistant","❌ Payment failed. Please try again.");
        });
        rzp.open();
    }catch(error){
        console.error("Razorpay open error:",error);
        appendChatMessage("assistant",`❌ Unable to open Razorpay Checkout: ${error.message}`);
    }
}

async function verifyPayment(rzpResponse){
    if(!rzpResponse?.razorpay_order_id||!rzpResponse?.razorpay_payment_id||!rzpResponse?.razorpay_signature){
        appendChatMessage("assistant","❌ Razorpay returned incomplete payment information.");
        return;
    }
    try{
        const response=await fetch(`${API_BASE}/verify-payment`,{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({
                razorpay_order_id:rzpResponse.razorpay_order_id,
                razorpay_payment_id:rzpResponse.razorpay_payment_id,
                razorpay_signature:rzpResponse.razorpay_signature
            })
        });
        if(!response.ok)throw new Error(`Server returned ${response.status}`);
        const result=await response.json();
        console.log("Payment verification result:",result);
        if(result.success===true&&result.verified===true){
            appendPaymentSuccessCard(rzpResponse);
        }else{
            appendChatMessage("assistant",`❌ ${displayValue(result.message)||"Payment verification failed."}`);
        }
    }catch(error){
        console.error("Payment verification error:",error);
        appendChatMessage("assistant",`❌ Payment verification error: ${error.message}`);
    }
}

function appendPaymentSuccessCard(rzpResponse){
    const chatWindow=document.getElementById("chat-window");
    if(!chatWindow)return;
    const wrapper=document.createElement("div");
    wrapper.className="flex flex-col space-y-1 max-w-[90%] message-animate items-start";
    const card=document.createElement("div");
    card.className="bg-slate-900 border border-emerald-500/30 rounded-2xl p-4 shadow-xl w-[280px]";
    card.innerHTML=`<div class="flex items-center gap-3"><div class="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center"><span class="text-emerald-400 text-xl">✓</span></div><div><div class="text-white font-bold text-sm">Payment Verified</div><div class="text-emerald-400 text-[10px] uppercase tracking-wider font-mono">Transaction successful</div></div></div><div class="mt-4 pt-3 border-t border-slate-700"><div class="text-[9px] text-slate-500 uppercase font-mono">Order</div><div class="text-xs text-slate-300 font-mono truncate mt-1">${escapeHtml(rzpResponse.razorpay_order_id)}</div><div class="text-[9px] text-slate-500 uppercase font-mono mt-3">Payment</div><div class="text-xs text-slate-300 font-mono truncate mt-1">${escapeHtml(rzpResponse.razorpay_payment_id)}</div></div>`;
    wrapper.appendChild(card);
    const tag=document.createElement("span");
    tag.className="text-[10px] text-slate-500 font-mono uppercase px-1";
    tag.innerText="SYSTEM AGENT • VERIFIED";
    wrapper.appendChild(tag);
    chatWindow.appendChild(wrapper);
    chatWindow.scrollTop=chatWindow.scrollHeight;
}

function initAsciiBackground(){
    const hero=document.getElementById("hero-section");
    if(!hero)return;
    let canvas=document.getElementById("ascii-background");
    if(!canvas){
        canvas=document.createElement("canvas");
        canvas.id="ascii-background";
        hero.prepend(canvas);
    }
    hero.style.position="relative";
    hero.style.overflow="hidden";
    canvas.style.position="absolute";
    canvas.style.inset="0";
    canvas.style.width="100%";
    canvas.style.height="100%";
    canvas.style.pointerEvents="none";
    canvas.style.zIndex="0";
    Array.from(hero.children).forEach(child=>{
        if(child!==canvas){
            child.style.position="relative";
            child.style.zIndex="1";
        }
    });
    const ctx=canvas.getContext("2d");
    if(!ctx)return;
    let width=0,height=0,dpr=1,particles=[];
    const characters=["0","1","0","1","·","•",".",":","+","*","#","@","░","▒"];
    const mouse={x:-1000,y:-1000,active:false};
    function resizeCanvas(){
        const rect=hero.getBoundingClientRect();
        width=Math.max(1,Math.floor(rect.width));
        height=Math.max(1,Math.floor(rect.height));
        dpr=Math.min(window.devicePixelRatio||1,2);
        canvas.width=width*dpr;
        canvas.height=height*dpr;
        canvas.style.width=`${width}px`;
        canvas.style.height=`${height}px`;
        ctx.setTransform(dpr,0,0,dpr,0,0);
        createButterfly();
    }
    function butterflyShape(t){
        const value=Math.exp(Math.cos(t))-2*Math.cos(4*t)-Math.pow(Math.sin(t/12),5);
        return{x:Math.sin(t)*value,y:Math.cos(t)*value};
    }
    function createButterfly(){
        particles=[];
        const centerX=width*0.78;
        const centerY=height*0.49;
        const scale=Math.min(width,height)*0.115;
        const particleCount=width<700?550:1800;
        for(let i=0;i<particleCount;i++){
            const t=Math.random()*Math.PI*16;
            const shape=butterflyShape(t);
            const onShape=Math.random()<0.82;
            const spread=onShape?Math.random()*0.20:Math.random()*1.8;
            let x=centerX+shape.x*scale+(Math.random()-0.5)*spread*scale;
            let y=centerY+shape.y*scale+(Math.random()-0.5)*spread*scale;
            x=Math.max(-30,Math.min(width+30,x));
            y=Math.max(-30,Math.min(height+30,y));
            particles.push({
                baseX:x,
                baseY:y,
                char:characters[Math.floor(Math.random()*characters.length)],
                size:Math.random()*5+5,
                phase:Math.random()*Math.PI*2,
                speed:Math.random()*0.8+0.4,
                brightness:Math.random(),
                strong:Math.random()<0.3
            });
        }
    }
    function drawGlow(){
        const centerX=width*0.78;
        const centerY=height*0.49;
        const radius=Math.min(width,height)*0.48;
        const gradient=ctx.createRadialGradient(centerX,centerY,0,centerX,centerY,radius);
        gradient.addColorStop(0,"rgba(37,99,235,0.14)");
        gradient.addColorStop(0.2,"rgba(59,130,246,0.09)");
        gradient.addColorStop(0.45,"rgba(96,165,250,0.045)");
        gradient.addColorStop(0.7,"rgba(147,197,253,0.02)");
        gradient.addColorStop(1,"rgba(255,255,255,0)");
        ctx.fillStyle=gradient;
        ctx.fillRect(0,0,width,height);
    }
    function drawButterfly(time){
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        const rect=hero.getBoundingClientRect();
        const mouseX=mouse.x-rect.left;
        const mouseY=mouse.y-rect.top;
        for(const p of particles){
            let x=p.baseX+Math.sin(time*0.0008*p.speed+p.phase)*2.5;
            let y=p.baseY+Math.cos(time*0.0007*p.speed+p.phase)*2.5;
            if(mouse.active){
                const dx=x-mouseX;
                const dy=y-mouseY;
                const distance=Math.sqrt(dx*dx+dy*dy);
                const radius=140;
                if(distance<radius){
                    const force=(radius-distance)/radius;
                    x+=(dx/(distance||1))*force*30;
                    y+=(dy/(distance||1))*force*30;
                }
            }
            const flicker=Math.sin(time*0.0025+p.phase)*0.5+0.5;
            const alpha=p.strong?0.5+flicker*0.4:0.25+flicker*0.35;
            ctx.font=`${p.size}px monospace`;
            ctx.fillStyle=`rgba(37,99,235,${alpha})`;
            ctx.shadowColor=p.strong?"rgba(37,99,235,0.7)":"transparent";
            ctx.shadowBlur=p.strong?8:0;
            ctx.fillText(p.char,x,y);
        }
        ctx.shadowBlur=0;
    }
    function drawAmbientCharacters(time){
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.font="11px monospace";
        const amount=width<768?40:110;
        for(let i=0;i<amount;i++){
            const x=width*(0.52+Math.random()*0.47);
            const y=Math.random()*height;
            const flicker=Math.sin(time*0.0015+i*1.7)*0.5+0.5;
            ctx.fillStyle=`rgba(59,130,246,${0.06+flicker*0.1})`;
            ctx.shadowBlur=0;
            ctx.fillText(characters[Math.floor(Math.random()*characters.length)],x,y);
        }
    }
    function drawDigitalTrails(time){
        const lineCount=width<768?4:8;
        for(let i=0;i<lineCount;i++){
            const y=height*(0.18+(i/lineCount)*0.65);
            const startX=width*(0.55+Math.sin(time*0.0002+i)*0.03);
            const length=width*(0.1+Math.sin(time*0.0005+i)*0.025);
            ctx.beginPath();
            ctx.moveTo(startX,y);
            ctx.lineTo(startX+length,y);
            ctx.strokeStyle="rgba(37,99,235,0.07)";
            ctx.lineWidth=1;
            ctx.stroke();
        }
    }
    function animate(time){
        ctx.clearRect(0,0,width,height);
        drawGlow();
        drawDigitalTrails(time);
        drawAmbientCharacters(time);
        drawButterfly(time);
        requestAnimationFrame(animate);
    }
    window.addEventListener("mousemove",event=>{
        mouse.x=event.clientX;
        mouse.y=event.clientY;
        mouse.active=true;
    },{passive:true});
    window.addEventListener("mouseleave",()=>mouse.active=false);
    window.addEventListener("resize",resizeCanvas);
    if(typeof ResizeObserver!=="undefined"){
        const observer=new ResizeObserver(()=>resizeCanvas());
        observer.observe(hero);
    }
    resizeCanvas();
    requestAnimationFrame(animate);
}