# Relatório da Etapa 0 (encerrado em 11/11/2026)

Situação: **Etapa 0 encerrada.** Todos os testes foram executados com chamadas reais para
xAI, OpenAI e Anthropic, inclusive os complementares (1B, perfis curados; 2C, confirmação em
afirmações difíceis). O único teste não feito é a voz da ElevenLabs: a chave salva no
ambiente é rejeitada pelo serviço ("Invalid API key"). As decisões estão na seção 5 e a
primeira edição da versão beta, na seção 6.

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

Uma segunda execução da parte A (feita junto com a parte B) repetiu os cinco status e as
mesmas fontes, com média de US$ 0,029 por afirmação.

### Teste 2, parte B: auditoria (Anthropic, `claude-opus-5-5`, esforço médio)

O auditor recebeu cada afirmação com a URL e o status dados pela parte A, abriu a URL com
`web_fetch` (limite de 40 mil tokens de conteúdo por página) e podia fazer até duas buscas.

| Afirmação | Verificador (OpenAI) | Auditor (Claude) | Fetches / buscas | Tokens entrada / saída | Custo |
| --- | --- | --- | --- | --- | --- |
| Lei 14.133/2021 | confirmada | aprovar / confirmada | 1 / 0 | 26.659 / 683 | US$ 0,120 |
| Código Civil, Lei 10.406/2002 | confirmada | aprovar / confirmada | 1 / 0 | 31.610 / 739 | US$ 0,141 |
| EC 103/2019 | confirmada | aprovar / confirmada | 1 / 0 | 25.665 / 653 | US$ 0,116 |
| STF com quinze ministros | nao_confirmada | rejeitar / contestada | 1 / 1 | 57.647 / 1.164 | US$ 0,264 |
| LGPD integral em agosto de 2020 | nao_confirmada | rejeitar / contestada | 1 / 0 | 24.046 / 1.008 | US$ 0,116 |

Média: **US$ 0,152 por afirmação**, cerca de cinco vezes o custo da verificação. A API da
Anthropic não devolve o valor cobrado; o custo foi calculado pela tabela de preços a partir
dos tokens e buscas informados em `usage`. Quase todo o custo vem dos tokens de entrada,
isto é, do texto da página aberta.

O que o teste respondeu:

1. **Concordância nas decisões: cinco de cinco.** O auditor aprovou as três afirmações
   verdadeiras e rejeitou as duas falsas, sempre citando trecho literal da fonte oficial.
2. **O auditor conferiu de fato a página.** Em cada caso registrou a URL aberta e o trecho
   encontrado. No caso do STF, informou que a página indicada pelo verificador (a
   Constituição no site da Câmara) chegou incompleta, terminando por volta do art. 39, e
   buscou o art. 101 no portal do STF ("compõe-se de onze Ministros"). A causa provável do
   corte é o próprio limite de 40 mil tokens do script, já que a Constituição inteira é bem
   maior; não é defeito da página. Lição para a Etapa 1: a URL do verificador deve apontar
   para o dispositivo específico (o artigo), não para a norma inteira.
3. **A afirmação sobre a LGPD foi mal classificada no gabarito.** O teste a esperava como
   "parcial", mas os dois pontos estão errados: a maior parte da lei vigorou em 18/9/2020
   (não em agosto) e as sanções só em 1º/8/2021, segundo a ANPD. A rejeição do auditor
   está correta, e o "nao_confirmada" do verificador também é defensável.
4. **Os status precisam de ajuste.** O auditor usou "contestada" para "a fonte oficial
   desmente a afirmação", enquanto o prompt define "contestada" como "fontes confiáveis se
   contradizem". A lista de status da Etapa 1 deve incluir um valor próprio para afirmação
   desmentida (por exemplo, "falsa"), separado de "nao_confirmada" (nada encontrado) e de
   "contestada" (fontes divergentes).
