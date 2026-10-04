# Fontes de financiamento — Exterior

Catálogo de agências/programas a investigar por região. **DAAD Co-funded
Research Grant**, **MSCA Postdoctoral Fellowships (European track)**,
**MSCA Doctoral Networks** e **Fundación Carolina** (Doctorado) têm
fetcher automatizado (`uv run bolsa-finder funding daad` / `msca` /
`msca-dn` / `fundacion-carolina`). Para as demais, siga
`references/elegibilidade.md` e monte o `FundingOpportunity` manualmente
a partir da página oficial atual -- não reutilize valores ou prazos
deste arquivo, que não leva URL/data de consulta e pode estar
desatualizado.

## Alemanha

- **DAAD** -- além do co-funded research grant automatizado, há outros
  programas (bolsa de doutorado integral, bolsas de pesquisa de curta
  duração) com elegibilidade e prazos próprios por chamada/país de
  origem. Buscar no banco de bolsas do DAAD filtrando por "Brazil" e pelo
  nível-alvo do candidato.

## União Europeia

- **MSCA (Marie Skłodowska-Curie Actions) -- Postdoctoral Fellowships,
  European track** -- automatizado. Elegível a pesquisadores de qualquer
  nacionalidade (confirmado explicitamente na página oficial). **Atenção**:
  isso NÃO cobre a trilha "Global Postdoctoral Fellowships" do mesmo
  programa, que é restrita a nacionais/residentes de longo prazo da
  UE/países associados -- não confundir as duas ao reportar ao candidato.
- **MSCA Doctoral Networks** -- automatizado (`funding msca-dn`). Financia
  posições de doutorado completas em consórcios europeus. A página
  oficial declara explicitamente "can be of any nationality" (`confirmed`),
  mapeado como `pleno`. Tem regras de mobilidade (ex.: não ter residido no
  país de destino recentemente há mais de 12 meses) que não afetam a
  elegibilidade de nacionalidade, mas devem ser checadas contra o perfil
  do candidato.
- **Erasmus Mundus Joint Doctorates/Masters** -- **não automatizado**:
  investigado nesta sessão; a trilha de doutorado foi extinta (migrou
  para o MSCA Doctoral Networks acima). Para mestrado, os critérios estão
  só no PDF anual "Erasmus+ Programme Guide", inscrição descentralizada
  por consórcio, sem página fixa com texto de elegibilidade.

## Espanha

- **Fundación Carolina -- Becas de Doctorado** -- automatizado
  (`funding fundacion-carolina`). Elegibilidade explícita: "Tener
  ciudadanía de alguno de los países de América Latina integrantes de la
  Comunidad Iberoamericana de Naciones" (`confirmed` -- Brasil se
  qualifica), mapeado como `pleno`. **Atenção**: a URL
  (`gestion.fundacioncarolina.es/programas/6519`) inclui um ID numérico e
  a página mostra o ciclo vigente ("Convocatoria: C.2026") -- revalidar
  se a Fundación Carolina reestruturar as páginas por ciclo no futuro.
  Fundación Carolina também tem bolsas de mestrado/pós-doutorado em
  outras URLs (`/postgrado/`, estâncias pós-doutorais), investigadas mas
  ainda não automatizadas nesta sessão.

## Estados Unidos

- **Fulbright DDRA** (Doctoral Dissertation Research Award) -- doutorado-
  sanduíche nos EUA. Elegibilidade real e explícita: cidadania brasileira
  sem dupla cidadania com os EUA, matrícula regular em doutorado em
  universidade brasileira, residência no Brasil, proficiência em inglês
  (TOEFL iBT 81 / IELTS 6,5 / Duolingo 110). **Não automatizado**:
  investigado nesta sessão (`fulbright.org.br`), mas a elegibilidade só
  aparece em PDFs específicos de cada ciclo ("Call-BR-DDR-AAAA-AAAA.pdf"),
  não numa página HTML persistente -- mesmo problema estrutural do CNPq
  (URL muda a cada ciclo). A página `fulbright.org.br/bolsas-para-
  brasileiros/` é só um índice, sem o texto de elegibilidade. Buscar o
  PDF do ciclo vigente e extrair a elegibilidade manualmente.

## Reino Unido

- **Chevening** (mestrado) -- **não automatizado**: elegibilidade real
  existe ("Be a citizen of a Chevening-eligible country or territory",
  Brasil se qualifica), mas a página `chevening.org` bloqueou requisições
  automatizadas (sem resposta/timeout) nas duas tentativas desta sessão
  -- revisitar com navegador real ou WebFetch em vez de `httpx` puro.
- **Commonwealth Scholarships** -- **não automatizado**: restrito a
  cidadãos de países-membros da Commonwealth; Brasil não se qualifica.

## Ásia-Pacífico

- **JSPS Postdoctoral Fellowships** (Japão) -- **não automatizado**: sem
  critério de nacionalidade explícito em HTML fixo ("citizens of a
  country that has diplomatic relations with Japan" exige inferência);
  editais via PDF anual.
- **Singapore International Graduate Award (SINGA)** -- **não
  automatizado**: a URL encontrada via busca (`a-star.edu.sg/...SINGA`)
  retornou 404 nas duas tentativas desta sessão (site parece ter sido
  reestruturado); revisitar buscando a URL atual.
- **Global Korea Scholarship (GKS)** (Coreia do Sul) -- **não
  automatizado**: sem página HTML fixa, detalhes só em PDF de
  "Application Guidelines" por chamada anual.
- **Australia Awards** -- **não automatizado**: restrito a países do
  Indo-Pacífico e África; Brasil não consta na lista de elegibilidade.
- **Endeavour Leadership Program** (Austrália) -- descontinuado ("no
  further rounds").
- **Manaaki New Zealand Scholarships** -- **não automatizado**: Brasil
  não é elegível para pós-graduação stricto sensu (só cursos curtos de
  2-4 semanas); verificação só via formulário interativo.

## Canadá

- **Vanier CGS** -- descontinuado ("no longer accepting applications").
- **Canadian Queen Elizabeth II Diamond Jubilee Scholarships** --
  **não automatizado**: programa descentralizado por universidade, sem
  página central com critério fixo.

## Suíça e França

- **Swiss Government Excellence Scholarships** -- **não automatizado**:
  critérios por país só em PDFs/factsheets anuais, sem texto em HTML.
- **Programme France Excellence Eiffel** -- **não automatizado**: só PDF
  de chamada anual ("Vade-mecum"); submissão fechada por via institucional
  francesa.
- **CNRS / Campus France** -- **não automatizado**: não é um programa
  unificado; o diretório do Campus France é JS-rendered e indexa
  centenas de editais avulsos.

## Outras regiões

- Agências nacionais de fomento (ex.: NWO na Holanda, ANR na França)
  costumam ter editais específicos para pesquisadores
  estrangeiros/pós-doutorado; buscar pelo nome da agência + "postdoctoral
  fellowship international applicants". NWO especificamente investigado
  nesta sessão: **não automatizado** (critérios só em PDFs de "Call for
  Proposals" por chamada).

## Observação

Para qualquer item acima, o relatório final só deve incluir o item como
`FundingOpportunity` com `url` + `consulted_at` reais, obtidos na sessão
atual. Itens apenas mencionados aqui sem verificação não entram no
relatório -- citar como "pista a investigar" no texto, não como bolsa
confirmada.
