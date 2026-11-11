"""Configuração do Briefing de Notícias.

Há dois níveis de configuração:
- variáveis de ambiente (arquivo .env fora do git): chaves de API, pasta de dados, segredo da sessão;
- configuração editável pelo painel, guardada no banco (tabela `config`). Os valores abaixo em
  PADRAO são usados na primeira execução e sempre que um campo não estiver no banco.
"""
import os
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent
PASTA_DADOS = pathlib.Path(os.environ.get("PORTAL_DADOS", RAIZ.parent / "dados")).resolve()
PASTA_AUDIOS = PASTA_DADOS / "audios"
ARQUIVO_BANCO = PASTA_DADOS / "briefing.sqlite3"
PASTA_PROMPTS = RAIZ / "prompts"
FUSO = os.environ.get("PORTAL_FUSO", "America/Sao_Paulo")


def chave(nome: str) -> str | None:
    """Lê uma chave de API do ambiente. PORTAL_ANTHROPIC_KEY é aceita como alternativa."""
    if nome == "ANTHROPIC_API_KEY":
        return os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("PORTAL_ANTHROPIC_KEY")
    return os.environ.get(nome)


AGENCIA_BRASIL = "https://agenciabrasil.ebc.com.br/rss/{}/feed.xml"

PADRAO = {
    # Modelos por papel. Nomes ficam aqui (e no painel), nunca espalhados pelo código.
    "modelos": {
        "coleta_x": "grok-4.7",
        "selecao": "gpt-6.1-terra",
        "verificacao": "gpt-6.1-sol",
        "confirmacao": "claude-sonnet-5-5",  # teste 2C: 0 erros publicados, 0 verdadeiras bloqueadas
        "redacao": "gpt-6.1-sol",
        "voz": "xai",            # xai (medido no teste 3); elevenlabs quando a chave for corrigida
        "voz_id": "eve",
    },
    "tetos": {"diario_usd": 10.0, "mensal_usd": 200.0},
    "agenda": {"ativa": True, "hora": "06:30"},
    "limites": {
        "posts_por_tema": 8,          # posts do X pedidos ao Grok
        "max_turns_x": 2,             # rodadas de busca do Grok (principal alavanca de custo)
        "novas_tentativas_x": 1,      # chamadas que falham na xAI também são cobradas
        "itens_oficiais_por_tema": 15,
        "horas_janela": 36,           # idade máxima dos itens oficiais
        "afirmacoes_por_candidato": 4,
        "minimo_afirmacoes_aprovadas": 2,
        "paralelismo": 4,             # verificações simultâneas
    },
    "temas": [
        {"id": "direito", "nome": "Direito", "ativo": True, "candidatos": 3, "publicar": 3,
         "descricao": "Direito no Brasil: leis novas, mudanças normativas e debates jurídicos relevantes",
         "perfis": ["JotaInfo", "migalhas", "OABNacional", "CNJ_oficial"],
         "feeds": [AGENCIA_BRASIL.format("justica"), "https://www.camara.leg.br/noticias/rss/ultimas-noticias"]},
        {"id": "tribunais", "nome": "Tribunais superiores", "ativo": True, "candidatos": 3, "publicar": 3,
         "descricao": "Decisões e julgamentos do STF, STJ, TST e TSE",
         "perfis": ["STF_oficial", "STJnoticias", "TSEjusbr", "CNJ_oficial"],
         "feeds": [AGENCIA_BRASIL.format("justica")]},
        {"id": "politica", "nome": "Política", "ativo": True, "candidatos": 3, "publicar": 3,
         "descricao": "Política nacional: Congresso, governo federal e projetos de lei em tramitação",
         "perfis": ["camaradeputados", "SenadoFederal"],
         "feeds": ["https://www.camara.leg.br/noticias/rss/ultimas-noticias",
                   "https://www12.senado.leg.br/noticias/rss", AGENCIA_BRASIL.format("politica")]},
        {"id": "tecnologia", "nome": "Tecnologia", "ativo": True, "candidatos": 3, "publicar": 3,
         "descricao": "Tecnologia: lançamentos de produtos e inovações anunciadas por fabricantes",
         "perfis": ["Apple", "Google", "Samsung", "nvidia", "Microsoft", "OpenAI", "AnthropicAI",
                    "xai", "intel", "AMD", "Qualcomm", "tecmundo", "tecnoblog", "canaltech"],
         "feeds": ["https://www.apple.com/newsroom/rss-feed.rss", "https://news.samsung.com/global/feed",
                   "https://nvidianews.nvidia.com/releases.xml", "https://news.microsoft.com/source/feed/",
                   "https://blog.google/rss/"]},
        {"id": "cultura", "nome": "Cultura", "ativo": True, "candidatos": 3, "publicar": 3,
         "descricao": "Cultura: livros, cinema, música, exposições e patrimônio cultural no Brasil",
         "perfis": [],
         "feeds": [AGENCIA_BRASIL.format("cultura")]},
        {"id": "ciencia", "nome": "Ciência", "ativo": True, "candidatos": 3, "publicar": 3,
         "descricao": "Curiosidade e ciência: descobertas científicas, em especial sobre o cérebro humano",
         "perfis": [],
         "feeds": ["https://www.sciencedaily.com/rss/mind_brain.xml", "https://www.nature.com/nature.rss",
                   "https://jornal.usp.br/feed/", "https://www.nasa.gov/feed/"]},
    ],
}