5. **Saída em JSON: ok.** As cinco respostas vieram com o objeto pedido, sem falha de
   leitura. Na Etapa 1 a saída estruturada nativa substitui a extração por texto.

### Teste 2, parte B: comparação de modelos do auditor

Mesmas cinco afirmações, mesmas URLs e status do verificador (reaproveitados da parte A,
sem nova cobrança da OpenAI), mesmo prompt e mesmas ferramentas. Comando:
`python3 teste2_verificacao.py --comparar-auditores claude-sonnet-5-5 claude-haiku-5-5`.
Saída em `saida/teste2b_comparacao_auditores.json`.

| Modelo | Decisões iguais às do Opus | Custo médio por afirmação | Faixa | Tokens de entrada (média) |
| --- | --- | --- | --- | --- |
| `claude-opus-5-5` | (referência) | US$ 0,152 | US$ 0,116 a 0,264 | 33.125 |
| `claude-sonnet-5-5` | 5 de 5 | US$ 0,068 | US$ 0,039 a 0,146 | 29.492 |
| `claude-haiku-5-5` | 5 de 5 | US$ 0,010 | US$ 0,003 a 0,034 | 52.949 |

O Sonnet custou 45 por cento do Opus e o Haiku, 7 por cento. O Haiku não chega ao
um quarenta avos da tabela porque usou mais tokens: abriu as páginas duas ou três vezes
e, no caso do STF, fez duas buscas e leu 122 mil tokens.

Qualidade, além da decisão:

- **Sonnet:** trechos literais em todos os casos e declaração explícita do que não leu
  ("Só li o título e a descrição, não o texto integral da lei"). No caso do STF,
  consultou também o Planalto e registrou que a redação atual do art. 101 é a da
  EC 122/2022, o que confere com o trecho citado ("menos de setenta anos").
- **Haiku:** no caso do STF, o trecho é paráfrase com citação parcial, não a frase
  literal, e a busca passou por fontes de pouca autoridade (Goodreads, questões de
  concurso) antes de chegar ao portal do STF. No caso da Lei 14.133, afirma que "o texto
  do art. 1º confirma" a afirmação; isso não pôde ser conferido porque o script não grava
  o texto da página aberta.
- **Os três modelos usaram "contestada"** para afirmação desmentida, o que confirma que o
  problema está na lista de status do prompt, não no modelo.

Limite do teste: cinco afirmações fáceis, todas com fonte oficial clara, não separam bem
os modelos. A escolha final pede um conjunto mais difícil: números e datas próximos do
correto, afirmações de fato parciais, páginas longas e fontes não oficiais.

Recomendação provisória: `claude-sonnet-5-5` como auditor padrão. O Haiku é candidato a
uma triagem barata ou a afirmações simples, se passar no conjunto difícil; o Opus fica
para casos em que verificador e auditor discordem.

### Teste 3: síntese de voz (mesmo roteiro de 931 caracteres, 154 palavras)

| Serviço | Duração | Custo da amostra | Custo por minuto | Observação |
| --- | --- | --- | --- | --- |
| xAI TTS, voz `eve`, `pt-BR` | 60,2 s | US$ 0,014 | US$ 0,014 | Preço de tabela (US$ 15 por milhão de caracteres) |
| OpenAI `gpt-4o-mini-tts`, voz `coral` | 64,4 s | não listado | não listado | Modelo depreciado, desliga em 06/01/2027 |
| ElevenLabs | adiado | | US$ 0,04 a 0,08 por minuto pela tabela | A pedido do autor |

Os dois MP3 foram entregues para avaliação de qualidade pelo autor.

Repetição em 11/11/2026, com a ElevenLabs incluída: a chave salva no ambiente foi rejeitada
pelo serviço (HTTP 401, "Invalid API key", tanto em `/v1/voices` quanto em
`/v1/user/subscription`), como já acontecera em 10/11. A xAI repetiu o resultado (59,3 s,
US$ 0,014). O teste da ElevenLabs depende de uma chave válida.

