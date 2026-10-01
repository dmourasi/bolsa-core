# Fontes de financiamento — Brasil

Catálogo de agências/programas a investigar. Apenas **CAPES PDSE** tem
fetcher automatizado (`uv run bolsa-finder funding capes-pdse`). Para as
demais, siga `references/elegibilidade.md` e monte o `FundingOpportunity`
manualmente a partir da página oficial atual -- não reutilize valores ou
prazos deste arquivo, que não leva URL/data de consulta e pode estar
desatualizado.

## CAPES (Coordenação de Aperfeiçoamento de Pessoal de Nível Superior)

- **PDSE** (Doutorado-Sanduíche no Exterior) -- automatizado. Elegibilidade
  é institucional/por edital, não só nacionalidade; ver
  `references/elegibilidade.md`.
- **PRINT** (Programa Institucional de Internacionalização) -- bolsas de
  mobilidade geridas pelas próprias IES, critérios variam por
  universidade/edital interno. Buscar o edital PRINT da instituição do
  candidato.
- Bolsas de pós-doutorado e outras modalidades de mobilidade -- checar a
  seção de "Bolsas e Auxílios Internacionais" no site da CAPES para o
  programa/país de interesse.

## CNPq (Conselho Nacional de Desenvolvimento Científico e Tecnológico)

- Bolsas de doutorado-sanduíche (SWE -- Doutorado Sanduíche no Exterior) e
  pós-doutorado (PDJ -- Pós-Doutorado Júnior, e modalidades de
  pós-doutorado no exterior). Critérios de elegibilidade e cotas variam
  por chamada; buscar a chamada vigente no site do CNPq.

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
