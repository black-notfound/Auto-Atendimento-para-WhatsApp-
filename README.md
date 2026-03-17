# 🔑 WhatsApp Keys Bot

Bot de atendimento automático para venda de keys via WhatsApp.

---

## 🚀 Como configurar (passo a passo)

### 1. Z-API
1. Acesse [z-api.io](https://z-api.io) e crie uma conta
2. Crie uma instância e copie o **Instance ID** e o **Token**
3. Conecte seu WhatsApp escaneando o QR Code

### 2. Anthropic API
1. Acesse [console.anthropic.com](https://console.anthropic.com)
2. Crie uma API Key e copie ela

### 3. Deploy no Railway
1. Acesse [railway.app](https://railway.app) e crie uma conta
2. Crie um novo projeto → **Deploy from GitHub**
3. Suba este código num repositório GitHub e conecte
4. Em **Variables**, adicione todas as variáveis do `.env.example`:
   - `ZAPI_INSTANCE_ID`
   - `ZAPI_TOKEN`
   - `ANTHROPIC_API_KEY`
   - `ADMIN_PASSWORD`
   - `OWNER_PHONE`
5. O Railway vai gerar uma URL pública (ex: `https://seu-bot.up.railway.app`)

### 4. Configurar Webhook na Z-API
1. No painel da Z-API, vá em **Webhooks**
2. Configure o webhook de mensagens recebidas para:
   ```
   https://seu-bot.up.railway.app/webhook
   ```

---

## 📦 Adicionar Keys

Acesse o painel admin:
```
https://seu-bot.up.railway.app/admin
```
- Cole as keys geradas (uma por linha)
- Escolha o plano correspondente
- Clique em **Adicionar Keys**

---

## 💬 Fluxo do cliente

1. Cliente manda "Oi" no WhatsApp
2. Bot exibe menu com os 4 planos
3. Cliente escolhe o plano (1, 2, 3 ou 4)
4. Bot pede o comprovante de pagamento
5. Cliente envia foto do comprovante
6. IA valida o comprovante
7. Bot entrega a key automaticamente ✅

---

## ⚠️ Alertas automáticos

O bot te avisa no WhatsApp quando:
- Estoque de um plano chega a 3 ou menos keys
- Estoque zera completamente

---

## 🛠 Rodando localmente (opcional)

```bash
pip install -r requirements.txt
cp .env.example .env
# Edite o .env com suas credenciais
uvicorn app.main:app --reload
```
