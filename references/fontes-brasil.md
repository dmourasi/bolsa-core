# Fontes de financiamento — Brasil

Catálogo de agências/programas a investigar. **CAPES PDSE** e **CAPES
PrInt** têm fetcher automatizado
(`uv run bolsa-finder funding capes-pdse` / `funding capes-print`). Para
as demais, siga `references/elegibilidade.md` e monte o
`FundingOpportunity` manualmente a partir da página oficial atual -- não
reutilize valores ou prazos deste arquivo, que não leva URL/data de
consulta e pode estar desatualizado.

## CAPES (Coordenação de Aperfeiçoamento de Pessoal de Nível Superior)

- **PDSE** (Doutorado-Sanduíche no Exterior) -- automatizado. Cobre só
  doutorado. Elegibilidade é institucional/por edital, não só
  nacionalidade; ver `references/elegibilidade.md`.
- **PrInt** (Programa Institucional de Internacionalização) -- automatizado.
  Cobre mobilidade de doutorandos E pós-doutorandos, mas as vagas são
  geridas pelas próprias IES participantes; critérios finais variam por
  universidade/edital interno. Buscar o edital PrInt da instituição do
  candidato para confirmar.
- Outras modalidades de mobilidade -- checar a seção de "Bolsas e Auxílios
  Internacionais" no site da CAPES para o programa/país de interesse.

## CNPq (Conselho Nacional de Desenvolvimento Científico e Tecnológico)

- Bolsas de doutorado-sanduíche (SWE -- Doutorado Sanduíche no Exterior) e
  pós-doutorado (PDJ -- Pós-Doutorado Júnior, e modalidades de
  pós-doutorado no exterior). **Não automatizado**: o CNPq não mantém uma
  página de programa permanente -- cada modalidade é aberta por "chamada"
  com URL e prazo próprios, que mudam a cada edital. Buscar a chamada
  vigente em gov.br/cnpq e montar o `FundingOpportunity` manualmente.

## FAPESP (Fundação de Amparo à Pesquisa do Estado de São Paulo)

- **BEPE** (Bolsa Estágio de Pesquisa no Exterior) -- programa permanente,
  mas a página oficial (`fapesp.br/bolsas/bepe`) é renderizada via
  JavaScript e retorna corpo vazio para `httpx`+`selectolax`. **Não
  automatizado** por essa razão (ver regra de páginas dinâmicas em
  `references/elegibilidade.md`); se for investigar, use WebFetch/
  navegador e marque `unverified` caso não consiga extrair o texto.

## FAPs estaduais (Fundações de Amparo à Pesquisa)

Relevantes para o perfil do candidato conforme a instituição de origem,
ex.: FAPESP (SP), FAPEMIG (MG), FAPERJ (RJ), FACEPE (PE), entre outras.
Muitas têm programas próprios de bolsa-sanduíche/pós-doc com regras de
elegibilidade específicas (algumas exigem vínculo prévio com a instituição
do estado). Buscar o programa da FAP correspondente à instituição do
candidato.

## Editais de mobilidade específicos

- Editais conjuntos CAPES/agência estrangeira (bilaterais), frequentemente
  por país (ex.: CAPES-DAAD, CAPES-COFECUB com a França). Buscar
  "CAPES edital [país] [ano]" para o edital vigente.
- Editais de instituições de destino que aceitam financiamento brasileiro
  combinado (cotutela/sanduíche) -- normalmente descritos na própria
  página do programa de pós-graduação de destino.

## Observação

Para qualquer item acima, o relatório final só deve incluir o item como
`FundingOpportunity` com `url` + `consulted_at` reais, obtidos na sessão
atual. Itens apenas mencionados aqui sem verificação não entram no
relatório -- citar como "pista a investigar" no texto, não como bolsa
confirmada.
