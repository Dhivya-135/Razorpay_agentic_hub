const state={chatHistory:[],isProcessing:false};
const API_BASE="/api";

document.addEventListener("DOMContentLoaded",()=>{
    initAgentDrawer();
    initChatListeners();
    initAsciiBackground();
    loadRazorpaySDK();
    if(typeof lucide!=="undefined"&&lucide.createIcons)lucide.createIcons();
});

function loadRazorpaySDK(){
    if(typeof window.Razorpay!=="undefined"){
        console.log("Razorpay SDK already loaded.");
        return Promise.resolve(true);
    }

    return new Promise(resolve=>{
        const existing=document.querySelector('script[src="https://checkout.razorpay.com/v1/checkout.js"]');

        if(existing){
            existing.addEventListener("load",()=>{
                console.log("Razorpay SDK loaded.");
                resolve(typeof window.Razorpay!=="undefined");
            });

            existing.addEventListener("error",()=>{
                console.error("Razorpay SDK failed to load.");
                resolve(false);
            });

            setTimeout(()=>{
                resolve(typeof window.Razorpay!=="undefined");
            },5000);

            return;
        }

        const script=document.createElement("script");
        script.src="https://checkout.razorpay.com/v1/checkout.js";
        script.async=true;

        script.onload=()=>{
            console.log("Razorpay SDK loaded dynamically.");
            resolve(typeof window.Razorpay!=="undefined");
        };

        script.onerror=()=>{
            console.error("Unable to load Razorpay Checkout SDK.");
            resolve(false);
        };

        document.head.appendChild(script);
    });
}

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

        setTimeout(()=>{
            document.getElementById("chat-input")?.focus();
        },350);
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

        if(!message||state.isProcessing)return;

        input.value="";

        await handleSendMessage(message);
    });
}

function displayValue(value){
    if(value===null||value===undefined)return"";

    if(typeof value==="string")return value;

    if(typeof value==="number"||typeof value==="boolean"){
        return String(value);
    }

    if(typeof value==="object"){
        if(typeof value.message==="string"){
            return value.message;
        }

        if(value.food_name){
            return `Checkout created for ${value.food_name}${value.amount!=null?` — ₹${value.amount}`:""}`;
        }

        if(value.error){
            return String(value.error);
        }

        try{
            return JSON.stringify(value,null,2);
        }catch{
            return"Action completed successfully.";
        }
    }

    return String(value);
}

function findAction(data){
    if(data?.action_data&&typeof data.action_data==="object"){
        return data.action_data;
    }

    if(data?.message&&typeof data.message==="object"){
        return data.message;
    }

    if(data?.response&&typeof data.response==="object"){
        return data.response;
    }

    if(data?.answer&&typeof data.answer==="object"){
        return data.answer;
    }

    return null;
}

async function handleSendMessage(messageText){
    state.isProcessing=true;
    toggleInputState(true);

    appendChatMessage("user",messageText);

    state.chatHistory.push({
        role:"user",
        content:messageText
    });

    const typingId=appendTypingIndicator();

    try{
        const response=await fetch(`${API_BASE}/chat`,{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                message:messageText,
                history:state.chatHistory
            })
        });

        removeTypingIndicator(typingId);

        if(!response.ok){
            throw new Error(`Server returned status code ${response.status}`);
        }

        const data=await response.json();

        console.log("FULL AGENT RESPONSE:",data);

        const action=data?.action_data||findAction(data);

        console.log("ACTION DATA:",action);

        const rawMessage=
            data?.text??
            data?.response??
            data?.message??
            data?.answer??
            "Action executed successfully.";

        const assistantText=displayValue(rawMessage);

        appendChatMessage("assistant",assistantText);

        state.chatHistory.push({
            role:"assistant",
            content:assistantText
        });

        if(action){
            await handleActionData(action);
        }

    }catch(error){
        removeTypingIndicator(typingId);

        console.error("Chat error:",error);

        appendChatMessage(
            "assistant",
            `⚠️ Error processing request: ${error.message}. Please check your backend logs.`
        );

    }finally{
        state.isProcessing=false;
        toggleInputState(false);
    }
}

