import os
import json
import asyncio
import re
from dotenv import load_dotenv
from sarvamai import SarvamAI
from backend import tools
from backend.tools import search_merchant_products, create_razorpay_checkout, verify_and_fulfill_payment

load_dotenv()

conversation_state={
    "pending_options":[],
    "selected_item":None,
    "active_merchant":None,
    "active_type":None
}

SARVAM_API_KEY=os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    raise RuntimeError("SARVAM_API_KEY is missing from .env")

client=SarvamAI(api_subscription_key=SARVAM_API_KEY)
MODEL_ID="sarvam-105b"

SYSTEM_INSTRUCTION="""
Use “suggest” or “recommend” requests for discovery only; never trigger checkout or payment.
For food orders, use the food checkout tool directly without database availability checks; never claim food is unavailable.
Route movies/cinema to PVR INOX and use the database only for movie listings and ticket options.
When the user selects a numbered option, immediately checkout that exact option; use its real item ID for movies and the selected food name for food.
Always preserve the latest merchant and option list and never mix previous food, movie, or merchant results.
Use tools only when required; never invent IDs, prices, restaurants, movies, availability, or payment details.
""".strip()

tools_definition=[
    {
        "type":"function",
        "function":{
            "name":"get_food_recommendations",
            "description":"Give food recommendations for discovery only. Never create payment or checkout.",
            "parameters":{
                "type":"object",
                "properties":{
                    "query":{"type":"string"},
                    "location":{"type":"string"},
                    "cuisine":{"type":"string"},
                    "budget":{"type":"string"}
                },
                "required":["query"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"search_merchant_products",
            "description":"Search the database only for movies, cinema, movie tickets, showtimes and PVR INOX entertainment products.",
            "parameters":{
                "type":"object",
                "properties":{
                    "query":{"type":"string"},
                    "location":{"type":"string"},
                    "merchant":{"type":"string"}
                },
                "required":["query"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"create_razorpay_checkout",
            "description":"Create Razorpay checkout for a real movie database item returned by search_merchant_products.",
            "parameters":{
                "type":"object",
                "properties":{
                    "item_ids":{
                        "type":"array",
                        "items":{"type":"integer"}
                    },
                    "merchant":{"type":"string"}
                },
                "required":["item_ids"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"create_food_razorpay_checkout",
            "description":"Create Razorpay checkout for a food order. Do not search the database. Use only when the user explicitly wants to order, buy or get food, not when asking for suggestions.",
            "parameters":{
                "type":"object",
                "properties":{
                    "food_name":{"type":"string"},
                    "amount":{"type":"number"},
                    "location":{"type":"string"}
                },
                "required":["food_name"]
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"verify_and_fulfill_payment",
            "description":"Verify a completed Razorpay payment.",
            "parameters":{
                "type":"object",
                "properties":{
                    "payment_id":{"type":"string"},
                    "order_id":{"type":"string"}
                },
                "required":["payment_id","order_id"]
            }
        }
    }
]

def get_food_recommendations(query,location=None,cuisine=None,budget=None):
    q=query.lower()
    if "biryani" in q:
        recommendations=[
            {"name":"Ambur Biryani","description":"Aromatic biryani known for its flavorful rice and tender meat.","price":299},
            {"name":"Dindigul Biryani","description":"A peppery South Indian style biryani with distinctive short-grain rice.","price":329},
            {"name":"Thalappakatti Biryani","description":"A popular Tamil Nadu style biryani with rich spices and seeraga samba rice.","price":349}
        ]
    elif "pizza" in q:
        recommendations=[
            {"name":"Margherita Pizza","description":"Classic pizza with tomato, mozzarella and herbs.","price":249},
            {"name":"Farmhouse Pizza","description":"Vegetable-loaded pizza with a rich cheesy topping.","price":329},
            {"name":"Chicken Tikka Pizza","description":"Cheesy pizza topped with flavorful chicken tikka.","price":399}
        ]
    elif "burger" in q:
        recommendations=[
            {"name":"Classic Chicken Burger","description":"Crispy chicken with fresh vegetables and sauce.","price":199},
            {"name":"Veg Cheese Burger","description":"Vegetable patty with melted cheese and sauces.","price":179},
            {"name":"Spicy Chicken Burger","description":"Spicy chicken patty with a bold sauce.","price":229}
        ]
    else:
        recommendations=[
            {"name":query.title(),"description":"A recommended food option based on your request.","price":299},
            {"name":f"{query.title()} Special","description":"A popular variation worth trying.","price":329},
            {"name":f"{query.title()} Premium","description":"A richer option for a more indulgent meal.","price":349}
        ]
    return {
        "type":"food_recommendations",
        "query":query,
        "location":location,
        "cuisine":cuisine,
        "budget":budget,
        "recommendations":recommendations
    }

tools_map={
    "get_food_recommendations":get_food_recommendations,
    "search_merchant_products":search_merchant_products,
    "create_razorpay_checkout":create_razorpay_checkout,
    "create_food_razorpay_checkout":tools.create_food_razorpay_checkout,
    "verify_and_fulfill_payment":verify_and_fulfill_payment
}

def save_food_options(result):
    recommendations=[]
    if isinstance(result,dict):
        recommendations=result.get("recommendations",[])
    if not isinstance(recommendations,list):
        return
    options=[]
    for index,item in enumerate(recommendations,1):
        if isinstance(item,dict):
            name=item.get("name")
            if not name:
                continue
            options.append({
                "number":index,
                "name":name,
                "price":item.get("price"),
                "description":item.get("description",""),
                "merchant":"Food",
                "type":"food"
            })
        elif isinstance(item,str):
            options.append({
                "number":index,
                "name":item,
                "price":None,
                "description":"",
                "merchant":"Food",
                "type":"food"
            })
    conversation_state["pending_options"]=options
    conversation_state["active_merchant"]="Food"
    conversation_state["active_type"]="food"

def save_movie_options(result):
    options=[]
    products=[]
    if isinstance(result,dict):
        products=result.get("products",result.get("items",[]))
    if not isinstance(products,list):
        return
    for index,product in enumerate(products,1):
        if not isinstance(product,dict):
            continue
        item_id=product.get("id")
        if item_id is None:
            continue
        try:
            item_id=int(item_id)
        except:
            continue
        options.append({
            "number":index,
            "item_id":item_id,
            "id":item_id,
            "name":product.get("name",product.get("title","Movie Ticket")),
            "price":product.get("price"),
            "merchant":"PVR INOX",
            "type":"movie"
        })
    conversation_state["pending_options"]=options
    conversation_state["active_merchant"]="PVR INOX"
    conversation_state["active_type"]="movie"

async def handle_number_selection(user_input):
    if not user_input.isdigit():
        return None
    if not conversation_state["pending_options"]:
        return None
    number=int(user_input)
    if number<1 or number>len(conversation_state["pending_options"]):
        return {
            "message":"Please select one of the displayed options.",
            "type":"error"
        }
    selected_option=conversation_state["pending_options"][number-1]
    conversation_state["selected_item"]=selected_option
    conversation_state["pending_options"]=[]
    if selected_option["type"]=="movie":
        result=await create_razorpay_checkout(
            item_ids=[selected_option["item_id"]],
            merchant="PVR INOX"
        )
        return {
            "message":result,
            "type":"checkout",
            "action_data":result,
            "selected_item":selected_option
        }
    if selected_option["type"]=="food":
        try:
            amount=selected_option.get("price")
            if amount:
                result=await asyncio.to_thread(
                    tools.create_food_razorpay_checkout,
                    food_name=selected_option["name"],
                    amount=float(amount)
                )
            else:
                result=await asyncio.to_thread(
                    tools.create_food_razorpay_checkout,
                    food_name=selected_option["name"]
                )
            return {
                "message":result,
                "type":"checkout",
                "action_data":result,
                "selected_item":selected_option
            }
        except Exception as e:
            print("Food selection checkout error:",repr(e))
            return {
                "message":"Unable to create Razorpay checkout.",
                "type":"error"
            }
    return None

def get_response_message(response):
    if response is None:
        return None
    if not getattr(response,"choices",None):
        return None
    return response.choices[0].message

async def run_agent(user_prompt,chat_history=None):
    if chat_history is None:
        chat_history=[]
    user_input=user_prompt.strip()
    selection_result=await handle_number_selection(user_input)
    if selection_result is not None:
        return selection_result

    lower_input=user_input.lower()

    recommendation_words=[
        "suggest",
        "recommend",
        "recommendation",
        "recommendations",
        "best",
        "options",
        "what should i eat",
        "what can i eat",
        "which should i eat"
    ]

    order_words=[
        "order",
        "buy",
        "purchase",
        "get me",
        "send me",
        "deliver me"
    ]

    food_keywords=[
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
        "food"
    ]

    movie_keywords=[
        "movie",
        "film",
        "cinema",
        "ticket",
        "showtime",
        "pvr",
        "inox",
        "watch"
    ]

    is_movie=any(keyword in lower_input for keyword in movie_keywords)
    is_food=any(keyword in lower_input for keyword in food_keywords)
    is_recommendation=any(keyword in lower_input for keyword in recommendation_words)
    is_food_order=any(keyword in lower_input for keyword in order_words)

    if is_food and not is_movie and is_recommendation:
        conversation_state["pending_options"]=[]
        conversation_state["selected_item"]=None
        conversation_state["active_merchant"]="Food"
        conversation_state["active_type"]="food"

        messages=[
            {
                "role":"system",
                "content":SYSTEM_INSTRUCTION
            }
        ]

        for msg in chat_history:
            if isinstance(msg,dict):
                role=msg.get("role","user")
                if role in ["user","assistant","system"]:
                    messages.append({
                        "role":role,
                        "content":msg.get("content","")
                    })

        messages.append({
            "role":"user",
            "content":user_prompt
        })

        try:
            response=client.chat.completions(
                model=MODEL_ID,
                messages=messages,
                tools=tools_definition,
                tool_choice="required",
                temperature=0.2,
                max_tokens=2048,
                reasoning_effort=None
            )
        except Exception as e:
            print("Sarvam recommendation error:",repr(e))
            return {
                "message":"Sorry, I couldn't connect to the AI service.",
                "type":"error"
            }

        response_message=get_response_message(response)

        if response_message is None:
            return {
                "message":"The AI model returned an empty response.",
                "type":"error"
            }

        while getattr(response_message,"tool_calls",None):
            messages.append({
                "role":"assistant",
                "content":response_message.content or "",
                "tool_calls":[
                    {
                        "id":tc.id,
                        "type":tc.type,
                        "function":{
                            "name":tc.function.name,
                            "arguments":tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            })

            for tool_call in response_message.tool_calls:
                function_name=tool_call.function.name

                try:
                    function_args=json.loads(tool_call.function.arguments)
                except:
                    function_args={}

                if function_name!="get_food_recommendations":
                    return {
                        "message":"I can recommend food without starting a checkout.",
                        "type":"recommendations"
                    }

                try:
                    result=get_food_recommendations(**function_args)
                except Exception as e:
                    print("Recommendation tool error:",repr(e))
                    result={"error":str(e)}

                save_food_options(result)

                messages.append({
                    "role":"tool",
                    "tool_call_id":tool_call.id,
                    "content":json.dumps(result)
                })

            try:
                response=client.chat.completions(
                    model=MODEL_ID,
                    messages=messages,
                    tools=tools_definition,
                    tool_choice="none",
                    temperature=0.2,
                    max_tokens=2048,
                    reasoning_effort=None
                )
            except Exception as e:
                print("Sarvam recommendation follow-up error:",repr(e))
                return {
                    "message":"There was a problem processing the recommendation.",
                    "type":"error"
                }

            response_message=get_response_message(response)

            if response_message is None:
                return {
                    "message":"The AI model returned an empty response.",
                    "type":"error"
                }

        return {
            "text":response_message.content or "",
            "action_data":None
        }

    if is_food and not is_movie and is_food_order and not is_recommendation:
        food_name=user_input

        prefixes=[
            "order me ",
            "order ",
            "get me ",
            "buy me ",
            "buy ",
            "send me ",
            "deliver me ",
            "i want to order ",
            "i want "
        ]

        for prefix in prefixes:
            if food_name.lower().startswith(prefix):
                food_name=food_name[len(prefix):].strip()
                break

        food_name=food_name.strip(" .,!?")

        if not food_name:
            return {
                "message":"Please tell me what food you want to order.",
                "type":"error"
            }

        amount=None
        price_match=re.search(
            r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)",
            food_name,
            re.IGNORECASE
        )

        if price_match:
            try:
                amount=float(price_match.group(1))
                food_name=re.sub(
                    r"\s*(?:for|at|₹|rs\.?|inr)?\s*\d+(?:\.\d+)?\s*(?:rs\.?|inr)?",
                    "",
                    food_name,
                    flags=re.IGNORECASE
                ).strip(" .,!?")
            except:
                amount=None

        try:
            if amount is not None:
                result=await asyncio.to_thread(
                    tools.create_food_razorpay_checkout,
                    food_name=food_name,
                    amount=amount
                )
            else:
                result=await asyncio.to_thread(
                    tools.create_food_razorpay_checkout,
                    food_name=food_name
                )
        except Exception as e:
            print("Food Razorpay checkout error:",repr(e))
            return {
                "message":"Unable to create Razorpay checkout.",
                "type":"error"
            }

        if not result.get("success"):
            return {
                "message":result,
                "type":"error",
                "action_data":result
            }

        return {
            "message":result,
            "type":"checkout",
            "action_data":result
        }

    messages=[
        {
            "role":"system",
            "content":SYSTEM_INSTRUCTION
        }
    ]

    for msg in chat_history:
        if isinstance(msg,dict):
            role=msg.get("role","user")
            if role in ["user","assistant","system"]:
                messages.append({
                    "role":role,
                    "content":msg.get("content","")
                })

    messages.append({
        "role":"user",
        "content":user_prompt
    })

    action_data=None

    try:
        response=client.chat.completions(
            model=MODEL_ID,
            messages=messages,
            tools=tools_definition,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=2048,
            reasoning_effort=None
        )
    except Exception as e:
        print("Sarvam error:",repr(e))
        return {
            "message":"Sorry, I couldn't connect to the AI service.",
            "type":"error"
        }

    response_message=get_response_message(response)

    if response_message is None:
        return {
            "message":"The AI model returned an empty response.",
            "type":"error"
        }

    while getattr(response_message,"tool_calls",None):
        messages.append({
            "role":"assistant",
            "content":response_message.content or "",
            "tool_calls":[
                {
                    "id":tc.id,
                    "type":tc.type,
                    "function":{
                        "name":tc.function.name,
                        "arguments":tc.function.arguments
                    }
                }
                for tc in response_message.tool_calls
            ]
        })

        for tool_call in response_message.tool_calls:
            function_name=tool_call.function.name

            try:
                function_args=json.loads(tool_call.function.arguments)
            except:
                function_args={}

            function_to_call=tools_map.get(function_name)

            if function_to_call is None:
                result={
                    "error":f"Unknown tool: {function_name}"
                }
            else:
                try:
                    if asyncio.iscoroutinefunction(function_to_call):
                        result=await function_to_call(**function_args)
                    else:
                        result=await asyncio.to_thread(
                            function_to_call,
                            **function_args
                        )
                except Exception as e:
                    print(f"Tool error ({function_name}):",repr(e))
                    result={
                        "error":str(e)
                    }

            action_data=result

            if function_name=="get_food_recommendations":
                save_food_options(result)

            if function_name=="search_merchant_products":
                save_movie_options(result)

            if function_name=="create_razorpay_checkout":
                return {
                    "message":result,
                    "type":"checkout",
                    "action_data":result
                }

            if function_name=="create_food_razorpay_checkout":
                return {
                    "message":result,
                    "type":"checkout",
                    "action_data":result
                }

            messages.append({
                "role":"tool",
                "tool_call_id":tool_call.id,
                "content":(
                    json.dumps(result)
                    if not isinstance(result,str)
                    else result
                )
            })

        try:
            response=client.chat.completions(
                model=MODEL_ID,
                messages=messages,
                tools=tools_definition,
                tool_choice="auto",
                temperature=0.2,
                max_tokens=2048,
                reasoning_effort=None
            )
        except Exception as e:
            print("Sarvam follow-up error:",repr(e))
            return {
                "message":"There was a problem processing the request.",
                "type":"error"
            }

        response_message=get_response_message(response)

        if response_message is None:
            return {
                "message":"The AI model returned an empty response.",
                "type":"error"
            }

    return {
        "text":response_message.content or "",
        "action_data":action_data
    }