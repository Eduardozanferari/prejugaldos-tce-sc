# Fontes oficiais por tema: levantamento e validação (Etapa 0)

Validação feita em 10/11/2026 a partir do ambiente de execução na nuvem, com `curl`
e com um navegador sem interface (Chromium via Playwright). "Bloqueio ao robô" significa
que o servidor respondeu 403 ou devolveu uma página de desafio; isso não impede a leitura
humana, mas exige tratamento no coletor (navegador real, RSS ou outra rota).

| Tema | Fonte | URL testada | Resultado | Como ler no fluxo diário |
| --- | --- | --- | --- | --- |
| Tribunais superiores | STF, portal de notícias | https://noticias.stf.jus.br/ | 200 no navegador; 403 ao `curl` | Navegador sem interface, ou RSS se existir |
| Tribunais superiores | STF, portal institucional | https://portal.stf.jus.br/noticias/ | 403 (curl e navegador) | Não usar; preferir noticias.stf.jus.br |
| Tribunais superiores | STJ, portal | https://www.stj.jus.br/sites/portalp/Inicio | 200 | Página inicial carrega; a página de notícias é montada por JavaScript, URL a confirmar com navegador |
| Tribunais superiores | STJ, notícias (URL antiga) | https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias.aspx | 404 | URL desatualizada |
| Tribunais superiores | TST, notícias | https://www.tst.jus.br/noticias | 202 com corpo vazio (desafio anti-robô) | Navegador sem interface |
| Política / tribunais | TSE, notícias | https://www.tse.jus.br/comunicacao/noticias | 403 (curl e navegador) | Bloqueio ao robô; avaliar RSS ou Agência de notícias |
| Direito | Diário Oficial da União | https://www.in.gov.br/leiturajornal | Sem resposta (erro de protocolo HTTP/2 e HTTP/1.1) | Testar de outro endereço IP; existe API da Imprensa Nacional a avaliar |
| Direito | Planalto, legislação | https://www.planalto.gov.br/ccivil_03/ | Sem resposta (conexão encerrada) | Testar de outro endereço IP |
| Política | Agência Câmara | https://www.camara.leg.br/noticias/ | 200 | Leitura direta; tem RSS |
| Política | Agência Senado | https://www12.senado.leg.br/noticias | 200 | Leitura direta; tem RSS |
| Política | Agência Gov (gov.br) | https://www.gov.br/pt-br/noticias | Redireciona para agenciagov.ebc.com.br (host ainda não liberado neste ambiente) | Liberar agenciagov.ebc.com.br e retestar |

Observações:

1. Os bloqueios do STF, TSE e TST são típicos de proteção anti-robô. Em produção, o
   coletor oficial deve usar um navegador sem interface ou feeds RSS, e respeitar o
   `robots.txt` de cada portal.
2. As falhas do DOU e do Planalto podem ser bloqueio ao IP do provedor de nuvem. O teste
   precisa ser repetido do servidor onde o portal vai rodar, antes de fechar a arquitetura.
3. Faltam validar: portais de Tecnologia (comunicados de fabricantes), Cultura (editoras,
   museus, publicações especializadas) e Ciência (revistas revisadas por pares e instituições).
   Esses domínios entram como "domínios confiáveis" por tema no painel e serão listados
   quando os subtemas forem definidos (decisão em aberto no briefing).
