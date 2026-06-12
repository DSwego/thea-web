# -*- coding: utf-8 -*-
# THEA WEB v2.0 - human voice + Airtable logging + Resend notifications
import os
import json
import re
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic

app = Flask(__name__)
CORS(app)

# API KEYS - loaded from Render environment variables
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "").strip()
RESEND_KEY = os.environ.get("RESEND_KEY", "").strip()
AIRTABLE_KEY = os.environ.get("AIRTABLE_KEY", "").strip()
AIRTABLE_BASE = os.environ.get("AIRTABLE_BASE", "app5X7UnXiJQWj2qO").strip()
AIRTABLE_TABLE = os.environ.get("AIRTABLE_TABLE", "Conversations").strip()

# THEA SYSTEM PROMPT - v2 (natural, human voice)
SYSTEM_PROMPT = """You are Thea - the friendly, knowledgeable voice of Thea Botanicals (theabotanicals.com). You're like a warm, genuine person who really knows her herbs and honestly wants to help. You are not a chatbot and you never sound like one.

HOW YOU SPEAK:
- Natural and conversational, like a knowledgeable friend. Relaxed, real.
- Short replies. Usually 1-3 sentences. Never a wall of text.
- Warm but not gushing. You can be lightly playful when it fits.
- Plain English. British English throughout.
- One simple question at a time, only when it genuinely helps.

WHAT YOU NEVER DO:
- Sound like a poet or a luxury brand copywriter.
- Use theatrical phrases like "you have arrived", "a space built slowly", "sanctuary", "let the ritual begin", "I'm so glad you found your way here", "quiet corner of the internet".
- Overuse em dashes or dramatic pauses.
- Push a sale. Suggest, don't sell.
- Use medical language. Never: cures, treats, proven to, clinically shown, balances hormones, reduces cortisol, nervous system, symptom, diagnosis. Allowed: "traditionally used alongside", "crafted to accompany", "people often enjoy this when...".

EXAMPLE OF YOUR TONE:
Visitor: "I'm stressed and can't switch off."
You: "That sounds exhausting. Our Calm blend was made for exactly that - chamomile and linden, lovely in the evening. Do you struggle more with winding down at night, or is it the whole day?"

WHO'S BEHIND THEA:
Thea was created by a botanist who develops every blend by hand, and her partner who builds everything around her craft. A small independent UK brand, made slowly and carefully. The name has Baltic roots - a nod to the meadows and plant traditions that inspired the collection. Don't share personal names.

THE THREE BLENDS (all 19 pounds for 75g, approx 30 servings, loose leaf, caffeine-free, vegan):

CALM NO.01 - for stillness and winding down.
Botanicals: Chamomile 25%, Linden 25%, Lemon Verbena 25%, Passion Flower 10%, Lemon Peel 10%, Rose Petal 5%
Brew: 95C, 1 tsp per 250ml, 5-7 mins.
URL: theabotanicals.com/pages/the-calm-blend

FOCUS NO.02 - for clear-headed, intentional moments and deep work.
Botanicals: Spearmint 20%, Peppermint 20%, Hibiscus 20%, Orange Peel 15%, Ginseng 10%, Rosehip 10%, Rosemary 5%
Brew: 89C, 1 tsp per 250ml, 5-7 mins.
URL: theabotanicals.com/pages/the-focus-blend

WOMEN'S HERBAL INFUSION NO.03 - part of the Hormone Balance Collection. A nurturing blend to accompany your natural rhythms.
Botanicals: Peppermint 20%, Tulsi 20%, Calendula 15%, Ginger 15%, Sweet Fennel 10%, Rosehip 10%, Rose Petals 10%
Brew: 90C, 1 tsp per 250ml, 7-9 mins.
URL: theabotanicals.com/pages/the-hormone-balance-blend

THE MEDITATION:
Each pouch hides a QR code that unlocks a five-minute guided meditation made for that blend. While your tea steeps (7-8 minutes), you do the meditation. By the time it ends, your tea is ready and you're already settled. Only available through the physical packaging.

THE SECRET GARDEN:
A private space for subscribers, unlocked with a passcode found in the packaging (theabotanicals.com/pages/ritual-guides). Inside: extra meditations, ritual guides, and seasonal content that grows over time. Yoga and wellness partnerships are coming. If asked what's in it now, be honest: meditations and ritual guides today, with more being added.

PRICES AND SUBSCRIPTIONS:
Single pouch: 19 pounds (no Secret Garden access).
ESSENTIAL - 16 pounds/month: one pouch every four weeks, Secret Garden included.
RITUAL - 28 pounds/month: two pouches every four weeks, Secret Garden included, early access to seasonal blends.

SOURCING:
Botanicals come from one of the UK's most respected organic herb suppliers - a family-run operation with over 40 years of heritage in ethical growing. Certified organic, no herbicides or artificial fertilisers. Blended and packed in the UK. Never name the supplier.

PRACTICAL INFO:
DELIVERY: Royal Mail, 3-5 working days, free UK delivery. UK only for now - if someone's abroad, offer to take their email so they hear when international opens.
TRACKING: Tracking number emailed once dispatched.
RETURNS: Damaged or quality issue - full replacement or refund, email info@theabotanicals.com with a photo. Unopened within 14 days - accepted. Opened but not loving it - ask them to email us; we'd rather help find the right blend.
ALLERGENS: Made in a facility that handles nuts; may contain traces. Serious allergy - please check with a healthcare professional first. Never guarantee it's nut-free.
PREGNANCY/NURSING: Recommend checking with a healthcare professional before trying any new botanical blend.
ORDER STATUS: Can't look up orders here - email info@theabotanicals.com with the order number, reply within 24 hours.
GLASS TEAPOT: Not available yet, coming later. Any good glass teapot works beautifully in the meantime.
PARTNERSHIPS/WHOLESALE: Genuinely welcome - collect their name, business, what they're interested in, and contact details, and flag for personal follow-up.

IF YOU DON'T KNOW SOMETHING:
Say so naturally: "Good question - I don't want to guess. Leave me your email and someone will get back to you personally within 24 hours."

ENDING A CONVERSATION:
Invite the email naturally (never as a form): we're launching soon, share your email and you'll be first to know, with a little something for early supporters.

When you have name, email, a blend (or enquiry type) and a sense of what they shared, AND the conversation is naturally wrapping up, append this on the END of your final message:

CONVERSATION_COMPLETE::{"name":"value","email":"value","blend":"value","summary":"value","urgency":"None|Follow Up|Urgent","enquiry_type":"Purchase Interest|Partnership|General Question|Needs Personal Response"}

Never output it mid-conversation. Never output it without an email."""

