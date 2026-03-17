from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from app.database import init_db, get_db, add_key, get_available_key, mark_key_used, count_available
from app.whatsapp import send_message, download_image
from app.ai import analyze_receipt
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

PLANS = {
    "1": "1 dia",
    "7": "7 dias",
    "15": "15 dias",
    "30": "30 dias",
}

OWNER_PHONE = os.getenv("OWNER_PHONE", "")  # Seu número para alertas de estoque baixo

# Estado de conversa por cliente (em memória)
states: dict = {}

MENU = (
    "👋 Olá! Bem-vindo!\n\n"
    "Escolha o plano de acesso:\n\n"
    "1️⃣ - 1 dia\n"
    "2️⃣ - 7 dias\n"
    "3️⃣ - 15 dias\n"
    "4️⃣ - 30 dias\n\n"
    "Responda com o número do plano desejado."
)

PLAN_MAP = {"1": "1", "2": "7", "3": "15", "4": "30"}


@app.on_event("startup")
def startup():
    init_db()
    logger.info("Banco de dados iniciado.")


# ─── Webhook WhatsApp ────────────────────────────────────────────────────────

@app.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        logger.info(f"Webhook: {body}")

        # Z-API envia mensagens próprias com isFromMe
        if body.get("isFromMe") or body.get("fromMe"):
            return {"status": "ignored"}

        phone   = body.get("phone", "")
        text    = (body.get("text", {}).get("message") or "").strip()
        is_image = body.get("type") == "image"
        image_b64 = None

        if is_image:
            image_b64 = await download_image(body)

        if not phone:
            return {"status": "no phone"}

        await handle(phone, text, image_b64, db)
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Erro no webhook: {e}", exc_info=True)
        return {"status": "error"}


async def handle(phone: str, text: str, image_b64: str | None, db: Session):
    state = states.get(phone, {})
    step  = state.get("step", "start")

    # Qualquer mensagem inicial ou "menu" reinicia
    if step == "start" or text.lower() in ["oi", "olá", "ola", "menu", "inicio", "início", "ola!"]:
        await send_message(phone, MENU)
        states[phone] = {"step": "awaiting_plan"}
        return

    if step == "awaiting_plan":
        plan_key = PLAN_MAP.get(text)
        if not plan_key:
            await send_message(phone, "❌ Opção inválida. Responda com 1, 2, 3 ou 4.")
            return

        # Verifica estoque antes de confirmar
        if count_available(db, plan_key) == 0:
            await send_message(
                phone,
                f"⚠️ O plano de *{PLANS[plan_key]}* está temporariamente indisponível.\n"
                "Por favor, escolha outro plano ou tente mais tarde."
            )
            # Alerta o dono
            if OWNER_PHONE:
                await send_message(OWNER_PHONE, f"🚨 Estoque ZERADO para o plano {PLANS[plan_key]}!")
            return

        states[phone] = {"step": "awaiting_receipt", "plan": plan_key}
        await send_message(
            phone,
            f"✅ Plano *{PLANS[plan_key]}* selecionado!\n\n"
            "Agora envie o *comprovante de pagamento* (print ou foto do PIX)."
        )
        return

    if step == "awaiting_receipt":
        if image_b64 is None:
            await send_message(phone, "📎 Por favor, envie uma *imagem* do comprovante.")
            return

        plan_key = state.get("plan")
        await send_message(phone, "⏳ Verificando comprovante...")

        valid = await analyze_receipt(image_b64)
        if not valid:
            await send_message(
                phone,
                "❌ Não identifiquei um comprovante válido.\n\n"
                "Envie uma foto clara do comprovante do PIX e tente novamente."
            )
            return

        # Busca e entrega a key
        key = get_available_key(db, plan_key)
        if not key:
            await send_message(
                phone,
                "⚠️ Ops! As keys deste plano acabaram neste momento.\n"
                "Aguarde alguns minutos e tente novamente."
            )
            if OWNER_PHONE:
                await send_message(OWNER_PHONE, f"🚨 Estoque acabou durante atendimento! Plano: {PLANS[plan_key]}")
            return

        mark_key_used(db, key, phone)
        states.pop(phone, None)

        await send_message(
            phone,
            f"✅ *Pagamento confirmado!*\n\n"
            f"🔑 Sua chave de acesso:\n"
            f"```{key.value}```\n\n"
            f"⏱ Validade: *{PLANS[plan_key]}*\n\n"
            f"Qualquer dúvida, é só chamar. Bom acesso! 🚀"
        )

        # Alerta dono se estoque baixo
        remaining = count_available(db, plan_key)
        if OWNER_PHONE and remaining <= 3:
            await send_message(
                OWNER_PHONE,
                f"⚠️ Estoque baixo! Plano {PLANS[plan_key]}: apenas *{remaining}* key(s) restante(s)."
            )
        return

    # Fallback
    await send_message(phone, MENU)
    states[phone] = {"step": "awaiting_plan"}


# ─── Painel Admin ────────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(db: Session = Depends(get_db)):
    stocks = {plan: count_available(db, plan) for plan in PLANS}
    rows = "".join(
        f"<tr><td>{PLANS[p]}</td><td><b>{stocks[p]}</b> disponíveis</td></tr>"
        for p in PLANS
    )
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
      <meta charset="UTF-8">
      <title>Painel Admin - Keys</title>
      <style>
        body {{ font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }}
        h1 {{ color: #333; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: left; }}
        th {{ background: #f5f5f5; }}
        textarea {{ width: 100%; height: 120px; font-family: monospace; }}
        select, button {{ padding: 8px 16px; margin-top: 8px; }}
        button {{ background: #25D366; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #1ebe57; }}
        .success {{ color: green; font-weight: bold; }}
      </style>
    </head>
    <body>
      <h1>🔑 Painel de Keys</h1>

      <h2>📦 Estoque atual</h2>
      <table>
        <tr><th>Plano</th><th>Quantidade</th></tr>
        {rows}
      </table>

      <h2>➕ Adicionar Keys</h2>
      <form method="POST" action="/admin/add">
        <label>Plano:</label><br>
        <select name="plan">
          <option value="1">1 dia</option>
          <option value="7">7 dias</option>
          <option value="15">15 dias</option>
          <option value="30">30 dias</option>
        </select><br><br>
        <label>Keys (uma por linha):</label><br>
        <textarea name="keys" placeholder="KEY-XXXX-YYYY&#10;KEY-AAAA-BBBB&#10;..."></textarea><br>
        <input type="password" name="password" placeholder="Senha admin" required><br>
        <button type="submit">Adicionar Keys</button>
      </form>
    </body>
    </html>
    """


@app.post("/admin/add", response_class=HTMLResponse)
async def admin_add(
    plan: str = Form(...),
    keys: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if password != ADMIN_PASSWORD:
        return "<h2 style='color:red'>❌ Senha incorreta.</h2><a href='/admin'>Voltar</a>"

    lines = [k.strip() for k in keys.strip().splitlines() if k.strip()]
    added = 0
    for line in lines:
        try:
            add_key(db, line, plan)
            added += 1
        except Exception:
            pass  # Ignora keys duplicadas

    return (
        f"<h2 style='color:green'>✅ {added} key(s) adicionada(s) ao plano {PLANS.get(plan, plan)}!</h2>"
        f"<a href='/admin'>← Voltar ao painel</a>"
    )
