# Como avaliar elegibilidade de brasileiros

Isto documenta a mesma disciplina que `eligibility.py` aplica em código,
para quando você for montar um `FundingOpportunity` manualmente (fontes
além de CAPES PDSE e DAAD, que já são automatizadas).

## Regra central

Nunca infira elegibilidade a partir de "parece que". A classificação deve
ser sustentada por um trecho verbatim da própria fonte. Sem trecho, o
nível é `unknown` (não existe fonte confiável) ou `unverified` (a fonte
existe mas não pôde ser lida -- ex.: página dinâmica, PDF protegido).

## Os quatro níveis

- **`confirmed`**: a fonte declara explicitamente que candidatos
  brasileiros/de instituições brasileiras são elegíveis. Exemplo real
  (DAAD): *"Doctoral candidates at universities in Brazil, who have been
  awarded a domestic scholarship from CAPES or one of the following
  foundations: ..."*. Trecho literal, sem ambiguidade de nacionalidade.
- **`likely`**: a fonte não menciona nacionalidade diretamente, mas o
  desenho do programa implica elegibilidade para o perfil do candidato
  (ex.: restrito a estudantes matriculados em doutorado reconhecido pela
  CAPES no Brasil, com seleção interna pela instituição). Exemplo real
  (CAPES PDSE): *"O candidato deve... atender aos requisitos para
  candidatura previstos no edital durante o processo seletivo interno em
  sua Instituição."* -- confirma o canal (edital institucional), não a
  regra de nacionalidade em si. Sempre que marcar `likely`, diga
  explicitamente no relatório que o edital específico da instituição/ano
  precisa ser conferido.
- **`unverified`**: a página existe mas não foi possível extrair texto
  útil (ex.: conteúdo renderizado via JavaScript, PDF que falhou ao
  parsear). Não tente adivinhar a partir do título da página ou de
  metadados soltos.
- **`unknown`**: não há fonte oficial localizada, ou a fonte foi lida mas
  não contém nenhuma informação relacionável a elegibilidade.

## Processo ao avaliar uma fonte nova

1. Buscar a página oficial do programa/edital (não um agregador de
   terceiros, exceto para descoberta inicial).
2. Buscar com WebFetch/WebSearch por palavras-chave de nacionalidade:
   "Brazil", "Brazilian", "brasileiro(a)", "nationality", "country of
   origin", "países elegíveis".
3. Copiar o trecho exato (não parafrasear) que sustenta a classificação.
4. Preencher `url` com o link exato consultado e `consulted_at` com a
   data de hoje.
5. Se o trecho não existir, não force uma classificação `likely` ou
   `confirmed` -- use `unknown`/`unverified` e diga isso ao usuário.

## Páginas dinâmicas (JS-rendered)

Nesta versão não há Playwright. Se `httpx` + `selectolax` (ou WebFetch)
não retornarem texto substantivo (corpo vazio, menos de ~200 caracteres
úteis), trate como `unverified` e registre no relatório que a página
precisa ser checada manualmente no navegador.
