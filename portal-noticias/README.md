# Briefing de Notícias (versão beta)

Portal pessoal de notícias verificadas. Todo dia, no horário escolhido no painel, o sistema:

1. coleta posts do X em perfis curados por tema (xAI, `grok-4.7` com `x_search`) e itens das fontes
   oficiais por RSS (Câmara, Senado, Agência Brasil, fabricantes, Nature, NASA, Jornal da USP);
2. escolhe as pautas e extrai as afirmações centrais de cada uma (OpenAI);
3. verifica cada afirmação na web, de preferência em fonte primária (OpenAI, `gpt-6.1-sol`);
4. pede ao Claude (`claude-sonnet-5-5`) que confirme cada afirmação dada como confirmada, abrindo a fonte;
5. publica a pauta só com as afirmações aprovadas pelos dois, e só se houver pelo menos duas;
   o que não passa é cortado ou descartado, com o motivo registrado;
6. redige a notícia só com essas afirmações, com as fontes numeradas, e gera o áudio (voz da xAI);
7. gera o áudio do resumo do dia, que toca em sequência com as notícias, inclusive com a tela bloqueada.

O teto de gasto diário e mensal é conferido antes de cada chamada paga. Ao atingi-lo, a execução para
e o painel mostra o aviso. Os resultados dos testes que embasaram cada escolha estão em
`etapa0/RELATORIO_ETAPA0.md`.

## Estrutura

| Caminho | Conteúdo |
| --- | --- |
| `briefing/config.py` | Valores padrão: modelos, tetos, horário, temas, perfis e feeds (todos editáveis no painel) |
| `briefing/prompts/*.md` | Prompts de cada etapa, versionados no git; dá para ajustar sem mexer no código |
| `briefing/pipeline.py` | O fluxo diário descrito acima |
| `briefing/coleta.py`, `briefing/ia.py` | Chamadas ao X, aos RSS e aos modelos |
| `briefing/custos.py` | Registro de custos e teto de gasto |
| `briefing/db.py` | Banco SQLite (um arquivo) |
| `briefing/web.py`, `templates/`, `static/` | Portal, painel, login e PWA |
| `etapa0/` | Testes de viabilidade e relatório da Etapa 0 |

## Instalação num servidor (Docker)

Requisitos: um servidor pequeno (1 vCPU, 2 GB) com Docker e Docker Compose.

```bash
git clone <este repositório> && cd <repositório>/portal-noticias
```

```bash
cp .env.example .env
```

Edite `.env` com as três chaves de API e um segredo de sessão (o próprio arquivo explica como gerar).

```bash
docker compose up -d --build
```

```bash
docker compose exec briefing python -m briefing senha seu_usuario
```

O último comando pede a senha do portal (mínimo de 10 caracteres). O portal fica em
`http://127.0.0.1:8000` no próprio servidor. Para acessar pelo celular, coloque um proxy com HTTPS
na frente (por exemplo, Caddy com um domínio próprio) e mantenha `PORTAL_HTTPS=1` no `.env`.
Depois, no celular, abra o endereço e use "Adicionar à tela de início" para instalar o portal.

Cópia de segurança: a pasta `dados/` contém o banco e os áudios; copiá-la basta.

## Uso local, sem Docker

```bash
pip install -r requirements.txt
```

```bash
python -m briefing senha seu_usuario
```

```bash
python -m briefing servidor
```

Para rodar uma edição sem abrir o portal (por exemplo, só dois temas):

```bash
python -m briefing executar direito tecnologia
```

## No painel

- tetos de gasto diário e mensal, horário da execução automática e liga/desliga da agenda;
- botão para executar agora, com todos os temas ou só os marcados;
- gasto do dia, do mês e por etapa; histórico das execuções;
- relatório de cada execução: registro, custos por tema e etapa, pautas publicadas e descartadas,
  e a decisão de cada verificador sobre cada afirmação;
- temas: nome, descrição, quantidade de pautas e de notícias, perfis do X e feeds RSS;
- modelos por etapa, para trocar quando um provedor desligar um modelo.

## Chaves de API

As chaves ficam só no `.env` (ou nas variáveis de ambiente) e nunca no código nem no git. Variáveis
lidas: `XAI_API_KEY`, `OPENAI_API_KEY` e `ANTHROPIC_API_KEY` (ou `PORTAL_ANTHROPIC_KEY`).

No ambiente em nuvem do Claude Code, o proxy injeta as chaves da xAI e da OpenAI; o código já usa
um valor fictício quando a variável não existe, e o proxy o substitui na requisição.

## Custo

A primeira edição completa (seis temas, 14 notícias) custou US$ 6,65, o que projeta cerca de
US$ 200 por mês. O teto mensal padrão é US$ 200; ajuste-o no painel. Detalhes na seção 6 de
`etapa0/RELATORIO_ETAPA0.md`.

## Limitações conhecidas da beta

- Fatos das últimas horas às vezes ainda não têm fonte indexada; nesse caso a afirmação fica
  "não confirmada" e a pauta é descartada. É o comportamento esperado, não uma falha.
- Portais com proteção anti-robô (STF, TSE, TST, Planalto) não são lidos diretamente; a coleta oficial
  usa os feeds RSS que respondem, e a verificação busca cópias oficiais da mesma fonte.
- A voz da ElevenLabs não foi testada: a chave salva no ambiente é rejeitada pelo serviço.
- Usuário único, sem notificações.
