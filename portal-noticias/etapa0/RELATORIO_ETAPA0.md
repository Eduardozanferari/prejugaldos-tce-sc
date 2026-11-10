# Relatório da Etapa 0 (atualizado em 10/11/2026, 21h30 UTC)

Situação: documentação oficial consultada, scripts prontos, fontes oficiais validadas e
**testes executados com chamadas reais** para xAI e OpenAI. Faltam: a auditoria com a
API da Anthropic (teste 2, parte B), que depende de a chave ser adicionada ao ambiente, e
a amostra de voz da ElevenLabs (adiada por decisão do autor). As seções 2 e 3 trazem os
números medidos.

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

Arquivos em `saida/` (fora do git): `teste1_coleta_x.json`, `teste2_verificacao.json`,
`teste3_voz.json` e os MP3.

### Teste 1: coleta no X (`grok-4.7`, `reasoning_effort` baixo, `max_turns` 2, janela de 48 h em UTC cobrindo as últimas 24 h)

| Tema | Execução | Posts buscados | Tokens entrada (em cache) | Tokens saída | Custo cobrado |
| --- | --- | --- | --- | --- | --- |
| Direito | 1 | 45 | 82.525 (38.656) | 4.479 | US$ 0,36 |
| Direito | 2 | 35 | 46.103 (17.536) | 4.701 | US$ 0,27 |
| Tecnologia | 1 | 104 | 157.669 (117.376) | 5.574 | US$ 0,69 |
| Tecnologia | 2 | 104 | 155.325 (99.328) | 7.302 | US$ 0,73 |
| Ciência | 1 | 65 | 103.424 (76.544) | 5.888 | US$ 0,45 |
| Ciência | 2 | 81 | 87.277 (50.944) | 4.848 | US$ 0,53 |

Total das seis execuções válidas: US$ 3,03, média de US$ 0,50 por tema por execução.
O custo cobrado vem do campo `usage.cost_in_usd_ticks` da própria xAI e coincidiu com o
cálculo pela tabela de preços em todas as execuções. Os posts buscados respondem por cerca
de 60 a 75 por cento do custo; os tokens, pelo restante.

O que o teste respondeu:

1. **Link de cada post: sim.** Cada item veio com URL no formato `x.com/<autor>/status/<id>`,
   e as anotações `url_citation` da resposta listam todos os posts lidos (85 a 88 por
   execução em tecnologia), mas sem posição no texto. Não há campo `citations` de nível
   superior na resposta em streaming.
2. **Métricas de engajamento: só como texto do modelo.** O modelo preencheu curtidas e
   republicações dizendo que os números constavam nos resultados da ferramenta, mas a API
   não devolve esses números em campo estruturado e nada permite conferi-los sem a API do
   X. Devem ser tratados como estimativa e não exibidos como dado.
3. **Estabilidade entre execuções iguais: baixa.** Índice de Jaccard dos links: Direito 0,0;
   Tecnologia 0,0; Ciência 0,36. Em Direito os assuntos coincidiram em parte (Caso Master e
   STF), mas os posts escolhidos foram outros. Em Tecnologia a primeira execução trouxe
   anúncios de jogos (PlayStation, GTA VI) com milhares de curtidas e a segunda trouxe
   lançamentos de fabricantes com dezenas de curtidas: o modelo interpretou o tema de forma
   diferente a cada vez. Em Ciência, os posts em português das últimas 24 horas tinham
   engajamento muito baixo (0 a 38 curtidas).
4. **Falhas são cobradas.** Quatro tentativas em Tecnologia terminaram com `status: failed`
   e a mensagem "the model is currently at capacity"; três delas cobraram os posts já
   buscados (US$ 0,31, US$ 0,28 e US$ 0,18) sem devolver resposta. O fluxo diário precisa
   limitar novas tentativas e registrar o custo das falhas.
5. **Restrição de rede:** respostas que demoram mais de 30 segundos sem enviar bytes são
   cortadas pelo proxy do ambiente. A solução adotada foi ler a resposta em streaming
   (eventos SSE), e o mesmo vale para OpenAI e Anthropic.

Conclusão do teste 1: o ranking livre não é confiável. A recomendação é a alternativa do
briefing: lista de perfis curados por tema (`allowed_x_handles`, até 20 por chamada) somada
a palavras-chave, com `max_turns` 1 ou 2. Isso também deve reduzir os posts buscados e o
custo, mas ainda não foi medido.

### Teste 2, parte A: verificação com busca na web (OpenAI, `gpt-6.1-sol`, esforço baixo)

Cinco afirmações fixas sobre direito brasileiro (três verdadeiras, uma falsa, uma parcial):

| Afirmação | Esperado | Resultado | Fonte apontada | Ações | Custo |
| --- | --- | --- | --- | --- | --- |
| Lei 14.133/2021 é a Lei de Licitações | confirmada | confirmada | Câmara, texto da lei | 1 busca, 2 páginas abertas | US$ 0,040 |
| Código Civil é a Lei 10.406/2002 | confirmada | confirmada | Câmara, texto da lei | 1 busca, 1 página | US$ 0,030 |
| EC 103/2019 alterou a previdência | confirmada | confirmada | Câmara, texto da emenda | 1 busca, 1 página | US$ 0,024 |
| STF tem quinze ministros | não confirmada | não confirmada (citou o art. 101 da CF: onze) | Câmara, Constituição | 1 busca, 2 páginas | US$ 0,032 |
| LGPD vigente integralmente desde agosto de 2020 | parcial | não confirmada (apontou que as sanções só valem desde 1º/8/2021) | ANPD, perguntas frequentes | 1 busca, 1 página | US$ 0,029 |

