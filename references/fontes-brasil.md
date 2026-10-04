# Fontes de financiamento — Brasil

Catálogo de agências/programas a investigar. **CAPES PDSE**, **CAPES
PrInt**, **CNPq** (4 modalidades), **FAPERJ** e **FAPESB** têm fetcher
automatizado (`uv run bolsa-finder funding capes-pdse` / `capes-print` /
`cnpq` / `faperj` / `fapesb`, ou `funding applicable <target_level>` para
já filtrar pelo nível do candidato). Para as demais, siga
`references/elegibilidade.md` e monte o `FundingOpportunity` manualmente
a partir da página oficial atual -- não reutilize valores ou prazos deste
arquivo, que não leva URL/data de consulta e pode estar desatualizado.

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

- **Modalidades no exterior** (GDE -- Doutorado Pleno, SWE -- Doutorado
  Sanduíche, MPE -- Mestrado Profissional, PDE -- Pós-Doutorado) --
  automatizado via a página "Modalidades" (purpose/benefícios/duração,
  não um edital específico, então não expira como as chamadas abaixo).
  **Atenção**: só SWE tem texto de elegibilidade nessa página (vínculo
  institucional no Brasil, `likely`); GDE/MPE/PDE ficam honestamente
  `unknown` -- a página não diz nada sobre nacionalidade/vínculo para
  eles, então nada é afirmado. GDE e MPE são hoje as ÚNICAS fontes
  automatizadas para os níveis `pleno` e `mestrado`, respectivamente.
- **Chamadas específicas** (ex.: editais bilaterais CNPq/agência
  estrangeira) -- **não automatizado**: cada modalidade/parceria abre por
  "chamada" com URL e prazo próprios que mudam a cada edital. Buscar a
  chamada vigente em gov.br/cnpq e montar o `FundingOpportunity`
  manualmente para valor/prazo específicos.

## FAPESP (Fundação de Amparo à Pesquisa do Estado de São Paulo)

- **BEPE** (Bolsa Estágio de Pesquisa no Exterior) -- programa permanente,
  mas a página oficial (`fapesp.br/bolsas/bepe`) é renderizada via
  JavaScript e retorna corpo vazio para `httpx`+`selectolax`. **Não
  automatizado** por essa razão (ver regra de páginas dinâmicas em
  `references/elegibilidade.md`); se for investigar, use WebFetch/
  navegador e marque `unverified` caso não consiga extrair o texto.

## FAPs estaduais (Fundações de Amparo à Pesquisa)

Relevantes para o perfil do candidato conforme a instituição de origem.
Muitas têm programas próprios de bolsa-sanduíche/pós-doc com regras de
elegibilidade específicas (algumas exigem vínculo prévio com a instituição
do estado).

- **FAPERJ** (Rio de Janeiro) -- **automatizado** (`funding faperj`).
  "Doutorado Sanduíche (Estágio de Doutorando no Exterior)" tem página de
  programa permanente e estática, com elegibilidade explícita
  (`confirmed`: exige nacionalidade brasileira OU visto permanente, e
  matrícula em doutorado avaliado pela CAPES com conceito ≥3 em
  instituição sediada no RJ -- essa segunda restrição geográfica deve ser
  checada contra o perfil do candidato antes de recomendar).
- **FAPESB** (Bahia) -- **automatizado** (`funding fapesb`). "Pós-Doutorado
  2 (PD2)" tem página de programa permanente e estática. Elegibilidade é
  por vínculo institucional com instituição sediada na Bahia (`likely`,
  mesmo padrão indireto do PDSE/SWE), não nacionalidade explícita.
- **FAPESP** (São Paulo) -- **não automatizado**: a página do programa
  BEPE é renderizada via JavaScript (corpo vazio para
  `httpx`+`selectolax`); ver seção CNPq/FAPESP acima.
- **FAPEMIG** (Minas Gerais), **FACEPE** (Pernambuco), **FAPERGS** (Rio
  Grande do Sul), demais FAPs -- **não automatizadas ainda**. Têm
  programas de bolsa-sanduíche/pós-doc (ex.: FAPEMIG PCRH), mas
  publicados como "chamadas" com URL/prazo que mudam a cada edital, igual
  ao padrão do CNPq -- buscar a chamada vigente no site da FAP e montar o
  `FundingOpportunity` manualmente.

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