function appendChatMessage(role,content){
    const chatWindow=document.getElementById("chat-window");

    if(!chatWindow)return;

    const wrapper=document.createElement("div");

    wrapper.className=
        `flex flex-col space-y-1 max-w-[85%] message-animate ${
            role==="user"
                ?"ml-auto items-end"
                :"items-start"
        }`;

    const bubble=document.createElement("div");

    bubble.className=
        role==="user"
            ?"user-message"
            :"assistant-message";

    const body=document.createElement("p");

    body.className="leading-relaxed whitespace-pre-wrap";

    body.innerText=displayValue(content);

    const tag=document.createElement("span");

    tag.className=
        "text-[10px] text-slate-500 font-mono uppercase px-1";

    tag.innerText=
        role==="user"
            ?"YOU"
            :"SYSTEM AGENT • ACTIVE";

    bubble.appendChild(body);

    wrapper.appendChild(bubble);
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

    wrapper.className=
        "flex flex-col space-y-1 max-w-[85%] message-animate items-start";

    wrapper.innerHTML=
        `<div class="bg-drawer-panel text-slate-400 p-3 rounded-2xl rounded-tl-none border border-drawer-border shadow-sm text-xs flex items-center space-x-2"><span class="font-mono">Agent thinking</span><span class="animate-bounce">.</span><span class="animate-bounce">.</span><span class="animate-bounce">.</span></div>`;

    chatWindow.appendChild(wrapper);

    chatWindow.scrollTop=chatWindow.scrollHeight;

    return id;
}

function removeTypingIndicator(id){
    if(id){
        document.getElementById(id)?.remove();
    }
}

function toggleInputState(disabled){
    const input=document.getElementById("chat-input");
    const button=document.getElementById("send-btn");

    if(input)input.disabled=disabled;
    if(button)button.disabled=disabled;
}

async function handleActionData(actionData){
    console.log("HANDLING ACTION DATA:",actionData);

    if(!actionData)return;

    if(Array.isArray(actionData)){
        renderProductGrid(actionData);
        return;
    }

    if(actionData?.products&&Array.isArray(actionData.products)){
        renderProductGrid(actionData.products);
        return;
    }

    if(actionData?.razorpay_order_id){
        console.log(
            "RAZORPAY ACTION DETECTED:",
            actionData
        );

        await openRazorpayCheckout(actionData);

        return;
    }

    console.log(
        "No supported action found:",
        actionData
    );
}

function renderProductGrid(products){
    const grid=document.getElementById("product-grid");

    if(!grid)return;

    grid.innerHTML="";

    if(!Array.isArray(products)||!products.length){
        grid.innerHTML=
            `<div class="flex flex-col items-center justify-center h-full opacity-40 py-8 text-center"><p class="text-xs font-medium text-slate-400">No products found for this query.</p></div>`;

        return;
    }

    products.forEach((prod,index)=>{
        const card=document.createElement("div");

        card.className=
            "product-card rounded-xl overflow-hidden shadow-lg flex flex-col justify-between p-3 space-y-3";

        const img=
            prod.image_url||
            prod.image||
            "https://placehold.co/400x250/1e293b/64748b?text=Product";

        const name=escapeHtml(
            prod.name||
            prod.title||
            "Product"
        );

        const merchant=escapeHtml(
            prod.merchant||
            "Store"
        );

        const category=escapeHtml(
            prod.category||
            "General"
        );

        const price=escapeHtml(
            String(prod.price??"")
        );

        card.innerHTML=
            `<div class="flex space-x-3"><div class="relative h-16 w-16 flex-shrink-0 rounded-lg overflow-hidden bg-slate-950"><img src="${img}" alt="${name}" class="w-full h-full object-cover" loading="lazy"></div><div class="flex-1 min-w-0"><div class="flex items-center justify-between gap-2"><span class="px-2 py-0.5 text-[9px] font-black uppercase rounded text-white ${getMerchantBadgeColor(prod.merchant||"")}">${merchant}</span><span class="text-xs font-bold text-emerald-400">₹${price}</span></div><h4 class="font-bold text-slate-100 text-xs truncate mt-1" title="${name}">${name}</h4><p class="text-[10px] text-slate-500 capitalize">${category}</p></div></div><button class="buy-product-btn w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition-colors shadow flex items-center justify-center space-x-1"><span>Buy Now</span></button>`;

        card
            .querySelector(".buy-product-btn")
            ?.addEventListener(
                "click",
                ()=>directCheckout(prod,index+1)
            );

        grid.appendChild(card);
    });
}