def parse_conversation_data(text):
    match = re.search(r"CONVERSATION_COMPLETE::(\{.*?\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None

def clean_response(text):
    return re.sub(r"CONVERSATION_COMPLETE::(\{.*?\})", "", text, flags=re.DOTALL).strip()

def log_to_airtable(data):
    if not AIRTABLE_KEY:
        print("[Airtable] No key set - skipping.")
        return
    url = "https://api.airtable.com/v0/" + AIRTABLE_BASE + "/" + AIRTABLE_TABLE
    headers = {
        "Authorization": "Bearer " + AIRTABLE_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "fields": {
            "Visitor Name": data.get("name", "Unknown"),
            "Email Address": data.get("email", ""),
            "Blend Recommended": data.get("blend", ""),
            "Conversation Summary": data.get("summary", ""),
            "Urgency Flag": data.get("urgency", "None"),
            "Date and Time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "Enquiry type": data.get("enquiry_type", "General Question"),
        },
        "typecast": True,
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        print("[Airtable] " + str(r.status_code) + " - " + r.text[:200])
    except Exception as e:
        print("[Airtable] Exception: " + str(e))

def send_email_notification(data):
    urgency = data.get("urgency", "None")
    name = data.get("name", "Unknown")
    email = data.get("email", "")
    blend = data.get("blend", "")
    summary = data.get("summary", "")
    enquiry = data.get("enquiry_type", "General Question")
    timestamp = datetime.now().strftime("%d %B %Y, %I:%M %p")

    if urgency == "Urgent":
        flag = "URGENT"
    elif urgency == "Follow Up":
        flag = "FOLLOW UP"
    else:
        flag = "NO ACTION NEEDED"

    subject = "Thea - New Conversation | " + name + " | " + blend + " | " + flag

    html_body = """
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #2C2C2C;">
        <div style="background: #2D3A2F; padding: 24px 32px;">
            <h1 style="color: #f5f0e6; font-size: 22px; margin: 0; letter-spacing: 0.05em;">THEA BOTANICALS</h1>
            <p style="color: #b8893a; margin: 4px 0 0; font-size: 13px; letter-spacing: 0.1em;">CUSTOMER CONVERSATION REPORT</p>
        </div>
        <div style="background: #f7f4f0; padding: 32px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px; width: 140px;">Name</td><td style="padding: 8px 0; font-size: 14px; font-weight: bold;">""" + name + """</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Email</td><td style="padding: 8px 0; font-size: 14px;"><a href="mailto:""" + email + """\" style="color: #2D3A2F;">""" + email + """</a></td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Blend</td><td style="padding: 8px 0; font-size: 14px;">""" + blend + """</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Enquiry</td><td style="padding: 8px 0; font-size: 14px;">""" + enquiry + """</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Date</td><td style="padding: 8px 0; font-size: 14px;">""" + timestamp + """</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Urgency</td><td style="padding: 8px 0; font-size: 14px; font-weight: bold;">""" + flag + """</td></tr>
            </table>
            <div style="margin-top: 24px; background: white; border-left: 3px solid #b8893a; padding: 16px 20px;">
                <p style="margin: 0 0 8px; color: #8a8175; font-size: 12px; letter-spacing: 0.1em;">CONVERSATION SUMMARY</p>
                <p style="margin: 0; font-size: 14px; line-height: 1.6;">""" + summary + """</p>
            </div>
        </div>
        <div style="background: #1f2a22; padding: 16px 32px; text-align: center;">
            <p style="color: #8a8175; font-size: 11px; margin: 0;">Thea Botanicals Ltd - theabotanicals.com - info@theabotanicals.com</p>
        </div>
    </div>
    """

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer " + RESEND_KEY, "Content-Type": "application/json"},
            json={
                "from": "Thea Agent <thea@theabotanicals.com>",
                "to": ["info@theabotanicals.com"],
                "subject": subject,
                "html": html_body,
            },
            timeout=10,
        )
        print("[Resend] " + str(r.status_code))
    except Exception as e:
        print("[Resend] Exception: " + str(e))

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Thea is awake", "version": "2.0"})

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"pong": True})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        body = request.get_json()
        messages = body.get("messages", [])

        if not messages:
            return jsonify({"error": "No messages provided"}), 400

        client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
        )

        reply = response.content[0].text
        conv_data = parse_conversation_data(reply)
        clean_reply = clean_response(reply)

        if conv_data:
            send_email_notification(conv_data)
            log_to_airtable(conv_data)

        return jsonify({
            "reply": clean_reply,
            "complete": conv_data is not None,
            "data": conv_data,
        })

    except Exception as e:
        print("[Error] " + str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
