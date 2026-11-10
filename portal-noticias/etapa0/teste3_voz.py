"""Teste 3: síntese de voz em português do Brasil.

Gera a mesma amostra de cerca de um minuto em até três serviços e mede duração
(ffprobe), caracteres cobrados e custo por minuto:
- ElevenLabs: POST /v1/text-to-speech/{voice_id} (eleven_multilingual_v2 e eleven_v4)
- xAI: POST /v1/tts (language pt-BR, US$ 15 por 1 milhão de caracteres)
- OpenAI: /v1/audio/speech com gpt-4o-mini-tts (depreciado, desliga em 06/01/2027)

Documentação consultada em 10/11/2026:
- https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- https://docs.x.ai/developers/model-capabilities/audio/text-to-speech
- https://developers.openai.com/api/docs/guides/text-to-speech

Uso: ELEVENLABS_API_KEY=... XAI_API_KEY=... OPENAI_API_KEY=... python teste3_voz.py
Serviços sem chave no ambiente são pulados.
"""
import datetime as dt
import json
import os
import pathlib
import subprocess

import requests

from precos import VOZ_POR_MILHAO_CHARS

SAIDA = pathlib.Path(__file__).parent / "saida"
SAIDA.mkdir(exist_ok=True)

# Roteiro de cerca de um minuto (perto de 160 palavras), no estilo do resumo diário.
TEXTO = (
    "Bom dia. Este é o resumo das notícias verificadas de hoje. "
    "O Supremo Tribunal Federal concluiu o julgamento sobre a validade de normas estaduais "
    "que tratam de licenciamento ambiental. Por maioria, os ministros entenderam que os "
    "estados podem legislar de forma complementar, desde que não reduzam a proteção prevista "
    "na lei federal. A decisão vale para todos os tribunais do país. "
    "Na tecnologia, uma fabricante de processadores anunciou uma nova geração de chips "
    "voltada a notebooks, com consumo de energia cerca de trinta por cento menor, segundo o "
    "comunicado oficial. Os primeiros aparelhos devem chegar às lojas no início do ano que vem. "
    "Em ciência, um estudo publicado em revista revisada por pares acompanhou quase dois mil "
    "adultos durante dez anos e associou o sono regular a um menor declínio da memória. Os "
    "autores lembram que o estudo é observacional e não prova causa e efeito. "
    "Essas foram as notícias de hoje. Até amanhã."
)


def duracao_segundos(arquivo: pathlib.Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arquivo)],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def registrar(nome: str, arquivo: pathlib.Path, chave_preco: str, chars: int) -> dict:
    dur = duracao_segundos(arquivo)
    custo = chars / 1e6 * VOZ_POR_MILHAO_CHARS[chave_preco]
    return {"servico": nome, "arquivo": arquivo.name, "caracteres": chars,
            "duracao_s": round(dur, 1), "custo_amostra_usd": round(custo, 4),
            "custo_por_minuto_usd": round(custo / (dur / 60), 4) if dur else None}


def elevenlabs(resultados: list) -> None:
    chave = os.environ.get("ELEVENLABS_API_KEY")
    if not chave:
        print("ElevenLabs: sem chave, pulando"); return
    h = {"xi-api-key": chave}
    voices = requests.get("https://api.elevenlabs.io/v1/voices", headers=h, timeout=60).json().get("voices", [])
    # Prefere uma voz pré-definida com rótulo de português; senão a primeira voz multilíngue.
    voz = next((v for v in voices if "portug" in json.dumps(v.get("labels", {})).lower()), None) or (voices[0] if voices else None)
    if not voz:
        print("ElevenLabs: nenhuma voz disponível"); return
    for modelo in ("eleven_multilingual_v2", "eleven_v4"):
        r = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voz['voice_id']}",
            params={"output_format": "mp3_44100_128"}, headers={**h, "Content-Type": "application/json"},
            json={"text": TEXTO, "model_id": modelo, **({} if modelo == "eleven_multilingual_v2" else {"language_code": "pt"})},
            timeout=180)
        if r.status_code != 200:
            print(f"ElevenLabs {modelo}: HTTP {r.status_code} {r.text[:200]}"); continue
        arq = SAIDA / f"voz_elevenlabs_{modelo}.mp3"
        arq.write_bytes(r.content)
        reg = registrar(f"ElevenLabs {modelo} (voz {voz['name']})", arq, f"elevenlabs_{modelo}", len(TEXTO))
        resultados.append(reg); print(reg)


def xai(resultados: list) -> None:
    chave = os.environ.get("XAI_API_KEY")
    if not chave:
        print("xAI: sem chave, pulando"); return
    r = requests.post("https://api.x.ai/v1/tts",
                      headers={"Authorization": f"Bearer {chave}", "Content-Type": "application/json"},
                      json={"text": TEXTO, "voice_id": "eve", "language": "pt-BR"}, timeout=180)
    if r.status_code != 200:
        print(f"xAI TTS: HTTP {r.status_code} {r.text[:200]}"); return
    arq = SAIDA / "voz_xai_eve.mp3"
    arq.write_bytes(r.content)
    reg = registrar("xAI TTS (voz eve)", arq, "xai_tts", len(TEXTO))
    resultados.append(reg); print(reg)


def openai_tts(resultados: list) -> None:
    chave = os.environ.get("OPENAI_API_KEY")
    if not chave:
        print("OpenAI: sem chave, pulando"); return
    from openai import OpenAI
    client = OpenAI(api_key=chave)
    arq = SAIDA / "voz_openai_gpt-4o-mini-tts.mp3"
    with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts", voice="coral", input=TEXTO,
            instructions="Fale em português do Brasil, tom de locutor de noticiário, ritmo calmo.") as resp:
        resp.stream_to_file(arq)
    dur = duracao_segundos(arq)
    reg = {"servico": "OpenAI gpt-4o-mini-tts (depreciado; desliga em 06/01/2027)", "arquivo": arq.name,
           "caracteres": len(TEXTO), "duracao_s": round(dur, 1),
           "custo_amostra_usd": None, "custo_por_minuto_usd": None,
           "observacao": "A página de preços de 10/11/2026 não lista mais este modelo; custo não estimado."}
    resultados.append(reg); print(reg)


def main() -> None:
    resultados: list = []
    print(f"Texto: {len(TEXTO)} caracteres, {len(TEXTO.split())} palavras")
    for fn in (elevenlabs, xai, openai_tts):
        try:
            fn(resultados)
        except Exception as e:  # registra e segue para o próximo serviço
            print(f"{fn.__name__}: erro {type(e).__name__}: {str(e)[:200]}")
    destino = SAIDA / "teste3_voz.json"
    destino.write_text(json.dumps({"data": dt.datetime.now(dt.timezone.utc).isoformat(),
                                   "texto_chars": len(TEXTO), "resultados": resultados},
                                  ensure_ascii=False, indent=2))
    print(f"Saída: {destino}")


if __name__ == "__main__":
    main()
