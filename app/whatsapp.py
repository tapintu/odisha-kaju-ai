import os, httpx

TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN","")
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID","")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION","v23.0")

async def send_text(to: str, text: str):
    if not TOKEN or not PHONE_ID:
        return {"mock": True, "to": to, "text": text}
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type":"application/json"}
    body = {
        "messaging_product":"whatsapp",
        "to": to,
        "type":"text",
        "text":{"body": text[:4096]}
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()

def extract_text_messages(payload):
    out = []
    try:
        for entry in payload.get("entry",[]):
            for change in entry.get("changes",[]):
                value = change.get("value",{})
                contacts = value.get("contacts",[])
                names = {c.get("wa_id"): c.get("profile",{}).get("name") for c in contacts}
                for m in value.get("messages",[]) or []:
                    if m.get("type") == "text":
                        phone = m.get("from")
                        out.append({
                            "phone": phone,
                            "name": names.get(phone),
                            "text": m.get("text",{}).get("body",""),
                            "message_id": m.get("id")
                        })
    except Exception:
        pass
    return out
