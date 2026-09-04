import os, json, re, httpx
from . import db

OPENAI_KEY = os.getenv("OPENAI_API_KEY","")
MODEL = os.getenv("OPENAI_MODEL","gpt-5.6-luna")

SYSTEM = """You are the WhatsApp sales assistant for Odisha Kaju / Jyotsna Enterprises, an Indian B2B cashew business.
Be concise, polite, human, and sales-oriented. Reply in the customer's language when practical, including English, Hindi, Odia, or mixed Indian English.

STRICT RULES:
1. Never invent a price, stock quantity, MOQ, discount, credit term, bank detail, delivery promise, or policy.
2. For current price/stock/MOQ, use the supplied verified product data.
3. Discounts, credit, complaints/refunds, bank-detail changes, legal issues, unusual delivery guarantees, and exceptional commercial terms require owner approval.
4. Ask only one or two useful questions at a time. Prefer grade, quantity, city/pincode, and purchase timing.
5. Minimum order must come from verified product data.
6. Do not claim an owner has approved something unless an approval answer is explicitly supplied.
7. Keep WhatsApp replies short unless the customer asks for detail.
"""

SENSITIVE_PATTERNS = {
    "discount": r"\b(discount|best rate|final rate|less rate|reduce|kam karo|lowest|₹\s*\d+|rs\.?\s*\d+)\b",
    "credit": r"\b(credit|udhar|days credit|7 day|15 day|30 day)\b",
    "complaint": r"\b(refund|complaint|damaged|bad quality|return|replace)\b",
    "bank": r"\b(bank account|account number|ifsc|upi change|payment details change)\b",
    "delivery": r"\b(guarantee delivery|guaranteed delivery|within 24 hours|same day)\b",
    "legal": r"\b(legal|lawyer|court|notice|case)\b"
}

def sensitive_category(text):
    t = text.lower()
    for cat,pat in SENSITIVE_PATTERNS.items():
        if re.search(pat,t,re.I):
            if cat=="discount" and any(k in t for k in ["price","rate","what rate","kitna","kya rate"]) and not any(k in t for k in ["best","final","discount","reduce","lowest","kam"]):
                continue
            return cat
    return None

def detect_grade(text):
    t = text.upper().replace("-","").replace(" ","")
    grades = ["W160","W180","W210","W240","W320","W400","JJH","SJH","JH","LWP","KK","SW","K"]
    for g in grades:
        if g.replace(" ","") in t:
            return g
    return None

async def call_openai(phone, user_text, verified_product=None, owner_answer=None):
    if not OPENAI_KEY:
        if verified_product:
            return f"{verified_product['grade']} is ₹{verified_product['price']:.0f}/kg. Stock available: {verified_product['stock']:.0f} kg. MOQ: {verified_product['moq']:.0f} kg. Please share required quantity and delivery city."
        return "Thank you for your enquiry. Please share the cashew grade, required quantity, and delivery city."

    hist = db.history(phone, 10)
    context = {"verified_product": verified_product, "owner_answer": owner_answer}
    input_items = [{"role":"system","content":SYSTEM + "\nVERIFIED BUSINESS CONTEXT:\n" + json.dumps(context,ensure_ascii=False)}]
    for h in hist:
        role = "assistant" if h["role"]=="assistant" else "user"
        input_items.append({"role":role,"content":h["content"]})
    input_items.append({"role":"user","content":user_text})

    headers={"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"}
    payload={"model":MODEL,"input":input_items}
    async with httpx.AsyncClient(timeout=60) as client:
        r=await client.post("https://api.openai.com/v1/responses",headers=headers,json=payload)
        r.raise_for_status()
        data=r.json()

    if data.get("output_text"):
        return data["output_text"].strip()
    chunks=[]
    for item in data.get("output",[]):
        for c in item.get("content",[]):
            if c.get("type") in ("output_text","text") and c.get("text"):
                chunks.append(c["text"])
    return "\n".join(chunks).strip() or "Please share the grade, quantity, and delivery city."

async def handle_customer_message(phone, text, name=None):
    db.add_message(phone,"user",text)
    if name:
        db.set_customer_fields(phone,name=name)

    grade = detect_grade(text)
    product = db.get_product(grade) if grade else None
    if grade:
        db.set_customer_fields(phone,grade=grade)

    cat = sensitive_category(text)
    if cat:
        approval_id = db.create_approval(phone,cat,text)
        reply = "I’m checking this with our team and will confirm shortly."
        db.add_message(phone,"assistant",reply)
        return {"reply":reply,"needs_approval":True,"approval_id":approval_id}

    reply = await call_openai(phone,text,verified_product=product)
    db.add_message(phone,"assistant",reply)
    return {"reply":reply,"needs_approval":False}