function escapeHtml(value){
    return String(value)
        .replace(/&/g,"&amp;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;")
        .replace(/"/g,"&quot;")
        .replace(/'/g,"&#039;");
}

function getMerchantBadgeColor(merchant=""){
    const m=merchant.toLowerCase();

    if(m.includes("zomato"))return"bg-red-600";
    if(m.includes("swiggy"))return"bg-orange-600";
    if(m.includes("pvr"))return"bg-yellow-600";

    return"bg-slate-700";
}

async function directCheckout(product,optionNumber){
    if(state.isProcessing)return;

    const itemId=Number(product?.id);

    if(!Number.isInteger(itemId)){
        appendChatMessage(
            "assistant",
            "❌ This movie does not have a valid database item ID."
        );

        return;
    }

    state.isProcessing=true;

    toggleInputState(true);

    try{
        console.log("Creating direct movie checkout:",{
            item_id:itemId,
            merchant:product?.merchant||"PVR INOX"
        });

        const response=await fetch(`${API_BASE}/checkout`,{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                item_id:itemId,
                merchant:product?.merchant||"PVR INOX"
            })
        });

        const result=await response.json();

        console.log(
            "Direct movie checkout response:",
            result
        );

        if(!response.ok||result?.status==="error"){
            appendChatMessage(
                "assistant",
                `❌ ${result?.message||"Unable to create Razorpay checkout."}`
            );

            return;
        }

        appendChatMessage(
            "assistant",
            `Opening Razorpay Checkout for option ${optionNumber}...`
        );

        await openRazorpayCheckout(result);

    }catch(error){
        console.error(
            "Direct checkout error:",
            error
        );

        appendChatMessage(
            "assistant",
            `❌ Unable to create checkout: ${error.message}`
        );

    }finally{
        state.isProcessing=false;
        toggleInputState(false);
    }
}

