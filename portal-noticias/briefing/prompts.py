"""Leitura dos prompts versionados (arquivos .md em prompts/)."""
import hashlib

from . import config


def texto(nome: str) -> str:
    return (config.PASTA_PROMPTS / f"{nome}.md").read_text(encoding="utf-8")


def montar(nome: str, **campos) -> str:
    return texto(nome).format(**campos)


def versao() -> str:
    """Impressão digital dos prompts usados numa execução, gravada em `execucoes`."""
    h = hashlib.sha1()
    for arq in sorted(config.PASTA_PROMPTS.glob("*.md")):
        h.update(arq.name.encode())
        h.update(arq.read_bytes())
    return h.hexdigest()[:12]
