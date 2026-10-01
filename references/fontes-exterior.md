# Fontes de financiamento — Exterior

Catálogo de agências/programas a investigar por região. Apenas o
**DAAD Co-funded Research Grant** tem fetcher automatizado
(`uv run bolsa-finder funding daad`). Para as demais, siga
`references/elegibilidade.md` e monte o `FundingOpportunity` manualmente a
partir da página oficial atual -- não reutilize valores ou prazos deste
arquivo, que não leva URL/data de consulta e pode estar desatualizado.

## Alemanha

- **DAAD** -- além do co-funded research grant automatizado, há outros
  programas (bolsa de doutorado integral, bolsas de pesquisa de curta
  duração) com elegibilidade e prazos próprios por chamada/país de
  origem. Buscar no banco de bolsas do DAAD filtrando por "Brazil" e pelo
  nível-alvo do candidato.

## União Europeia

- **MSCA (Marie Skłodowska-Curie Actions)** -- doutorados e pós-docs
  financiados pela Comissão Europeia, geralmente sem restrição de
  nacionalidade mas com regras de mobilidade (ex.: não ter residido no
  país de destino recentemente). Checar a chamada vigente no portal
  Euraxess/Horizon Europe.
- **Erasmus Mundus Joint Doctorates/Masters** -- consórcios específicos,
  cada um com seu próprio processo seletivo e critérios de elegibilidade
  geográfica.

## Estados Unidos

- **Fulbright** -- programas de doutorado/pós-doutorado para brasileiros,
  geridos pela Comissão Fulbright Brasil; elegibilidade e prazos
  publicados anualmente no site da comissão.

## Reino Unido

- **Chevening**, bolsas institucionais de universidades (ex.: Commonwealth
  Scholarships quando aplicável) -- verificar elegibilidade de
  nacionalidade por programa, pois alguns são restritos a países da
  Commonwealth.

## Outras regiões

- Agências nacionais de fomento (ex.: NWO na Holanda, ANR na França, JSPS
  no Japão) costumam ter editais específicos para pesquisadores
  estrangeiros/pós-doutorado; buscar pelo nome da agência + "postdoctoral
  fellowship international applicants".

## Observação

Para qualquer item acima, o relatório final só deve incluir o item como
`FundingOpportunity` com `url` + `consulted_at` reais, obtidos na sessão
atual. Itens apenas mencionados aqui sem verificação não entram no
relatório -- citar como "pista a investigar" no texto, não como bolsa
confirmada.
