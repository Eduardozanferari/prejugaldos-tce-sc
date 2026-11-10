# Proposta de arquitetura (uma página)

Objetivo: o sistema mais simples que uma pessoa sem formação em programação consiga
manter, atendendo aos requisitos do briefing (banco rastreável, prompts versionados,
teto de gasto, portal protegido por senha, áudio com tela bloqueada).

## Escolhas

| Item | Escolha | Por quê |
| --- | --- | --- |
| Linguagem | Python 3.12 | SDKs oficiais da xAI (compatível com SDK da OpenAI), OpenAI e Anthropic; fácil de ler e ajustar |
| Aplicação web | FastAPI + modelos HTML (Jinja2), sem framework de front-end | Um único processo serve o portal, o painel e a API interna; páginas leves, boa leitura no celular |
| Banco | SQLite, um arquivo em disco | Sem servidor de banco para administrar; cópia de segurança é copiar um arquivo; volume diário pequeno (dezenas de registros) |
| Agendamento | APScheduler dentro do mesmo processo | Horário configurável no painel sem mexer em cron; execução manual pelo painel |
| Prompts | Arquivos `.md` em `prompts/`, um por etapa, versionados no git | Ajustáveis sem tocar no código, com histórico |
| Saídas dos modelos | JSON validado com Pydantic (esquemas em `esquemas/`), até duas novas tentativas | Exigência do briefing; os três provedores suportam saída estruturada |
| Áudio | Arquivos MP3 em disco, servidos pelo próprio app; tocador HTML5 com Media Session API | Media Session mantém a reprodução com a tela bloqueada e mostra controles no celular |
| PWA | `manifest.json` + service worker simples | Instalável no celular; sem notificações nesta versão |
| Senha | Usuário único, senha com hash (argon2), sessão por cookie | Suficiente para uso pessoal |
| Chaves | Variáveis de ambiente (`.env` fora do git) | Exigência do briefing |
| Hospedagem | Um servidor virtual pequeno (1 vCPU, 2 GB) com Docker Compose, ou Fly.io com volume persistente | Um contêiner, um volume; o custo fica entre US$ 5 e US$ 10 por mês |
| Cópia de segurança | Cópia diária do arquivo SQLite e dos MP3 para armazenamento de objetos | Restauração é copiar de volta |

## Fluxo e dados

Tabelas: `execucoes`, `temas`, `candidatos`, `posts_origem`, `itens_oficiais`,
`afirmacoes`, `fontes`, `noticias`, `audios`, `custos`, `descartes`. Cada notícia aponta
para o candidato, cada afirmação para suas fontes (URL, trecho, data de acesso, status),
e cada etapa grava tokens e valor em `custos` antes de chamar a seguinte.

Modelos por papel (a confirmar com os testes):

- Coleta: `grok-4.7` com `x_search`, `reasoning_effort` baixo, `max_turns` limitado.
- Verificação e redação: `gpt-6.1-sol` com `web_search` (fontes completas via
  `web_search_call.action.sources`); `gpt-6-astra` reservado para casos difíceis.
- Auditoria: `claude-opus-5-5` com `web_fetch` (abre cada URL citada) e `web_search`
  limitado a duas buscas; `claude-sonnet-5-5` como alternativa mais barata.
- Voz: a definir no teste 3 (candidatos: ElevenLabs, xAI TTS, Google Chirp 3 HD).

Teto de gasto: contador diário e mensal em `custos`, verificado antes de cada chamada;
ao atingir o limite, a execução para e o painel mostra o aviso.

Segurança do conteúdo externo: todo texto de post ou página entra no prompt dentro de
um bloco marcado como dado, e cada prompt instrui o modelo a ignorar comandos ali contidos.
