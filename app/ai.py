import anthropic
import os
import logging

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


async def analyze_receipt(image_base64: str) -> bool:
    """
    Usa Claude para verificar se a imagem é um comprovante de pagamento.
    Retorna True se parecer válido.
    """
    try:
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Esta imagem é um comprovante de pagamento PIX ou transferência bancária? "
                                "Responda APENAS com SIM ou NAO."
                            ),
                        },
                    ],
                }
            ],
        )
        answer = response.content[0].text.strip().upper()
        logger.info(f"Análise do comprovante: {answer}")
        return answer == "SIM"
    except Exception as e:
        logger.error(f"Erro ao analisar comprovante: {e}")
        # Em caso de erro na IA, libera a key para não travar o cliente
        return True
