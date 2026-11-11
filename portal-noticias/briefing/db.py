"""Banco SQLite: um arquivo em disco, cópia de segurança é copiar o arquivo.

Rastreabilidade: cada notícia aponta para o candidato; cada candidato guarda as origens
(posts do X e itens oficiais); cada afirmação guarda a fonte e o trecho do verificador e a
decisão do confirmador; cada chamada paga grava uma linha em `custos`.
"""
import copy
import json
import sqlite3
import threading
from contextlib import contextmanager

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS config (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS execucoes (
    id INTEGER PRIMARY KEY, inicio TEXT NOT NULL, fim TEXT, data_edicao TEXT NOT NULL,
    gatilho TEXT NOT NULL, status TEXT NOT NULL, mensagem TEXT, versao_prompts TEXT, temas TEXT);
CREATE TABLE IF NOT EXISTS custos (
    id INTEGER PRIMARY KEY, execucao_id INTEGER, quando TEXT NOT NULL, etapa TEXT NOT NULL,
    tema TEXT, provedor TEXT NOT NULL, modelo TEXT, custo_usd REAL NOT NULL, sucesso INTEGER NOT NULL,
    detalhe TEXT, uso TEXT);
CREATE TABLE IF NOT EXISTS posts_origem (
    id INTEGER PRIMARY KEY, execucao_id INTEGER NOT NULL, tema TEXT NOT NULL, link TEXT, autor TEXT,
    texto TEXT, assunto TEXT, coletado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS itens_oficiais (
    id INTEGER PRIMARY KEY, execucao_id INTEGER NOT NULL, tema TEXT NOT NULL, fonte TEXT, titulo TEXT,
    link TEXT, publicado_em TEXT, resumo TEXT, coletado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidatos (
    id INTEGER PRIMARY KEY, execucao_id INTEGER NOT NULL, tema TEXT NOT NULL, titulo TEXT NOT NULL,
    resumo TEXT, origens TEXT, status TEXT NOT NULL, motivo TEXT);
CREATE TABLE IF NOT EXISTS afirmacoes (
    id INTEGER PRIMARY KEY, candidato_id INTEGER NOT NULL, ordem INTEGER, texto TEXT NOT NULL,
    status_verificador TEXT, url_verificador TEXT, trecho_verificador TEXT, justificativa_verificador TEXT,
    urls_consultadas TEXT, modelo_confirmador TEXT, confirmador_concorda INTEGER, status_confirmador TEXT,
    url_confirmador TEXT, trecho_confirmador TEXT, justificativa_confirmador TEXT,
    decisao TEXT, verificado_em TEXT, confirmado_em TEXT);
CREATE TABLE IF NOT EXISTS noticias (
    id INTEGER PRIMARY KEY, candidato_id INTEGER NOT NULL, execucao_id INTEGER NOT NULL, tema TEXT NOT NULL,
    data_edicao TEXT NOT NULL, titulo TEXT NOT NULL, linha_fina TEXT, corpo TEXT NOT NULL, roteiro TEXT,
    referencias TEXT, publicado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audios (
    id INTEGER PRIMARY KEY, execucao_id INTEGER NOT NULL, noticia_id INTEGER, tipo TEXT NOT NULL,
    data_edicao TEXT NOT NULL, arquivo TEXT NOT NULL, caracteres INTEGER, duracao_s REAL, criado_em TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_custos_quando ON custos(quando);
CREATE INDEX IF NOT EXISTS idx_noticias_data ON noticias(data_edicao);
CREATE VIEW IF NOT EXISTS descartes AS
    SELECT c.*, e.data_edicao FROM candidatos c JOIN execucoes e ON e.id = c.execucao_id
    WHERE c.status = 'descartado';
"""

_trava = threading.Lock()


def conectar() -> sqlite3.Connection:
    config.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.ARQUIVO_BANCO, timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def iniciar() -> None:
    with conectar() as con:
        con.executescript(ESQUEMA)


@contextmanager
def transacao():
    """Escrita serializada: várias threads de verificação gravam ao mesmo tempo."""
    with _trava:
        con = conectar()
        try:
            yield con
            con.commit()
        finally:
            con.close()


def consultar(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    con = conectar()
    try:
        return con.execute(sql, params).fetchall()
    finally:
        con.close()


def inserir(tabela: str, **campos) -> int:
    nomes = ", ".join(campos)
    marcas = ", ".join("?" for _ in campos)
    valores = tuple(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for v in campos.values())
    with transacao() as con:
        return con.execute(f"INSERT INTO {tabela} ({nomes}) VALUES ({marcas})", valores).lastrowid


def atualizar(tabela: str, id_: int, **campos) -> None:
    pares = ", ".join(f"{k} = ?" for k in campos)
    valores = tuple(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for v in campos.values())
    with transacao() as con:
        con.execute(f"UPDATE {tabela} SET {pares} WHERE id = ?", (*valores, id_))


# Configuração editável -----------------------------------------------------------------

def ler_config() -> dict:
    cfg = copy.deepcopy(config.PADRAO)
    for linha in consultar("SELECT chave, valor FROM config"):
        valor = json.loads(linha["valor"])
        if isinstance(cfg.get(linha["chave"]), dict) and isinstance(valor, dict):
            cfg[linha["chave"]].update(valor)
        else:
            cfg[linha["chave"]] = valor
    return cfg


def gravar_config(chave: str, valor) -> None:
    with transacao() as con:
        con.execute("INSERT INTO config (chave, valor) VALUES (?, ?) "
                    "ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                    (chave, json.dumps(valor, ensure_ascii=False)))
