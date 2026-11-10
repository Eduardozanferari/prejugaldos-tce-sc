"""Tabela de preços usada pelos testes da Etapa 0.

Todos os valores em dólares, copiados das páginas oficiais em 10/11/2026.
Fontes:
- xAI: https://docs.x.ai/developers/pricing
- OpenAI: https://developers.openai.com/api/docs/pricing
- Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
- ElevenLabs: https://elevenlabs.io/pricing/api
- Google Cloud TTS: https://cloud.google.com/text-to-speech/pricing
Os preços mudam; confira as páginas antes de reutilizar estes números.
"""

DATA_CONSULTA = "2026-11-10"

# Preço por 1 milhão de tokens: (entrada, entrada em cache, saída)
TOKENS = {
    # xAI (contexto curto, < 200k tokens)
    "grok-4.7": (2.00, 0.50, 6.00),
    # OpenAI (modo padrão)
    "gpt-6-astra": (10.00, 1.00, 50.00),
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
    "gpt-6.1-terra": (1.00, 0.05, 5.00),
    "gpt-6-luna": (0.10, 0.01, 0.50),
    # Anthropic
    "claude-opus-5-5": (4.00, 0.20, 20.00),
    "claude-sonnet-5-5": (2.00, 0.10, 10.00),
    "claude-haiku-5-5": (0.10, 0.01, 0.50),
}

# Ferramentas de servidor
FERRAMENTAS = {
    "xai_x_search_por_post": 5.00 / 1000,       # por post buscado
    "xai_x_search_por_perfil": 10.00 / 1000,    # por perfil buscado
    "xai_web_search_por_chamada": 5.00 / 1000,
    "openai_web_search_por_chamada": 10.00 / 1000,  # mais tokens de conteúdo ao preço do modelo
    "anthropic_web_search_por_busca": 10.00 / 1000,
    "anthropic_web_fetch": 0.0,                 # só tokens
}

# Síntese de voz, preço por 1 milhão de caracteres
VOZ_POR_MILHAO_CHARS = {
    "elevenlabs_eleven_v4": 80.00,            # $0.08 por 1k caracteres
    "elevenlabs_eleven_multilingual_v2": 80.00,
    "elevenlabs_eleven_flash_v2_5": 40.00,
    "elevenlabs_eleven_v4_turbo": 40.00,
    "xai_tts": 15.00,
    "google_chirp3_hd": 30.00,                # 1 milhão de caracteres grátis por mês
    "google_neural2": 16.00,                  # 1 milhão grátis por mês
    "google_wavenet_ou_standard": 4.00,       # 4 milhões grátis por mês
}
# OpenAI: gpt-4o-mini-tts e tts-1 estão depreciados (desligamento em 06/01/2027);
# a substituição indicada é gpt-realtime-2.1-mini, cobrada por token de áudio
# (US$ 20 por 1 milhão de tokens de áudio de saída). O custo por minuto é medido no teste 3.


def custo_tokens(modelo: str, entrada: int, saida: int, cache: int = 0) -> float:
    pe, pc, ps = TOKENS[modelo]
    return (entrada - cache) / 1e6 * pe + cache / 1e6 * pc + saida / 1e6 * ps
