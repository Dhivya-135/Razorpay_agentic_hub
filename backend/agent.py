import os
import json
import asyncio
import re
from dotenv import load_dotenv
from sarvamai import SarvamAI
from backend import tools

load_dotenv()

SARVAM_API_KEY=os.getenv("SARVAM_API_KEY")

if not SARVAM_API_KEY:
    raise RuntimeError("SARVAM_API_KEY is missing. Set it in your .env file.")

client=SarvamAI(api_subscription_key=SARVAM_API_KEY)
MODEL_ID="sarvam-105b"

conversation_state={
    "pending_options":[],
    "selected_item":None,
    "active_type":None,
    "active_merchant":None
}

SYSTEM_INSTRUCTION="""
You are Razorpay Agentic Payment Hub, an intelligent shopping and booking assistant.

IMPORTANT RULES:

FOOD:
- Food recommendations must use AI knowledge only.
- Never search the movie/product database for food recommendations.
- Never invent live restaurant availability.
- Never claim live food prices unless explicitly provided by the user.
- When the user asks for food recommendations, provide exactly 3 food options.
- Do not create a checkout merely because food was recommended.
- Food checkout happens only after the user explicitly asks to order, buy, purchase, get, or deliver food.
- Food checkout uses the real Razorpay checkout flow.

MOVIES:
- Movie information must come only from the PVR INOX database.
- Never invent movie names, prices, showtimes, item IDs, or movie details.
- When the user selects a movie option, use the exact database item ID.
- Movie checkout must use the exact PVR INOX database item.
- Preserve the database movie image_url when displaying movie results.
- Movie booking uses the real Razorpay checkout flow.

GENERAL:
- Never invent database item IDs.
- Never create a movie checkout without a valid database item.
- Never create a food checkout unless the user explicitly orders food.
- Keep responses concise and useful.
"""

