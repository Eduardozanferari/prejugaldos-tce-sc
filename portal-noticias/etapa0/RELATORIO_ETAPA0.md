# Relatório da Etapa 0 (versão preliminar, 10/11/2026)

Situação: a documentação oficial das quatro APIs foi consultada, os três scripts de teste
estão prontos e as fontes oficiais foram validadas. **As execuções com chamadas reais ainda
não aconteceram**, porque as chaves salvas no ambiente para xAI, OpenAI e ElevenLabs foram
rejeitadas pelos três serviços ("chave incorreta"), e não há chave da Anthropic no ambiente.
As seções 2 a 4 serão completadas com os números medidos assim que as chaves forem corrigidas.

## 1. O que a documentação já responde

### Teste 1: coleta no X (xAI, ferramenta `x_search`)

Fonte: https://docs.x.ai/developers/tools/x-search e https://docs.x.ai/developers/pricing

- A ferramenta roda na Responses API (`POST https://api.x.ai/v1/responses`, modelo
  `grok-4.7`). Parâmetros: `from_date` e `to_date` (formato `AAAA-MM-DD`, janela de 00:00 UTC
  de `from_date` até, sem incluir, `to_date`), `allowed_x_handles` ou `excluded_x_handles`
  (até 20 perfis, não combináveis), `enable_image_understanding`, `enable_video_understanding`.
- **Não existe parâmetro de ordenação por curtidas.** Internamente o modelo escolhe entre
  `x_keyword_search` (ordenação "Top" ou "Latest", decidida pelo modelo), `x_semantic_search`,
  `x_user_search` e `x_thread_fetch`. O ranking de "maior repercussão" depende, portanto, do
  julgamento do modelo sobre o que ele buscou, não de uma ordenação garantida pela API.
- **A resposta documentada traz links, não métricas.** O campo `citations` lista as URLs dos
  posts (`https://x.com/i/status/...`) encontrados; não há campo de curtidas ou republicações.
  O teste pede ao modelo que informe números só quando visíveis e verifica a consistência entre
  duas execuções. Qualquer número de engajamento deve ser tratado como estimativa do modelo.
- Custo: US$ 5 por mil posts buscados e US$ 10 por mil perfis, somados aos tokens
  (`grok-4.7`: US$ 2 por milhão de entrada, US$ 6 por milhão de saída). A contagem vem em
  `usage.server_side_tool_usage_details.x_posts_fetched`. Posts repetidos entre buscas contam
  duas vezes. O parâmetro `max_turns` limita as rodadas de busca e é a principal alavanca de custo.
- Conclusão parcial: a alternativa prevista no briefing, lista de perfis curados por tema via
  `allowed_x_handles`, é suportada diretamente e reduz custo. A decisão final depende da
  estabilidade medida no teste.

### Teste 2: verificação com busca na web