Média: US$ 0,031 por afirmação, com cerca de 13 mil tokens de entrada e 200 a 260 de saída.
A lista `web_search_call.action.sources` trouxe de 15 a 24 URLs consultadas por afirmação,
e a ação `open_page` confirma que o modelo abriu as páginas, não só leu trechos de busca.
As fontes escolhidas foram primárias (textos oficiais na Câmara e página da ANPD). O único
desvio foi classificar a afirmação parcial como "não confirmada" em vez de "parcial"; a
justificativa estava correta, então é ajuste de prompt, não de capacidade.

### Teste 2, parte B: auditoria (Anthropic)

Não executada: não há chave da Anthropic no ambiente. O script está pronto
(`claude-opus-5-5` com `web_fetch` abrindo a URL apontada pelo verificador).

### Teste 3: síntese de voz (mesmo roteiro de 931 caracteres, 154 palavras)

| Serviço | Duração | Custo da amostra | Custo por minuto | Observação |
| --- | --- | --- | --- | --- |
| xAI TTS, voz `eve`, `pt-BR` | 60,2 s | US$ 0,014 | US$ 0,014 | Preço de tabela (US$ 15 por milhão de caracteres) |
| OpenAI `gpt-4o-mini-tts`, voz `coral` | 64,4 s | não listado | não listado | Modelo depreciado, desliga em 06/01/2027 |
| ElevenLabs | adiado | | US$ 0,04 a 0,08 por minuto pela tabela | A pedido do autor |

Os dois MP3 foram entregues para avaliação de qualidade pelo autor.

## 3. Estimativa de custo mensal (seis temas, execução diária)

Agora com as medições dos testes 1, 2A e 3 onde existem; o restante segue por tabela.
Hipóteses: 6 temas; uma coleta por tema por dia; 4 candidatos por tema; 8 afirmações por
candidato; 3 notícias publicadas por tema; roteiros de áudio de 2,2 mil caracteres por
notícia mais resumo diário de 12 mil caracteres (1,5 milhão de caracteres por mês).

| Etapa | Cenário econômico | Cenário amplo | Base |
| --- | --- | --- | --- |
| Coleta no X (`grok-4.7`) | US$ 45 (perfis curados, `max_turns` 1; estimado) | US$ 90 (ranking livre, `max_turns` 2; **medido**: US$ 0,50 por tema) | Teste 1 |
| Coleta oficial (sem modelo) | US$ 0 | US$ 0 | Leitura direta |
| Agrupamento e extração (`gpt-6-luna` / `gpt-6.1-terra`) | US$ 3 | US$ 10 | Tabela |
| Verificação (`gpt-6.1-sol`) | US$ 70 (uma chamada por candidato, 24 por dia) | US$ 135 (uma chamada por afirmação, 144 por dia; **medido**: US$ 0,031) | Teste 2A |
| Redação (`gpt-6.1-sol`) | US$ 15 | US$ 25 | Tabela |
| Auditoria (`claude-sonnet-5-5` / `claude-opus-5-5`) | US$ 35 | US$ 75 | Tabela; a medir no teste 2B |
| Áudio | US$ 23 (xAI TTS; **medido**: US$ 0,014 por minuto) | US$ 60 a 125 (ElevenLabs) | Teste 3 e tabela |
| Hospedagem | US$ 5 | US$ 10 | Servidor pequeno |
| **Total aproximado** | **US$ 195** | **US$ 405 a 470** | |

Coleta e verificação somam dois terços do custo. As alavancas continuam as mesmas:
perfis curados e `max_turns` baixo na coleta; verificação por candidato com buscas
limitadas e `allowed_domains`; teto de gasto diário desde a Etapa 1.

## 4. Riscos identificados

1. **Ranking por repercussão não é garantido pela API da xAI**, e o teste 1 mediu
   estabilidade baixa (Jaccard 0,0 a 0,36). Mitigação: perfis curados por tema.
2. **Métricas de engajamento não vêm estruturadas.** Mitigação: tratá-las como estimativa e
   não exibi-las como dado no portal, ou obtê-las por outra via (API do X, custo próprio).
3. **Fontes oficiais com proteção anti-robô (STF, TSE, TST) e falhas de rede (DOU, Planalto).**
   Mitigação: navegador sem interface, RSS onde houver, reteste do servidor definitivo.
4. **Custo de coleta e verificação pode ultrapassar o esperado**, e chamadas que falham
   na xAI ainda são cobradas. Mitigação: teto de gasto diário e mensal desde a Etapa 1,
   registro por etapa e por tema, e limite de novas tentativas.
5. **Depreciações frequentes** (OpenAI desliga `gpt-4o-mini-tts` em janeiro de 2027; xAI
   retirou modelos em maio de 2026). Mitigação: nomes de modelo e de ferramenta em configuração,
   nunca no código.
6. **Injeção de instruções por conteúdo externo.** Mitigação já prevista nos prompts de teste:
   conteúdo de posts e páginas é marcado como dado e os prompts mandam ignorar comandos.

## 5. Próximos passos

1. Adicionar a chave da Anthropic ao ambiente e rodar a parte B do teste 2.
2. Medir a coleta com perfis curados (`allowed_x_handles`) em um tema, para fechar a
   decisão "perfis curados ou ranking livre" com número de posts e custo.
3. Decidir o serviço de voz após ouvir as amostras (ElevenLabs adiada).
4. Definir o teto de gasto mensal a partir da seção 3.
5. Aprovação da arquitetura (`ARQUITETURA.md`) antes da Etapa 1.
