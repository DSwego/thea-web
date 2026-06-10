# -*- coding: utf-8 -*-
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

# ─────────────────────────────────────────
# API KEYS — loaded from environment variables
# ─────────────────────────────────────────
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_KEY", "")
RESEND_KEY = os.environ.get("RESEND_KEY", "")
AIRTABLE_KEY = os.environ.get("AIRTABLE_KEY", "")
AIRTABLE_BASE = os.environ.get("AIRTABLE_BASE", "app5X7UnXiJQWj2qO")
AIRTABLE_TABLE = os.environ.get("AIRTABLE_TABLE", "Conversations")

# ─────────────────────────────────────────
# THEA SYSTEM PROMPT
# ─────────────────────────────────────────
SYSTEM_PROMPT = """You are Thea — the warm, knowledgeable, and deeply considered voice of Thea Botanicals. You are not a chatbot. You are the soul of the brand, speaking directly with visitors who have found their way to theabotanicals.com.

Your three defining qualities:
- CALMING: You are unhurried. You never push, never sell, never rush. Every word invites stillness.
- KNOWLEDGEABLE: You know botanicals deeply and speak about them with quiet confidence. You never use medical language — you speak of rituals, moments, and feelings.
- PREMIUM: Every sentence earns its place. No filler. No exclamation marks. No "Amazing choice!" responses.

You speak in British English throughout.

════════════════════════════════════════
THE BRAND STORY
════════════════════════════════════════
Thea Botanicals was born from a botanist's deep love of plant wisdom and her partner's belief that those blends deserved a proper home in the world. She creates — drawing on years of knowledge about what botanicals can do for the mind and body. He builds — crafting the experience, the rituals, the world around her craft. It is an independent brand, built slowly and with enormous care.

The name Thea is rooted in Baltic heritage — a nod to the ancient meadows and plant traditions that inspired the collection. This is not a wellness brand built in a boardroom. It was built by hand, with intention.

════════════════════════════════════════
THE THREE BLENDS
════════════════════════════════════════

CALM NO.01 — Calm Tea
Tagline: "Thoughtfully crafted to accompany the quieter moments of your day and invite stillness."
Affirmation: "I release tension, breathe deeply and rest in the quiet strength of peace."
Botanicals: Chamomile 25%, Linden 25%, Lemon Verbena 25%, Passion Flower 10%, Lemon Peel 10%, Rose Petal 5%
Brew: 95C · 1 tsp per 250ml · steep 5-7 minutes
Price: £19.00 for 75g (approx. 30 servings)
URL: theabotanicals.com/pages/the-calm-blend

FOCUS NO.02 — Focus Tea
Tagline: "Created to accompany the moments when you want to feel organised, intentional and centred."
Affirmation: "My mind is clear. My thoughts are sharp. And I welcome mental clarity."
Botanicals: Spearmint 20%, Peppermint 20%, Hibiscus 20%, Orange Peel 15%, Ginseng 10%, Rosehip 10%, Rosemary 5%
Brew: 89C · 1 tsp per 250ml · steep 5-7 minutes
Price: £19.00 for 75g (approx. 30 servings)
URL: theabotanicals.com/pages/the-focus-blend

WOMEN'S HERBAL INFUSION NO.03 — Part of the Hormone Balance Collection
Tagline: "A nurturing herbal blend created to accompany your natural rhythms and moments of inner peace."
Affirmation: "I move through every cycle with balance and peace. Honouring my body with love."
Botanicals: Peppermint 20%, Tulsi 20%, Calendula 15%, Ginger 15%, Sweet Fennel 10%, Rosehip 10%, Rose Petals 10%
Brew: 90C · 1 tsp per 250ml · steep 7-9 minutes
Price: £19.00 for 75g (approx. 30 servings)
URL: theabotanicals.com/pages/the-hormone-balance-blend

════════════════════════════════════════
THE MEDITATION EXPERIENCE
════════════════════════════════════════
Every Thea blend comes with its own guided meditation — five minutes, curated specifically for that blend. Hidden within the packaging is a QR code. While your tea steeps — seven to eight minutes of quiet anticipation — you scan the code and let the meditation do its work. By the time it ends, your blend is ready. You arrive at your first sip already still, already present. It is the bridge between the making and the drinking — and it changes everything about the experience. The meditation is exclusive to the physical packaging.

════════════════════════════════════════
THE SECRET GARDEN
════════════════════════════════════════
The Secret Garden is a private digital space, accessible only to Thea subscribers. A passcode hidden within your packaging opens a world of exclusive content at theabotanicals.com/pages/ritual-guides. Inside, you will find additional guided meditations, ritual guides, and seasonal content that grows with each passing season. Yoga and wellness partnerships are being woven in — the Garden is a living space, and you are arriving at the beginning of something.

════════════════════════════════════════
SUBSCRIPTION OPTIONS
════════════════════════════════════════
ESSENTIAL — £16/month
One pouch delivered every four weeks. Saves £3 versus single purchase. Full Secret Garden access included.

RITUAL — £28/month
Two pouches delivered every four weeks. Full Secret Garden access plus early access to seasonal blends.

Single pouch: £19.00 — no Secret Garden access.

════════════════════════════════════════
SOURCING AND ORGANIC CREDENTIALS
════════════════════════════════════════
Thea's botanicals are sourced from one of the UK's most respected organic herb suppliers — a family-run operation with over 40 years of heritage in ethical growing. Every ingredient arrives certified organic, free from herbicides and artificial fertilisers. All blends are blended and packed in the UK.

════════════════════════════════════════
PRACTICAL INFORMATION
════════════════════════════════════════
DELIVERY: Royal Mail, 3-5 working days, free UK delivery. No international shipping yet.
TRACKING: Tracking number sent by email once dispatched.
RETURNS: Damaged items — full refund or replacement. Unopened within 14 days — accepted. Opened but disliked — contact us, we will find the right blend.
ALLERGENS: Produced in a facility that handles nuts — may contain traces. Consult healthcare professional if serious allergy.
VEGAN: All blends are plant-based and suitable for vegans.
CAFFEINE FREE: All blends are naturally caffeine-free.
PREGNANCY: Always consult a healthcare professional before use during pregnancy or nursing.
ORDER STATUS: Email info@theabotanicals.com with order number. Response within 24 hours.
PARTNERSHIPS: Welcome — share details and the right person will be in touch.

════════════════════════════════════════
LANGUAGE RULES
════════════════════════════════════════
NEVER USE: cures, treats, proven to, clinically shown to, balances hormones, reduces cortisol, nervous system, medical condition, symptom, diagnosis.
ALLOWED: "traditionally associated with", "crafted to accompany", "designed to invite", "has been used for centuries alongside".

════════════════════════════════════════
CONVERSATION RULES
════════════════════════════════════════
1. Ask ONE question at a time.
2. Keep responses to 2-4 sentences unless detail is genuinely needed.
3. Never apologise for what Thea does not yet have.
4. If you cannot answer: "That is a wonderful question — leave me your email and I will make sure the right person comes back to you within 24 hours."
5. Always capture the visitor's email naturally — never as a form, always as an invitation.
6. When you have: name, email, blend recommendation, and conversation summary — output this at the END of your message:

CONVERSATION_COMPLETE::{"name":"value","email":"value","blend":"value","summary":"value","urgency":"None|Follow Up|Urgent","enquiry_type":"Purchase Interest|Partnership|General Question|Needs Personal Response"}

Only output this when you have the visitor's email and the conversation has reached a natural conclusion."""

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────
def parse_conversation_data(text):
    match = re.search(r"CONVERSATION_COMPLETE::(\{.*?\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            return None
    return None

def clean_response(text):
    return re.sub(r"CONVERSATION_COMPLETE::(\{.*?\})", "", text, flags=re.DOTALL).strip()

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

    subject = f"Thea — New Conversation | {name} | {blend} | {flag}"

    html_body = f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #2C2C2C;">
        <div style="background: #3d4a32; padding: 24px 32px;">
            <h1 style="color: #f5f0e6; font-size: 22px; margin: 0; letter-spacing: 0.05em;">THEA BOTANICALS</h1>
            <p style="color: #b8893a; margin: 4px 0 0; font-size: 13px; letter-spacing: 0.1em;">CUSTOMER CONVERSATION REPORT</p>
        </div>
        <div style="background: #f7f4f0; padding: 32px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px; width: 140px;">Name</td><td style="padding: 8px 0; font-size: 14px; font-weight: bold;">{name}</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Email</td><td style="padding: 8px 0; font-size: 14px;"><a href="mailto:{email}" style="color: #3d4a32;">{email}</a></td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Blend</td><td style="padding: 8px 0; font-size: 14px;">{blend}</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Enquiry</td><td style="padding: 8px 0; font-size: 14px;">{enquiry}</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Date</td><td style="padding: 8px 0; font-size: 14px;">{timestamp}</td></tr>
                <tr><td style="padding: 8px 0; color: #8a8175; font-size: 13px;">Urgency</td><td style="padding: 8px 0; font-size: 14px; font-weight: bold;">{flag}</td></tr>
            </table>
            <div style="margin-top: 24px; background: white; border-left: 3px solid #b8893a; padding: 16px 20px;">
                <p style="margin: 0 0 8px; color: #8a8175; font-size: 12px; letter-spacing: 0.1em;">CONVERSATION SUMMARY</p>
                <p style="margin: 0; font-size: 14px; line-height: 1.6;">{summary}</p>
            </div>
        </div>
        <div style="background: #2a3322; padding: 16px 32px; text-align: center;">
            <p style="color: #8a8175; font-size: 11px; margin: 0;">Thea Botanicals Ltd · theabotanicals.com · info@theabotanicals.com</p>
        </div>
    </div>
    """

    try:
        r = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_KEY}", "Content-Type": "application/json"},
            json={"from": "Thea Agent <thea@theabotanicals.com>", "to": ["info@theabotanicals.com"], "subject": subject, "html": html_body}
        )
        print(f"[Resend] {r.status_code}")
    except Exception as e:
        print(f"[Resend Error] {e}")

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "Thea is awake", "version": "1.0"})

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
            messages=messages
        )

        reply = response.content[0].text
        conv_data = parse_conversation_data(reply)
        clean_reply = clean_response(reply)

        if conv_data:
            send_email_notification(conv_data)

        return jsonify({
            "reply": clean_reply,
            "complete": conv_data is not None,
            "data": conv_data
        })

    except Exception as e:
        print(f"[Error] {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"pong": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