### Teste 1B: coleta no X com perfis curados (`allowed_x_handles`)

Mesmo modelo, prompt e janela do teste 1, com a busca restrita a perfis curados: em Direito,
nove contas institucionais e veículos jurídicos (STF, STJ, TSE, CNJ, Câmara, Senado, OAB, JOTA,
Migalhas); em Tecnologia, catorze fabricantes e veículos especializados.

| Tema | Execução | Posts buscados | Custo cobrado | Perfis que trouxeram posts |
| --- | --- | --- | --- | --- |
| Direito | 1 | 36 | US$ 0,26 | SenadoFederal (6), STF_oficial (2) |
| Direito | 2 | 40 | US$ 0,31 | SenadoFederal (4), STF_oficial (2), STJnoticias (2) |
| Tecnologia | 1 | 127 | US$ 1,10 | Tecnoblog (5), canaltech (3) |
| Tecnologia | 2 | 33 | US$ 0,23 | Tecnoblog (6), canaltech (2) |

| Medida | Ranking livre (teste 1) | Perfis curados (1B) |
| --- | --- | --- |
| Jaccard entre execuções, Direito | 0,0 | **0,6** |
| Jaccard entre execuções, Tecnologia | 0,0 | **0,33** |
| Custo médio por tema, Direito | US$ 0,32 | US$ 0,28 |
| Custo médio por tema, Tecnologia | US$ 0,71 | US$ 0,67 (de 0,23 a 1,10) |

Conclusões:

1. **A estabilidade melhorou muito**, e as pautas passaram a ser fatos (decisões do STF e do
   STJ, leis sancionadas, lançamentos), em vez de anúncios de jogos e posts de baixo alcance.
2. **O custo quase não caiu** e continua instável em Tecnologia (uma execução buscou 127 posts).
   O controle de custo fica com o teto diário e o `max_turns`.
3. **Só parte dos perfis rende posts.** Com o prompt em português, as contas em inglês dos
   fabricantes não aparecem; os veículos brasileiros, sim. Na beta, os perfis viraram um campo
   editável por tema no painel, e a coleta oficial por RSS cobre os comunicados dos fabricantes.

Decisão: **perfis curados por tema**, como previa a alternativa do briefing.

### Teste 2C: verificação e confirmação em afirmações difíceis

Papéis conforme decisão do autor (11/11/2026): a OpenAI verifica e revisa; o Claude apenas
confirma o resultado da OpenAI. Uma afirmação só é publicada se a OpenAI a der como confirmada
e o Claude concordar. Quinze afirmações com gabarito conferido em fonte primária: dez
verdadeiras, três falsas (Marco Civil "de 2015"; idade máxima de 65 anos para o STF, que é 70
desde a EC 122/2022; o mito dos 10% do cérebro) e duas parciais (CPC "em vigor em março de
2015", que vigorou em 2016; Lei 8.666 revogada "integralmente apenas em 2023", quando os crimes
foram revogados em 2021). Novidades em relação ao teste 2: status "falsa" separado de
"nao_confirmada" e "contestada"; texto das páginas abertas pelo Claude gravado; limite de
25 mil tokens por página. Script: `teste2c_confirmacao.py`.

| Medida | OpenAI (`gpt-6.1-sol`) | Claude Sonnet 5.5 | Claude Haiku 5.5 |
| --- | --- | --- | --- |
| Status igual ao gabarito | 14 de 15 | | |
| Afirmações publicadas (verificador e confirmador de acordo) | | 10 | 6 |
| Publicadas que não eram verdadeiras | | **0** | **0** |
| Verdadeiras bloqueadas | | **0** | 4 |
| Custo médio por afirmação | US$ 0,031 | US$ 0,063 | US$ 0,006 |

O que o teste mostrou:

1. **O único erro da OpenAI foi pego pelos dois confirmadores.** Ela deu como confirmada a
   revogação "integral apenas em 2023" da Lei 8.666; os dois apontaram, na própria página, que
   os arts. 89 a 108 foram revogados em 2021.
2. **O Haiku bloqueou verdadeiras quando a fonte não abria.** Nos quatro casos, a página
   apontada pela OpenAI não abriu para o Claude (Planalto com "Acesso Negado"; artigos da Wiley
   e da PNAS inacessíveis) e o Haiku não conseguiu buscar outra cópia. O Sonnet, nas mesmas
   situações, achou cópias oficiais da mesma fonte e confirmou corretamente.
3. **Os trechos são verificáveis.** Nas páginas que abriram, o trecho citado pelo confirmador
   foi encontrado no texto gravado em todos os casos conferidos automaticamente.
4. **"Falsa" e "parcial" ainda se confundem** quando a afirmação tem uma parte certa e outra
   errada (Marco Civil "de 2015": o número está certo e o ano, errado). Como nenhuma das duas
   classificações leva à publicação, a diferença não afeta o portal.

Decisão: **`claude-sonnet-5-5` como confirmador**, só nas afirmações que a OpenAI deu como
confirmadas. O Haiku fica descartado por bloquear verdadeiras; o Opus não é necessário, já que
o Sonnet não errou e custa menos da metade.

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
| Auditoria (`claude-sonnet-5-5` / `claude-opus-5-5`) | US$ 110 (Sonnet, 3 afirmações centrais por notícia, 54 por dia; **medido**: US$ 0,068) | US$ 655 (Opus, todas as afirmações, 144 por dia; **medido**: US$ 0,152) | Teste 2B |
| Áudio | US$ 23 (xAI TTS; **medido**: US$ 0,014 por minuto) | US$ 60 a 125 (ElevenLabs) | Teste 3 e tabela |
| Hospedagem | US$ 5 | US$ 10 | Servidor pequeno |
| **Total aproximado** | **US$ 270** | **US$ 985 a 1.050** | |

Com a medição do teste 2B, **a auditoria passa a ser a etapa mais cara** no cenário amplo,
seguida da verificação e da coleta. Outras combinações medidas para a auditoria, por mês:
Sonnet em todas as afirmações, US$ 295; Haiku nas afirmações centrais, US$ 16; Haiku em
todas, US$ 45. A estimativa anterior (US$ 35 a 75 para auditoria)
estava baixa porque não previa o tamanho das páginas abertas. Alavancas da auditoria:
auditar só as afirmações centrais de cada notícia; usar `claude-sonnet-5-5` (metade do
preço por token do Opus) ou `claude-haiku-5-5` (um quarenta avos), o que ainda precisa ser
testado quanto à qualidade; reduzir `max_content_tokens` e apontar para o dispositivo
específico da norma, para que cada página aberta seja menor. As demais alavancas
continuam: perfis curados e `max_turns` baixo na coleta; verificação por candidato com
buscas limitadas e `allowed_domains`; teto de gasto diário desde a Etapa 1.

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
6. **Custo da auditoria proporcional ao tamanho das páginas** (teste 2B: 24 mil a 58 mil
   tokens de entrada por afirmação). Mitigação: limite de conteúdo por página, URLs que
   apontem para o trecho específico, auditoria só das afirmações centrais e modelo mais
   barato se a qualidade se mantiver.
7. **Páginas cortadas pelo limite de conteúdo podem esconder o trecho que sustenta a
   afirmação.** Mitigação: o auditor já busca outra fonte nesse caso (teste 2B, item 4);
   na Etapa 1, registrar quando a página veio truncada.
8. **Injeção de instruções por conteúdo externo.** Mitigação já prevista nos prompts de teste:
   conteúdo de posts e páginas é marcado como dado e os prompts mandam ignorar comandos.

## 5. Decisões que encerram a Etapa 0