OpenAI (fonte: https://developers.openai.com/api/docs/guides/tools-web-search e
https://developers.openai.com/api/docs/pricing):

- Ferramenta `web_search` na Responses API. A resposta traz `web_search_call` com as ações
  (`search`, `open_page`, `find_in_page`, as duas últimas só em modelos com raciocínio) e
  anotações `url_citation` com URL, título e posição no texto. Com
  `include=["web_search_call.action.sources"]` vem a **lista completa das URLs consultadas**,
  que é o que o briefing exige. `filters.allowed_domains` aceita até 100 domínios.
- Modelos atuais: `gpt-6-astra` (US$ 10 / US$ 50 por milhão), `gpt-6.1-sol` (US$ 2 / US$ 10),
  `gpt-6.1-terra` (US$ 1 / US$ 5), `gpt-6-luna` (US$ 0,10 / US$ 0,50). Modo lote custa metade.
- Busca: US$ 10 por mil chamadas, mais os tokens de conteúdo de busca ao preço do modelo.

Anthropic (fonte: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool
e .../web-fetch-tool e https://platform.claude.com/docs/en/about-claude/pricing):

- `web_search_20260318` (US$ 10 por mil buscas) devolve resultados com URL, título e
  citações obrigatórias; `web_fetch_20260318` **abre a página inteira, sem custo além dos
  tokens**, e só aceita URLs já presentes na conversa, o que casa com o papel de auditor:
  ele recebe as URLs do verificador e as abre. Páginas montadas por JavaScript não são lidas.
- Modelos: `claude-opus-5-5` (US$ 4 / US$ 20 por milhão), `claude-sonnet-5-5`
  (US$ 2 / US$ 10), `claude-haiku-5-5` (US$ 0,10 / US$ 0,50).

### Teste 3: síntese de voz em português do Brasil

| Serviço | Suporte a pt-BR | Preço por milhão de caracteres | Observação |
| --- | --- | --- | --- |
| ElevenLabs `eleven_v4` / `eleven_multilingual_v2` | Sim (Multilingual v2 lista "Portuguese (Brazil)") | US$ 80 (US$ 0,08 por mil) | Planos: Starter US$ 6/mês, Creator US$ 22/mês com 275 mil caracteres incluídos, Pro US$ 99/mês |
| ElevenLabs `eleven_flash_v2_5` / `eleven_v4_turbo` | Sim | US$ 40 | Menor latência, qualidade um pouco menor |
| xAI TTS (`POST /v1/tts`) | Sim, código `pt-BR` explícito | US$ 15 | Até 60 mil caracteres por chamada; voz e idioma independentes |
| Google Cloud Chirp 3 HD | A confirmar na lista de vozes | US$ 30, 1 milhão grátis por mês | Exige projeto Google Cloud |
| Google Cloud Neural2 / WaveNet | pt-BR disponível | US$ 16 / US$ 4, com franquia mensal | Qualidade inferior ao Chirp 3 |
| OpenAI `gpt-4o-mini-tts` | Sim | Não listado mais | **Depreciado, desliga em 06/01/2027**; substituto é `gpt-realtime-2.1-mini` (cobrado por token de áudio). Não recomendado para construir agora |
| Azure AI Speech | pt-BR disponível | Página exige JavaScript; não extraído | 0,5 milhão de caracteres grátis por mês no nível gratuito |

### Fontes oficiais

Ver `fontes_oficiais.md`. Resumo: Câmara e Senado respondem normalmente; STF (noticias.stf.jus.br)
exige navegador; TSE, TST e portal.stf.jus.br bloqueiam robôs; DOU e Planalto não responderam
deste ambiente e precisam ser retestados do servidor definitivo.

## 2. Resultados medidos

Pendentes da correção das chaves. Os scripts gravam em `saida/`:

- `teste1_coleta_x.json`: posts por tema, links, métricas informadas, índice de Jaccard entre
  as duas execuções, tokens, posts buscados e custo por execução.
- `teste2_verificacao.json`: para cada afirmação, status, URL e trecho do verificador (OpenAI),
  URLs consultadas, decisão do auditor (Claude), URLs abertas e custo por afirmação.
- `teste3_voz.json` e os MP3: duração, caracteres e custo por minuto de cada serviço.

## 3. Estimativa de custo mensal (seis temas, execução diária)

Estimativa feita só com os preços de tabela e com hipóteses de volume; será refeita com os
tokens medidos. Hipóteses: 6 temas; coleta com até 3 rodadas por tema; 4 candidatos por tema;
8 afirmações por candidato verificadas em uma chamada por candidato; 3 notícias publicadas
por tema; roteiros de áudio de 2,2 mil caracteres por notícia mais resumo diário de 12 mil.

| Etapa | Cenário econômico | Cenário amplo | Base |
| --- | --- | --- | --- |
| Coleta no X (`grok-4.7`) | US$ 27 (20 posts por tema, perfis curados) | US$ 65 (60 posts por tema) | US$ 5 por mil posts + tokens |
| Coleta oficial (sem modelo) | US$ 0 | US$ 0 | Leitura direta |
| Agrupamento e extração (`gpt-6-luna` ou `gpt-6.1-terra`) | US$ 3 | US$ 10 | Tokens |
| Verificação (`gpt-6.1-terra` / `gpt-6.1-sol`) | US$ 80 | US$ 150 | 24 candidatos por dia, 6 buscas cada |
| Redação (`gpt-6.1-sol`) | US$ 15 | US$ 25 | 18 notícias por dia |
| Auditoria (`claude-sonnet-5-5` / `claude-opus-5-5`) | US$ 35 | US$ 75 | 18 notícias, 6 páginas abertas cada |
| Áudio (xAI TTS / Google) | US$ 25 | US$ 60 (ElevenLabs Flash) a US$ 125 (ElevenLabs v4) | 1,5 milhão de caracteres por mês |
| Hospedagem | US$ 5 | US$ 10 | Servidor pequeno |
| **Total aproximado** | **US$ 190** | **US$ 400 a 460** | |

A verificação é o maior item. As alavancas são: verificar por candidato (não por afirmação
isolada), limitar buscas por candidato, usar `allowed_domains` com os domínios confiáveis do
tema e reduzir o número máximo de candidatos por tema no painel.

## 4. Riscos identificados

1. **Ranking por repercussão não é garantido pela API da xAI.** Mitigação: perfis curados por
   tema e comparação entre execuções; o teste medirá a estabilidade.
2. **Métricas de engajamento não vêm estruturadas.** Mitigação: tratá-las como estimativa e
   não exibi-las como dado no portal, ou obtê-las por outra via (API do X, custo próprio).
3. **Fontes oficiais com proteção anti-robô (STF, TSE, TST) e falhas de rede (DOU, Planalto).**
   Mitigação: navegador sem interface, RSS onde houver, reteste do servidor definitivo.
4. **Custo de verificação pode ultrapassar o esperado.** Mitigação: teto de gasto diário e
   mensal desde a Etapa 1, com registro por etapa e por tema.
5. **Depreciações frequentes** (OpenAI desliga `gpt-4o-mini-tts` em janeiro de 2027; xAI
   retirou modelos em maio de 2026). Mitigação: nomes de modelo e de ferramenta em configuração,
   nunca no código.
6. **Injeção de instruções por conteúdo externo.** Mitigação já prevista nos prompts de teste:
   conteúdo de posts e páginas é marcado como dado e os prompts mandam ignorar comandos.

## 5. Próximos passos

1. Corrigir as chaves de xAI, OpenAI e ElevenLabs no ambiente e adicionar a da Anthropic.
2. Rodar os três testes (`teste1_coleta_x.py`, `teste2_verificacao.py`, `teste3_voz.py`) e
   completar as seções 2 e 3 com números medidos.
3. Decidir, com base nos resultados: perfis curados ou ranking livre; serviço de voz;
   teto de gasto mensal.
4. Aprovação da arquitetura (`ARQUITETURA.md`) antes da Etapa 1.