TOOL_DEFINITIONS=[
    {
        "type":"function",
        "function":{
            "name":"search_movie_database",
            "description":"Search movies available in the PVR INOX database. Use only for movie or cinema requests.",
            "parameters":{
                "type":"object",
                "properties":{
                    "query":{
                        "type":"string",
                        "description":"Movie search query"
                    },
                    "location":{
                        "type":"string",
                        "description":"Optional location"
                    }
                },
                "required":["query"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"create_movie_checkout",
            "description":"Create a real Razorpay checkout for an exact PVR INOX database movie item.",
            "parameters":{
                "type":"object",
                "properties":{
                    "item_id":{
                        "type":"integer",
                        "description":"Exact movie database item ID"
                    }
                },
                "required":["item_id"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"create_food_checkout",
            "description":"Create a real Razorpay checkout for explicitly ordered food.",
            "parameters":{
                "type":"object",
                "properties":{
                    "food_name":{
                        "type":"string",
                        "description":"Food the user explicitly wants to order"
                    },
                    "location":{
                        "type":"string",
                        "description":"Optional delivery location"
                    }
                },
                "required":["food_name"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"verify_payment",
            "description":"Verify a completed Razorpay payment.",
            "parameters":{
                "type":"object",
                "properties":{
                    "razorpay_order_id":{
                        "type":"string"
                    },
                    "razorpay_payment_id":{
                        "type":"string"
                    },
                    "razorpay_signature":{
                        "type":"string"
                    }
                },
                "required":[
                    "razorpay_order_id",
                    "razorpay_payment_id",
                    "razorpay_signature"
                ]
            }
        }
    }
]

def get_response_message(response):
    try:
        if not response or not getattr(response,"choices",None):
            return None
        return response.choices[0].message
    except Exception:
        return None

def reset_state():
    conversation_state["pending_options"]=[]
    conversation_state["selected_item"]=None
    conversation_state["active_type"]=None
    conversation_state["active_merchant"]=None

def save_movie_options(products):
    options=[]

    for item in products or []:
        try:
            item_id=int(item.get("id"))
        except Exception:
            continue

        options.append({
            "number":len(options)+1,
            "item_id":item_id,
            "name":item.get("name") or item.get("title") or "Movie",
            "price":item.get("price"),
            "merchant":"PVR INOX",
            "type":"movie",
            "image_url":item.get("image_url") or item.get("image"),
            "showtime":item.get("showtime"),
            "location":item.get("location")
        })

    conversation_state["pending_options"]=options
    conversation_state["active_type"]="movie"
    conversation_state["active_merchant"]="PVR INOX"

def save_food_options(text):
    options=[]

    if not text:
        conversation_state["pending_options"]=[]
        conversation_state["active_type"]="food"
        conversation_state["active_merchant"]="Food"
        return

    for line in text.splitlines():
        clean=re.sub(r"[*_`#]","",line).strip()

        match=re.match(r"^\s*(\d+)[.)]\s*(.+)$",clean)

        if not match:
            continue

        number=int(match.group(1))
        name=match.group(2).strip()

        name=re.split(r"\s+[—–-]\s+",name,1)[0].strip()

        name=re.sub(r"\s+$","",name)

        if not name:
            continue

        options.append({
            "number":number,
            "name":name,
            "merchant":"Food",
            "type":"food"
        })

    options=sorted(options,key=lambda x:x["number"])

    unique_options=[]
    seen_names=set()

    for option in options:
        name=option["name"].strip().lower()

        if name in seen_names:
            continue

        seen_names.add(name)
        unique_options.append(option)

    unique_options=unique_options[:3]

    for index,option in enumerate(unique_options,1):
        option["number"]=index

    conversation_state["pending_options"]=unique_options
    conversation_state["active_type"]="food"
    conversation_state["active_merchant"]="Food"

    print("Saved food options:",conversation_state["pending_options"])

def recover_food_options_from_history(chat_history):
    if not chat_history:
        return False

    for msg in reversed(chat_history):
        if not isinstance(msg,dict):
            continue

        role=msg.get("role")
        content=msg.get("content","")

        if role not in {"assistant","model"}:
            continue

        if not isinstance(content,str) or not content.strip():
            continue

        clean_content=re.sub(r"[*_`#]","",content)

        has_one=re.search(r"(?m)^\s*1[.)]\s+",clean_content)
        has_two=re.search(r"(?m)^\s*2[.)]\s+",clean_content)
        has_three=re.search(r"(?m)^\s*3[.)]\s+",clean_content)

        if has_one and has_two and has_three:
            save_food_options(content)

            if len(conversation_state.get("pending_options",[]))>=3:
                print("Recovered food options from chat history.")
                return True

    return False

def format_movie_options():
    options=conversation_state["pending_options"]

    if not options:
        return "I couldn't find any movies available at PVR INOX."

    lines=["🎬 Movies available at PVR INOX:"]

    for option in options:
        name=option.get("name","Movie")
        price=option.get("price")
        showtime=option.get("showtime")

        details=[]

        if price is not None:
            details.append(f"₹{price}")

        if showtime:
            details.append(str(showtime))

        suffix=f" — {' • '.join(details)}" if details else ""

        lines.append(f"{option['number']}. {name}{suffix}")

    lines.append("")
    lines.append("Reply with the option number to book.")

    return "\n".join(lines)

def format_food_options():
    options=conversation_state["pending_options"]

    if not options:
        return "Sorry, I couldn't generate food suggestions right now."

    lines=["🍽️ Here are 3 food options:"]

    for option in options:
        lines.append(f"{option['number']}. {option['name']}")

    lines.append("")
    lines.append("Reply with the option number if you want to order.")

    return "\n".join(lines)

def extract_selection_number(text):
    if not text:
        return None

    value=text.strip().lower()

    patterns=[
        r"^\s*(\d+)\s*$",
        r"^\s*option\s*(\d+)\s*$",
        r"^\s*option\s*#?\s*(\d+)\s*$",
        r"^\s*(?:checkout|buy|order|purchase)\s+(?:product|option|item)?\s*#?\s*(\d+)\s*$",
        r"^\s*(?:checkout|buy|order|purchase)\s*#?\s*(\d+)\s*$"
    ]

    for pattern in patterns:
        match=re.match(pattern,value)

        if match:
            return int(match.group(1))

    return None

def extract_location(text):
    if not text:
        return None

    match=re.search(
        r"\b(?:in|at|near)\s+(.+)$",
        text,
        re.IGNORECASE
    )

    if match:
        location=match.group(1).strip()

        location=re.sub(
            r"\b(?:please|pls|please suggest|suggest|recommend)\b",
            "",
            location,
            flags=re.IGNORECASE
        ).strip()

        return location or None

    return None

def extract_food_name(text):
    if not text:
        return ""

    value=text.strip()

    value=re.sub(
        r"^\s*(?:please\s+)?(?:order|buy|purchase|get|send|deliver)\s+",
        "",
        value,
        flags=re.IGNORECASE
    )

    value=re.sub(
        r"^\s*(?:me|some|a|an)\s+",
        "",
        value,
        flags=re.IGNORECASE
    )

    location_match=re.search(
        r"\s+(?:in|at|near)\s+.+$",
        value,
        re.IGNORECASE
    )

    if location_match:
        value=value[:location_match.start()].strip()

    return value.strip()

def is_movie_request(text):
    if not text:
        return False

    value=text.lower()

    keywords=[
        "movie",
        "movies",
        "film",
        "films",
        "cinema",
        "cinemas",
        "ticket",
        "tickets",
        "showtime",
        "showtimes",
        "pvr",
        "inox"
    ]

    return any(keyword in value for keyword in keywords)

def is_food_request(text):
    if not text:
        return False

    value=text.lower()

    keywords=[
        "biryani",
        "pizza",
        "burger",
        "dosa",
        "idli",
        "parotta",
        "fried rice",
        "noodles",
        "chicken",
        "mutton",
        "fish",
        "pasta",
        "sandwich",
        "meal",
        "food",
        "restaurant",
        "eat"
    ]

    return any(keyword in value for keyword in keywords)

def is_food_order(text):
    if not text:
        return False

    value=text.lower()

    keywords=[
        "order",
        "buy",
        "purchase",
        "deliver",
        "delivery",
        "send me",
        "get me"
    ]

    return any(keyword in value for keyword in keywords)

def is_food_suggestion(text):
    if not text:
        return False

    value=text.lower()

    keywords=[
        "suggest",
        "suggestion",
        "recommend",
        "recommendation",
        "best",
        "what should i eat",
        "what can i eat",
        "which should i eat",
        "options"
    ]

    return any(keyword in value for keyword in keywords)

async def run_movie_search(user_input):
    reset_state()

    query=user_input.strip()
    location=extract_location(user_input)

    try:
        products=tools.search_merchant_products(
            query=query,
            merchant="PVR INOX",
            location=location
        )
    except TypeError:
        try:
            products=tools.search_merchant_products(
                query=query,
                merchant="PVR INOX"
            )
        except Exception as e:
            print("Movie database error:",repr(e))

            return {
                "text":"Sorry, I couldn't search PVR INOX right now.",
                "action_data":None,
                "type":"error"
            }
    except Exception as e:
        print("Movie database error:",repr(e))

        return {
            "text":"Sorry, I couldn't search PVR INOX right now.",
            "action_data":None,
            "type":"error"
        }

    if not products:
        return {
            "text":"I couldn't find that movie in the PVR INOX database.",
            "action_data":None
        }

    save_movie_options(products)

    return {
        "text":format_movie_options(),
        "action_data":{
            "products":products
        }
    }

async def run_food_ai(user_input,chat_history):
    location=extract_location(user_input)

    prompt=f"""
Give exactly 3 useful food recommendations for this request.

User request: {user_input}
Location: {location or "not specified"}

Rules:
- Use general AI knowledge only.
- Do not search any database.
- Do not claim live availability.
- Do not claim live restaurant prices.
- Do not create checkout.
- Give exactly 3 numbered food options.
- Keep each option on one line.
- Use this exact format:
1. Food name
2. Food name
3. Food name
""".strip()

    messages=[
        {
            "role":"system",
            "content":SYSTEM_INSTRUCTION
        }
    ]

    for msg in chat_history or []:
        if not isinstance(msg,dict):
            continue

        role=msg.get("role")
        content=msg.get("content","")

        if role in {"user","assistant"} and content:
            messages.append({
                "role":role,
                "content":content
            })

    messages.append({
        "role":"user",
        "content":prompt
    })

    try:
        response=await asyncio.to_thread(
            client.chat.completions,
            model=MODEL_ID,
            messages=messages,
            reasoning_effort=None,
            temperature=0.2,
            max_tokens=300
        )
    except Exception as e:
        print("Food AI error:",repr(e))

        return {
            "text":"Sorry, I couldn't generate food suggestions right now.",
            "action_data":None,
            "type":"error"
        }

    message=get_response_message(response)

    if message is None:
        print("Food AI returned no message.")
        print("Food AI response:",response)

        return {
            "text":"Sorry, I couldn't generate food suggestions right now.",
            "action_data":None,
            "type":"error"
        }

    content=getattr(message,"content",None)

    if not content:
        print("Food AI returned empty content.")
        print("Food AI response:",response)

        return {
            "text":"Sorry, I couldn't generate food suggestions right now.",
            "action_data":None,
            "type":"error"
        }

    content=content.strip()

    print("Food AI response:",content)

    save_food_options(content)

    if len(conversation_state["pending_options"])<3:
        print("Food AI did not return 3 parseable options.")

        return {
            "text":content,
            "action_data":None
        }

    return {
        "text":format_food_options(),
        "action_data":None
    }

async def run_food_order(user_input):
    reset_state()

    food_name=extract_food_name(user_input)
    location=extract_location(user_input)

    if not food_name:
        return {
            "text":"Please tell me what food you would like to order.",
            "action_data":None
        }

    print("Direct food order:",food_name)
    print("Food location:",location)

    try:
        result=await asyncio.to_thread(
            tools.create_food_razorpay_checkout,
            food_name=food_name,
            location=location
        )
    except Exception as e:
        print("Food checkout error:",repr(e))

        return {
            "text":"Sorry, I couldn't create the food checkout right now.",
            "action_data":None,
            "type":"error"
        }

    print("Food checkout result:",result)

    if not result:
        return {
            "text":"Sorry, I couldn't create the food checkout right now.",
            "action_data":None,
            "type":"error"
        }

    if result.get("success") is False:
        return {
            "text":result.get(
                "message",
                "Sorry, I couldn't create the food checkout right now."
            ),
            "action_data":None,
            "type":"error"
        }

    return {
        "text":f"Opening Razorpay Checkout for {food_name}...",
        "action_data":{
            "razorpay_order_id":result.get("razorpay_order_id"),
            "razorpay_key_id":result.get("razorpay_key_id"),
            "key_id":result.get("razorpay_key_id"),
            "amount":result.get("amount_paise"),
            "amount_paise":result.get("amount_paise"),
            "currency":result.get("currency","INR"),
            "merchant":result.get("merchant","Razorpay"),
            "food_name":result.get("food_name",food_name),
            "type":"food_checkout"
        }
    }

async def handle_number_selection(number):
    options=conversation_state.get("pending_options",[])

    print("================================")
    print("SELECTION RECEIVED:",number)
    print("ACTIVE TYPE:",conversation_state.get("active_type"))
    print("PENDING OPTIONS:",options)
    print("================================")

    if not options:
        return {
            "text":"Please ask me for food or movie recommendations first.",
            "action_data":None
        }

    if number<1 or number>len(options):
        return {
            "text":f"Please select an option between 1 and {len(options)}.",
            "action_data":None
        }

    selected=options[number-1]

    conversation_state["selected_item"]=selected

    print("SELECTED ITEM:",selected)

    if selected.get("type")=="movie":
        item_id=selected.get("item_id")

        if not item_id:
            return {
                "text":"This movie does not have a valid database item ID.",
                "action_data":None,
                "type":"error"
            }

        try:
            result=await tools.create_razorpay_checkout(
                item_ids=[item_id],
                merchant="PVR INOX"
            )
        except Exception as e:
            print("Movie checkout error:",repr(e))

            return {
                "text":"Sorry, I couldn't create the movie checkout right now.",
                "action_data":None,
                "type":"error"
            }

        if not result or result.get("status")=="error":
            return {
                "text":result.get(
                    "message",
                    "Sorry, I couldn't create the movie checkout right now."
                ) if result else "Sorry, I couldn't create the movie checkout right now.",
                "action_data":None,
                "type":"error"
            }

        return {
            "text":f"Opening Razorpay Checkout for {selected.get('name','movie')}...",
            "action_data":result
        }

    if selected.get("type")=="food":
        food_name=selected.get("name","").strip()

        if not food_name:
            return {
                "text":"I couldn't identify the selected food.",
                "action_data":None,
                "type":"error"
            }

        print("Creating food checkout for:",food_name)

        try:
            result=await asyncio.to_thread(
                tools.create_food_razorpay_checkout,
                food_name=food_name
            )
        except Exception as e:
            print("Food checkout error:",repr(e))

            return {
                "text":f"Sorry, I couldn't create the food checkout right now: {str(e)}",
                "action_data":None,
                "type":"error"
            }

        print("Food checkout result:",result)

        if not result:
            return {
                "text":"Sorry, I couldn't create the food checkout right now.",
                "action_data":None,
                "type":"error"
            }

        if result.get("success") is False:
            return {
                "text":result.get(
                    "message",
                    "Sorry, I couldn't create the food checkout right now."
                ),
                "action_data":None,
                "type":"error"
            }

        return {
            "text":f"Opening Razorpay Checkout for {food_name}...",
            "action_data":{
                "razorpay_order_id":result.get("razorpay_order_id"),
                "razorpay_key_id":result.get("razorpay_key_id"),
                "key_id":result.get("razorpay_key_id"),
                "amount":result.get("amount_paise"),
                "amount_paise":result.get("amount_paise"),
                "currency":result.get("currency","INR"),
                "merchant":result.get("merchant","Razorpay"),
                "food_name":result.get("food_name",food_name),
                "type":"food_checkout"
            }
        }

    return {
        "text":"I couldn't process that selection.",
        "action_data":None,
        "type":"error"
    }

async def run_generic_ai(user_input,chat_history):
    messages=[
        {
            "role":"system",
            "content":SYSTEM_INSTRUCTION
        }
    ]

    for msg in chat_history or []:
        if not isinstance(msg,dict):
            continue

        role=msg.get("role")
        content=msg.get("content","")

        if role in {"user","assistant"} and content:
            messages.append({
                "role":role,
                "content":content
            })

    messages.append({
        "role":"user",
        "content":user_input
    })

    try:
        response=await asyncio.to_thread(
            client.chat.completions,
            model=MODEL_ID,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.2,
            reasoning_effort=None,
            max_tokens=800
        )
    except Exception as e:
        print("Generic AI error:",repr(e))

        return {
            "text":"Sorry, I couldn't process your request right now.",
            "action_data":None,
            "type":"error"
        }

    message=get_response_message(response)

    if message is None:
        print("Generic AI returned no message.")
        print("Generic AI response:",response)

        return {
            "text":"Sorry, I couldn't process your request right now.",
            "action_data":None,
            "type":"error"
        }

    tool_calls=getattr(message,"tool_calls",None)

    if tool_calls:
        for tool_call in tool_calls:
            try:
                function_name=tool_call.function.name
                arguments=json.loads(
                    tool_call.function.arguments or "{}"
                )
            except Exception as e:
                print("Tool parsing error:",repr(e))
                continue

            if function_name=="search_movie_database":
                query=arguments.get("query","")
                location=arguments.get("location")

                return await run_movie_search(
                    f"{query} in {location}" if location else query
                )

            if function_name=="create_movie_checkout":
                item_id=arguments.get("item_id")

                if not item_id:
                    continue

                try:
                    result=await tools.create_razorpay_checkout(
                        item_ids=[int(item_id)],
                        merchant="PVR INOX"
                    )
                except Exception as e:
                    print("Movie tool checkout error:",repr(e))

                    return {
                        "text":"Sorry, I couldn't create the movie checkout.",
                        "action_data":None,
                        "type":"error"
                    }

                return {
                    "text":"Opening Razorpay Checkout...",
                    "action_data":result
                }

            if function_name=="create_food_checkout":
                food_name=arguments.get("food_name","")
                location=arguments.get("location")

                if not food_name:
                    continue

                try:
                    result=await asyncio.to_thread(
                        tools.create_food_razorpay_checkout,
                        food_name=food_name,
                        location=location
                    )
                except Exception as e:
                    print("Food tool checkout error:",repr(e))

                    return {
                        "text":"Sorry, I couldn't create the food checkout.",
                        "action_data":None,
                        "type":"error"
                    }

                if not result:
                    return {
                        "text":"Sorry, I couldn't create the food checkout.",
                        "action_data":None,
                        "type":"error"
                    }

                if result.get("success") is False:
                    return {
                        "text":result.get(
                            "message",
                            "Sorry, I couldn't create the food checkout."
                        ),
                        "action_data":None,
                        "type":"error"
                    }

                return {
                    "text":f"Opening Razorpay Checkout for {food_name}...",
                    "action_data":{
                        "razorpay_order_id":result.get("razorpay_order_id"),
                        "razorpay_key_id":result.get("razorpay_key_id"),
                        "key_id":result.get("razorpay_key_id"),
                        "amount":result.get("amount_paise"),
                        "amount_paise":result.get("amount_paise"),
                        "currency":result.get("currency","INR"),
                        "merchant":result.get("merchant","Razorpay"),
                        "food_name":result.get("food_name",food_name),
                        "type":"food_checkout"
                    }
                }

    content=getattr(message,"content",None)

    if not content:
        print("Generic AI returned empty content.")
        print("Generic AI response:",response)

        return {
            "text":"Sorry, I couldn't generate a response right now.",
            "action_data":None,
            "type":"error"
        }

    return {
        "text":content,
        "action_data":None
    }

async def run_agent(user_input,chat_history=None):
    if chat_history is None:
        chat_history=[]

    user_input=(user_input or "").strip()

    if not user_input:
        return {
            "text":"How can I help you today?",
            "action_data":None
        }

    selection_number=extract_selection_number(user_input)

    if selection_number is not None:
        pending_options=conversation_state.get("pending_options",[])

        if not pending_options:
            recovered=recover_food_options_from_history(chat_history)

            if recovered:
                pending_options=conversation_state.get("pending_options",[])

        if pending_options:
            return await handle_number_selection(selection_number)

        return {
            "text":"Please ask me for food or movie recommendations first.",
            "action_data":None
        }

    value=user_input.lower().strip()

    greetings=[
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "good morning",
        "good afternoon",
        "good evening"
    ]

    if value in greetings:
        return {
            "text":"Hello! 👋 I can help you discover movies at PVR INOX or get food recommendations and place real Razorpay orders.",
            "action_data":None
        }

    if is_movie_request(user_input):
        return await run_movie_search(user_input)

    if is_food_request(user_input) and is_food_order(user_input) and not is_food_suggestion(user_input):
        return await run_food_order(user_input)

    if is_food_request(user_input) and is_food_suggestion(user_input):
        return await run_food_ai(
            user_input,
            chat_history
        )

    if is_food_request(user_input) and not is_food_order(user_input):
        return await run_food_ai(
            user_input,
            chat_history
        )

    return await run_generic_ai(
        user_input,
        chat_history
    )
