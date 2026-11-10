# Portal pessoal de notícias verificadas

Projeto descrito no briefing de 9 de novembro de 2026. Este diretório é independente
do catálogo de prejulgados (`index.html` na raiz do repositório).

Estrutura:

- `etapa0/`: testes de viabilidade, relatório e proposta de arquitetura (Etapa 0).

Chaves de API nunca entram no código nem no repositório. Os scripts leem as variáveis
de ambiente `XAI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` (ou `PORTAL_ANTHROPIC_KEY`)
e `ELEVENLABS_API_KEY`.

Observações para rodar no ambiente em nuvem do Claude Code:

- O proxy do ambiente injeta as chaves da xAI e da OpenAI. Os SDKs exigem que a variável
  exista ao iniciar, então basta um valor fictício (por exemplo, `OPENAI_API_KEY=sk-ficticia`);
  o proxy substitui o valor na requisição.
- Rodar os scripts com `python3 script.py` de dentro de `etapa0/` (não usar `python3 -I`,
  que impede a importação de `precos.py`).