| Questão | Decisão | Base |
| --- | --- | --- |
| Coleta no X | `grok-4.7` com `x_search`, perfis curados por tema, `max_turns` 2, uma nova tentativa | Testes 1 e 1B |
| Métricas de engajamento | Não são exibidas: a API não as devolve em campo estruturado | Teste 1 |
| Coleta oficial | Feeds RSS que respondem (Câmara, Senado, Agência Brasil, fabricantes, Nature, NASA, Jornal da USP) | Validação de 11/11 |
| Verificação | `gpt-6.1-sol` com `web_search`, uma chamada por afirmação central, até 4 por pauta | Testes 2A e 2C |
| Confirmação | `claude-sonnet-5-5` com `web_fetch` e no máximo uma busca, só nas afirmações confirmadas pela OpenAI | Testes 2B e 2C |
| Regra de publicação | Pauta publicada só com pelo menos 2 afirmações aprovadas pelos dois; as demais são cortadas | Decisão do autor e teste 2C |
| Voz | xAI TTS, voz `eve`, `pt-BR` (US$ 0,014 por minuto); ElevenLabs quando houver chave válida | Teste 3 |
| Teto de gasto | US$ 10 por dia e US$ 200 por mês, editáveis no painel | Seção 3 e seção 6 |
| Arquitetura | A de `ARQUITETURA.md`, implementada na beta (`../briefing/`) | |


## 6. Primeira edição da versão beta (11/11/2026)

A versão beta (`../briefing/`, instruções em `../README.md`) rodou a edição completa dos seis
temas com chamadas reais. Por causa de uma alteração de prompt feita durante a execução, a edição
saiu em duas execuções (Direito e Tribunais na primeira; Política, Tecnologia, Cultura e Ciência na
segunda); os números abaixo somam as duas.

| Medida | Resultado |
| --- | --- |
| Pautas avaliadas | 18 (3 por tema) |
| Notícias publicadas | 14 |
| Pautas descartadas | 4, todas por terem menos de 2 afirmações aprovadas pelos dois verificadores |
| Afirmações verificadas pela OpenAI | 49: 45 confirmadas, 3 parciais, 1 contestada |
| Confirmações do Claude (Sonnet) | 45: concordou em 40, discordou em 5 |
| Chamadas com falha | 0 |
| Áudios | 14 notícias e 1 resumo do dia (8.727 caracteres) |
| **Custo da edição** | **US$ 6,65** |

| Etapa | Chamadas | Custo | Parcela |
| --- | --- | --- | --- |
| Confirmação (`claude-sonnet-5-5`) | 45 | US$ 2,56 | 38% |
| Verificação (`gpt-6.1-sol`) | 49 | US$ 2,20 | 33% |
| Coleta no X (`grok-4.7`) | 7 | US$ 1,67 | 25% |
| Voz (xAI) | 15 | US$ 0,13 | 2% |
| Redação e seleção (OpenAI) | 20 | US$ 0,09 | 1% |

Por tema, a edição custou de US$ 0,79 (Cultura) a US$ 1,45 (Política).

As cinco discordâncias do Claude foram pertinentes: em quatro, ele apontou na própria página que a
afirmação exagerava ou simplificava o fato (por exemplo, "a MP segue para o Senado", quando a página
mostra a matéria enviada à Câmara; "multa motivada por informações incompletas", quando esse foi só um
dos motivos). Na quinta, a chamada terminou sem resposta (`stop_reason=tool_use`) e a afirmação foi
cortada, o lado seguro; a beta agora repete a chamada uma vez nesse caso.

Custo mensal projetado, com uma edição por dia: **cerca de US$ 200**, que é exatamente o teto
mensal padrão. Com esse teto, as últimas edições do mês podem ser interrompidas. O teto deve ser
ajustado no painel (por exemplo, US$ 230) ou o custo reduzido: as alavancas são menos pautas por tema,
menos temas, e confirmar só as afirmações centrais.