async function openRazorpayCheckout(actionData){
    console.log(
        "Preparing Razorpay Checkout:",
        actionData
    );

    const loaded=await loadRazorpaySDK();

    console.log(
        "Razorpay SDK status:",
        {
            loaded:loaded,
            Razorpay:typeof window.Razorpay
        }
    );

    if(!loaded||typeof window.Razorpay!=="function"){
        appendChatMessage(
            "assistant",
            "❌ Razorpay Checkout SDK could not be loaded."
        );

        console.error(
            "Razorpay SDK unavailable."
        );

        return;
    }

    const key=String(
        actionData?.razorpay_key_id||
        actionData?.key_id||
        ""
    );

    const orderId=String(
        actionData?.razorpay_order_id||
        actionData?.order_id||
        ""
    );

    let amount=Number(
        actionData?.total_paise??
        actionData?.amount_paise??
        actionData?.amount??
        0
    );

    if(
        actionData?.amount!=null&&
        actionData?.amount_paise==null&&
        actionData?.total_paise==null&&
        amount>0&&
        amount<1000
    ){
        amount=Math.round(amount*100);
    }

    const currency=String(
        actionData?.currency||
        "INR"
    );

    const merchant=String(
        actionData?.merchant||
        "Razorpay"
    );

    const foodName=String(
        actionData?.food_name||
        "Food Order"
    );

    let description=
        `Food Order - ${foodName}`;

    if(
        !actionData?.food_name&&
        Array.isArray(actionData?.item_summaries)
    ){
        description=
            actionData.item_summaries.join(", ");
    }

    console.log(
        "FINAL RAZORPAY VALUES:",
        {
            key:key,
            orderId:orderId,
            amount:amount,
            currency:currency,
            merchant:merchant,
            description:description
        }
    );

    if(
        !key||
        !key.startsWith("rzp_")
    ){
        appendChatMessage(
            "assistant",
            "❌ Invalid Razorpay Key ID."
        );

        console.error(
            "Invalid Razorpay key:",
            key
        );

        return;
    }

    if(!orderId){
        appendChatMessage(
            "assistant",
            "❌ Razorpay Order ID is missing."
        );

        console.error(
            "Missing order ID:",
            actionData
        );

        return;
    }

    if(
        !Number.isFinite(amount)||
        amount<=0
    ){
        appendChatMessage(
            "assistant",
            "❌ Invalid Razorpay amount."
        );

        console.error(
            "Invalid amount:",
            amount
        );

        return;
    }

    const options={
        key:key,
        amount:Math.round(amount),
        currency:currency,
        name:merchant,
        description:description,
        order_id:orderId,
        theme:{
            color:"#2563EB"
        },
        handler:function(response){
            console.log(
                "Razorpay payment success:",
                response
            );

            verifyPayment(response);
        },
        modal:{
            ondismiss:function(){
                console.log(
                    "Razorpay Checkout dismissed."
                );
            },
            escape:true,
            backdropclose:false
        }
    };

    console.log(
        "RAZORPAY OPTIONS READY:",
        options
    );

    try{
        const razorpay=
            new window.Razorpay(options);

        razorpay.on(
            "payment.failed",
            function(response){
                console.error(
                    "Razorpay payment failed:",
                    response
                );

                appendChatMessage(
                    "assistant",
                    `❌ Payment failed: ${response?.error?.description||"Please try again."}`
                );
            }
        );

        razorpay.on(
            "payment.authorized",
            function(response){
                console.log(
                    "Razorpay payment authorized:",
                    response
                );
            }
        );

        razorpay.open();

        console.log(
            "RAZORPAY OPEN CALLED SUCCESSFULLY"
        );

        setTimeout(()=>{
            const iframe=
                document.querySelector(
                    'iframe[src*="razorpay"]'
                );

            const modal=
                document.querySelector(
                    '[class*="razorpay"]'
                );

            if(
                !iframe&&
                !modal
            ){
                console.warn(
                    "Razorpay modal was not detected. Showing manual payment button."
                );

                showRazorpayFallback(
                    actionData
                );
            }
        },1500);

    }catch(error){
        console.error(
            "RAZORPAY OPEN ERROR:",
            error
        );

        showRazorpayFallback(
            actionData,
            error.message
        );
    }
}

function showRazorpayFallback(
    actionData,
    errorMessage=""
){
    console.error(
        "Razorpay fallback:",
        errorMessage
    );

    const existing=
        document.getElementById(
            "razorpay-fallback-container"
        );

    existing?.remove();

    const amount=Number(
        actionData?.amount_paise||
        actionData?.total_paise||
        0
    );

    const foodName=
        actionData?.food_name||
        "Food Order";

    const container=
        document.createElement("div");

    container.id=
        "razorpay-fallback-container";

    container.className=
        "mt-3 p-3 rounded-xl border border-blue-500/30 bg-blue-500/10";

    container.innerHTML=`
        <p class="text-xs text-slate-300 mb-2">
            Razorpay Checkout is ready for ${escapeHtml(foodName)}.
        </p>
        <button
            id="open-razorpay-manual"
            class="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition">
            Pay ₹${(amount/100).toFixed(2)} with Razorpay
        </button>
    `;

    const chatWindow=
        document.getElementById(
            "chat-window"
        );

    if(chatWindow){
        chatWindow.appendChild(
            container
        );

        chatWindow.scrollTop=
            chatWindow.scrollHeight;
    }

    document
        .getElementById(
            "open-razorpay-manual"
        )
        ?.addEventListener(
            "click",
            function(){
                openRazorpayFromUserClick(
                    actionData
                );
            }
        );
}

