import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()

from . import db
from .ai import handle_customer_message, call_openai
from .whatsapp import send_text, extract_text_messages

app = FastAPI(title="Odisha Kaju AI Sales Assistant")
db.init_db()

@app.get("/health")
def health():
    return {"ok":True,"service":"odisha-kaju-ai"}

@app.get("/whatsapp/webhook")
async def verify(request: Request):
    q=request.query_params
    if q.get("hub.mode")=="subscribe" and q.get("hub.verify_token")==os.getenv("WHATSAPP_VERIFY_TOKEN","change-this-secret"):
        return PlainTextResponse(q.get("hub.challenge",""))
    raise HTTPException(403,"Webhook verification failed")

@app.post("/whatsapp/webhook")
async def receive(request: Request):
    payload = await request.json()
    messages = extract_text_messages(payload)
    for m in messages:
        result = await handle_customer_message(m["phone"],m["text"],m.get("name"))
        await send_text(m["phone"], result["reply"])
    return {"received":True,"processed":len(messages)}

class Simulate(BaseModel):
    phone: str="919999999999"
    text: str
    name: str|None=None

@app.post("/simulate")
async def simulate(x: Simulate):
    return await handle_customer_message(x.phone,x.text,x.name)

@app.get("/api/products")
def products():
    return db.list_products()

class ProductUpdate(BaseModel):
    price: float|None=None
    stock: float|None=None
    moq: float|None=None

@app.patch("/api/products/{grade}")
def product_update(grade:str, x:ProductUpdate):
    db.update_product(grade,x.price,x.stock,x.moq)
    return db.get_product(grade)

@app.get("/api/customers")
def customers():
    return db.customers()

@app.get("/api/approvals")
def approvals():
    return db.approvals()

class ApprovalAnswer(BaseModel):
    answer: str

@app.post("/api/approvals/{approval_id}/resolve")
async def approval_resolve(approval_id:int,x:ApprovalAnswer):
    pending = [a for a in db.approvals() if a["id"]==approval_id]
    if not pending:
        raise HTTPException(404,"Approval not found")
    a=pending[0]
    db.resolve_approval(approval_id,x.answer)
    response = await call_openai(a["phone"],
        "Continue the customer conversation based on the owner's decision.",
        owner_answer=x.answer)
    db.add_message(a["phone"],"assistant",response)
    await send_text(a["phone"],response)
    return {"ok":True,"sent":response}

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!doctype html><html><head><meta name=viewport content='width=device-width,initial-scale=1'>
    <style>body{font-family:system-ui;max-width:760px;margin:35px auto;padding:0 16px}code{background:#eee;padding:2px 5px}li{margin:10px 0}</style></head>
    <body><h1>Odisha Kaju AI Sales Assistant</h1>
    <p>Backend is running.</p>
    <ul>
      <li><code>GET /health</code></li>
      <li><code>POST /simulate</code> — test customer messages without WhatsApp</li>
      <li><code>GET /api/products</code></li>
      <li><code>GET /api/customers</code></li>
      <li><code>GET /api/approvals</code></li>
      <li><code>GET/POST /whatsapp/webhook</code></li>
    </ul>
    <p>Use <code>/docs</code> for the interactive API screen.</p></body></html>"""
