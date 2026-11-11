"""Registro de custos e teto de gasto.

Antes de cada chamada paga, `reservar()` confere se o gasto do dia e do mês, somado às
reservas em andamento e à estimativa da chamada, cabe nos tetos do painel. Se não couber,
levanta TetoAtingido e a execução para. Depois da chamada, `registrar()` grava o custo real
(inclusive de chamadas que falharam, que também são cobradas).
"""
import datetime as dt
import threading
from zoneinfo import ZoneInfo

from . import config, db

# Estimativas conservadoras por chamada, a partir das medições da Etapa 0.
ESTIMATIVA_USD = {
    "coleta_x": 0.80,
    "selecao": 0.05,
    "verificacao": 0.08,
    "confirmacao": 0.20,   # Sonnet no pior caso medido; Haiku custa bem menos
    "redacao": 0.10,
    "voz": 0.05,
}


class TetoAtingido(RuntimeError):
    pass


_trava = threading.Lock()
_reservado = 0.0


def agora() -> dt.datetime:
    return dt.datetime.now(ZoneInfo(config.FUSO))


def gasto(periodo: str) -> float:
    """Soma do gasto no dia ou no mês corrente (fuso do portal)."""
    hoje = agora()
    prefixo = hoje.strftime("%Y-%m-%d") if periodo == "dia" else hoje.strftime("%Y-%m")
    linha = db.consultar("SELECT COALESCE(SUM(custo_usd), 0) AS total FROM custos WHERE quando LIKE ?",
                         (prefixo + "%",))[0]
    return float(linha["total"])


def reservar(etapa: str, estimativa: float | None = None) -> float:
    global _reservado
    est = ESTIMATIVA_USD.get(etapa, 0.1) if estimativa is None else estimativa
    tetos = db.ler_config()["tetos"]
    with _trava:
        dia, mes = gasto("dia") + _reservado + est, gasto("mes") + _reservado + est
        if dia > float(tetos["diario_usd"]):
            raise TetoAtingido(f"teto diário de US$ {tetos['diario_usd']:.2f} seria ultrapassado "
                               f"(gasto e reservas: US$ {dia - est:.2f}; próxima chamada: até US$ {est:.2f})")
        if mes > float(tetos["mensal_usd"]):
            raise TetoAtingido(f"teto mensal de US$ {tetos['mensal_usd']:.2f} seria ultrapassado "
                               f"(gasto e reservas: US$ {mes - est:.2f}; próxima chamada: até US$ {est:.2f})")
        _reservado += est
    return est


def registrar(reserva: float, execucao_id: int | None, etapa: str, tema: str | None, provedor: str,
              modelo: str | None, custo_usd: float, sucesso: bool = True, detalhe: str | None = None,
              uso: dict | None = None) -> None:
    global _reservado
    db.inserir("custos", execucao_id=execucao_id, quando=agora().isoformat(timespec="seconds"),
               etapa=etapa, tema=tema, provedor=provedor, modelo=modelo, custo_usd=round(custo_usd, 6),
               sucesso=int(sucesso), detalhe=detalhe, uso=uso)
    with _trava:
        _reservado = max(0.0, _reservado - reserva)


def liberar(reserva: float) -> None:
    """Desfaz uma reserva quando a chamada nem chegou a ser feita."""
    global _reservado
    with _trava:
        _reservado = max(0.0, _reservado - reserva)