function openRazorpayFromUserClick(
    actionData
){
    console.log(
        "Opening Razorpay from direct user click:",
        actionData
    );

    const key=String(
        actionData?.razorpay_key_id||
        actionData?.key_id||
        ""
    );

    const orderId=String(
        actionData?.razorpay_order_id||
        actionData?.order_id||
        ""
    );

    const amount=Number(
        actionData?.amount_paise||
        actionData?.total_paise||
        0
    );

    const currency=String(
        actionData?.currency||
        "INR"
    );

    const merchant=String(
        actionData?.merchant||
        "Razorpay"
    );

    const foodName=String(
        actionData?.food_name||
        "Food Order"
    );

    if(
        !key||
        !key.startsWith("rzp_")
    ){
        appendChatMessage(
            "assistant",
            "❌ Invalid Razorpay Key ID."
        );

        return;
    }

    if(!orderId){
        appendChatMessage(
            "assistant",
            "❌ Razorpay Order ID is missing."
        );

        return;
    }

    if(
        !Number.isFinite(amount)||
        amount<=0
    ){
        appendChatMessage(
            "assistant",
            "❌ Invalid Razorpay amount."
        );

        return;
    }

    try{
        const razorpay=
            new window.Razorpay({
                key:key,
                amount:Math.round(amount),
                currency:currency,
                name:merchant,
                description:`Food Order - ${foodName}`,
                order_id:orderId,
                theme:{
                    color:"#2563EB"
                },
                handler:function(response){
                    console.log(
                        "Razorpay payment success:",
                        response
                    );

                    verifyPayment(response);
                },
                modal:{
                    ondismiss:function(){
                        console.log(
                            "Razorpay Checkout dismissed."
                        );
                    },
                    escape:true,
                    backdropclose:false
                }
            });

        razorpay.on(
            "payment.failed",
            function(response){
                console.error(
                    "Razorpay payment failed:",
                    response
                );

                appendChatMessage(
                    "assistant",
                    `❌ Payment failed: ${response?.error?.description||"Please try again."}`
                );
            }
        );

        razorpay.open();

        document
            .getElementById(
                "razorpay-fallback-container"
            )
            ?.remove();

    }catch(error){
        console.error(
            "Manual Razorpay open error:",
            error
        );

        appendChatMessage(
            "assistant",
            `❌ Unable to open Razorpay Checkout: ${error.message}`
        );
    }
}

async function verifyPayment(rzpResponse){
    if(
        !rzpResponse?.razorpay_order_id||
        !rzpResponse?.razorpay_payment_id||
        !rzpResponse?.razorpay_signature
    ){
        appendChatMessage(
            "assistant",
            "❌ Payment response is incomplete. Razorpay did not return all verification fields."
        );

        return;
    }

    try{
        const res=await fetch(
            `${API_BASE}/verify-payment`,
            {
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    razorpay_order_id:
                        rzpResponse.razorpay_order_id,
                    razorpay_payment_id:
                        rzpResponse.razorpay_payment_id,
                    razorpay_signature:
                        rzpResponse.razorpay_signature
                })
            }
        );

        if(!res.ok){
            throw new Error(
                `Verification server returned ${res.status}`
            );
        }

        const result=await res.json();

        console.log(
            "Payment verification:",
            result
        );

        if(
            result.success===true||
            result.status==="PAID"||
            result.verified===true
        ){
            appendChatMessage(
                "assistant",
                `🎉 Payment Verified!\n\nOrder ID: ${rzpResponse.razorpay_order_id}\nPayment ID: ${rzpResponse.razorpay_payment_id}`
            );
        }else{
            appendChatMessage(
                "assistant",
                `❌ ${displayValue(result.message)||"Payment verification failed. Please try again."}`
            );
        }

    }catch(error){
        console.error(
            "Payment verification error:",
            error
        );

        appendChatMessage(
            "assistant",
            `❌ Verification network error: ${error.message}`
        );
    }
}

function initAsciiBackground(){
    let canvas=document.getElementById("ascii-background");
    const hero=document.getElementById("hero-section");

    if(!hero){
        console.warn(
            "Hero section not found. ASCII animation disabled."
        );
        return;
    }

    if(!canvas){
        canvas=document.createElement("canvas");
        canvas.id="ascii-background";
        hero.prepend(canvas);
    }

    canvas.style.position="absolute";
    canvas.style.inset="0";
    canvas.style.width="100%";
    canvas.style.height="100%";
    canvas.style.pointerEvents="none";
    canvas.style.zIndex="0";

    hero.style.position="relative";
    hero.style.overflow="hidden";

    const ctx=canvas.getContext("2d");

    if(!ctx){
        console.warn(
            "Canvas context unavailable."
        );
        return;
    }

    let width=0;
    let height=0;
    let dpr=1;

    const particles=[];

    let particleCount=900;

    let animationStarted=false;

    const mouse={
        x:-1000,
        y:-1000,
        active:false
    };

    const characters=[
        "0",
        "1",
        "0",
        "1",
        "·",
        "•",
        ".",
        ":",
        "+",
        "*",
        "#",
        "@",
        "░",
        "▒"
    ];

    function resizeCanvas(){
        const rect=hero.getBoundingClientRect();

        width=Math.max(
            1,
            Math.floor(rect.width)
        );

        height=Math.max(
            1,
            Math.floor(rect.height)
        );

        dpr=Math.min(
            window.devicePixelRatio||1,
            2
        );

        canvas.width=width*dpr;
        canvas.height=height*dpr;

        canvas.style.width=`${width}px`;
        canvas.style.height=`${height}px`;

        ctx.setTransform(
            dpr,
            0,
            0,
            dpr,
            0,
            0
        );

        if(width<640){
            particleCount=400;
        }else if(width<1024){
            particleCount=650;
        }else{
            particleCount=1000;
        }

        createParticles();
    }

    function butterflyShape(t){
        const value=
            Math.exp(Math.cos(t))-
            2*Math.cos(4*t)-
            Math.pow(
                Math.sin(t/12),
                5
            );

        const x=
            Math.sin(t)*
            value;

        const y=
            Math.cos(t)*
            value;

        return{
            x,
            y
        };
    }

    function createParticles(){
        particles.length=0;

        const centerX=width*0.78;
        const centerY=height*0.48;

        const scale=
            Math.min(
                width,
                height
            )*0.055;

        for(
            let i=0;
            i<particleCount;
            i++
        ){
            const t=
                Math.random()*
                Math.PI*
                24;

            const shape=
                butterflyShape(t);

            const isCore=
                Math.random()<0.70;

            const spread=
                isCore
                    ?Math.random()*0.50
                    :Math.random()*3.2;

            let x=
                centerX+
                shape.x*
                scale+
                (
                    Math.random()-0.5
                )*
                spread*
                scale;

            let y=
                centerY+
                shape.y*
                scale+
                (
                    Math.random()-0.5
                )*
                spread*
                scale;

            x=Math.max(
                -20,
                Math.min(
                    width+20,
                    x
                )
            );

            y=Math.max(
                -20,
                Math.min(
                    height+20,
                    y
                )
            );

            particles.push({
                x,
                y,
                baseX:x,
                baseY:y,
                size:
                    Math.random()*2.4+
                    0.6,
                speed:
                    Math.random()*0.7+
                    0.25,
                phase:
                    Math.random()*
                    Math.PI*
                    2,
                drift:
                    Math.random()*0.8+
                    0.2,
                char:
                    characters[
                        Math.floor(
                            Math.random()*
                            characters.length
                        )
                    ],
                brightness:
                    Math.random(),
                opacity:
                    Math.random()
            });
        }
    }

    function drawAmbientCharacters(time){
        ctx.textAlign="center";
        ctx.textBaseline="middle";
        ctx.font="10px monospace";

        const amount=
            width<768
                ?60
                :130;

        for(
            let i=0;
            i<amount;
            i++
        ){
            const x=
                width*
                (
                    0.55+
                    Math.random()*
                    0.45
                );

            const y=
                Math.random()*
                height;

            const flicker=
                Math.sin(
                    time*0.0015+
                    i*1.7
                )*
                0.5+
                0.5;

            ctx.fillStyle=
                `rgba(59,130,246,${0.025+flicker*0.08})`;

            ctx.fillText(
                characters[
                    Math.floor(
                        Math.random()*
                        characters.length
                    )
                ],
                x,
                y
            );
        }
    }

    function drawParticles(time){
        ctx.textAlign="center";
        ctx.textBaseline="middle";

        for(const p of particles){
            const floatX=
                Math.sin(
                    time*
                    0.0008*
                    p.speed+
                    p.phase
                )*
                4;

            const floatY=
                Math.cos(
                    time*
                    0.0007*
                    p.speed+
                    p.phase
                )*
                4;

            let x=
                p.baseX+
                floatX;

            let y=
                p.baseY+
                floatY;

            if(mouse.active){
                const heroRect=
                    hero.getBoundingClientRect();

                const mouseX=
                    mouse.x-
                    heroRect.left;

                const mouseY=
                    mouse.y-
                    heroRect.top;

                const dx=
                    x-
                    mouseX;

                const dy=
                    y-
                    mouseY;

                const distance=
                    Math.sqrt(
                        dx*dx+
                        dy*dy
                    );

                const interactionRadius=110;

                if(
                    distance<
                    interactionRadius
                ){
                    const force=
                        (
                            interactionRadius-
                            distance
                        )/
                        interactionRadius;

                    x+=
                        (
                            dx/
                            (distance||1)
                        )*
                        force*
                        24;

                    y+=
                        (
                            dy/
                            (distance||1)
                        )*
                        force*
                        24;
                }
            }

            const flicker=
                Math.sin(
                    time*0.003+
                    p.phase
                )*
                0.5+
                0.5;

            let alpha=
                0.05+
                flicker*
                0.32;

            if(p.brightness>0.84){
                alpha=
                    0.20+
                    flicker*
                    0.55;

                ctx.font=
                    `${Math.max(
                        9,
                        p.size*5
                    )}px monospace`;

                ctx.fillStyle=
                    `rgba(37,99,235,${alpha})`;

            }else{
                ctx.font=
                    `${Math.max(
                        7,
                        p.size*4
                    )}px monospace`;

                ctx.fillStyle=
                    `rgba(96,165,250,${alpha})`;
            }

            ctx.fillText(
                p.char,
                x,
                y
            );
        }
    }

    function drawGlow(){
        const centerX=
            width*0.78;

        const centerY=
            height*0.48;

        const radius=
            Math.min(
                width,
                height
            )*0.42;

        const gradient=
            ctx.createRadialGradient(
                centerX,
                centerY,
                0,
                centerX,
                centerY,
                radius
            );

        gradient.addColorStop(
            0,
            "rgba(59,130,246,0.055)"
        );

        gradient.addColorStop(
            0.30,
            "rgba(96,165,250,0.025)"
        );

        gradient.addColorStop(
            0.65,
            "rgba(147,197,253,0.012)"
        );

        gradient.addColorStop(
            1,
            "rgba(255,255,255,0)"
        );

        ctx.fillStyle=gradient;

        ctx.fillRect(
            0,
            0,
            width,
            height
        );
    }

    function drawDigitalTrails(time){
        const lineCount=
            width<768
                ?5
                :9;

        for(
            let i=0;
            i<lineCount;
            i++
        ){
            const y=
                height*
                (
                    0.15+
                    (
                        i/
                        lineCount
                    )*
                    0.70
                );

            const startX=
                width*
                (
                    0.55+
                    Math.sin(
                        time*0.0002+
                        i
                    )*
                    0.04
                );

            const length=
                width*
                (
                    0.12+
                    Math.sin(
                        time*0.0005+
                        i*2
                    )*
                    0.03
                );

            ctx.beginPath();

            ctx.moveTo(
                startX,
                y
            );

            ctx.lineTo(
                startX+
                length,
                y
            );

            ctx.strokeStyle=
                "rgba(59,130,246,0.025)";

            ctx.lineWidth=1;

            ctx.stroke();
        }
    }

    function animate(time){
        ctx.clearRect(
            0,
            0,
            width,
            height
        );

        drawGlow();
        drawDigitalTrails(time);
        drawAmbientCharacters(time);
        drawParticles(time);

        requestAnimationFrame(
            animate
        );
    }

    window.addEventListener(
        "mousemove",
        event=>{
            mouse.x=event.clientX;
            mouse.y=event.clientY;
            mouse.active=true;
        },
        {
            passive:true
        }
    );

    window.addEventListener(
        "mouseleave",
        ()=>{
            mouse.active=false;
        }
    );

    window.addEventListener(
        "resize",
        resizeCanvas
    );

    if(typeof ResizeObserver!=="undefined"){
        const observer=
            new ResizeObserver(
                ()=>{
                    resizeCanvas();
                }
            );

        observer.observe(hero);
    }

    resizeCanvas();

    if(!animationStarted){
        animationStarted=true;

        requestAnimationFrame(
            animate
        );
    }
}
