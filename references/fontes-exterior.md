# Fontes de financiamento — Exterior

Catálogo de agências/programas a investigar por região. **DAAD Co-funded
Research Grant** e **MSCA Postdoctoral Fellowships (European track)** têm
fetcher automatizado (`uv run bolsa-finder funding daad` / `funding msca`).
Para as demais, siga `references/elegibilidade.md` e monte o
`FundingOpportunity` manualmente a partir da página oficial atual -- não
reutilize valores ou prazos deste arquivo, que não leva URL/data de
consulta e pode estar desatualizado.

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
- **MSCA Doctoral Networks** -- financia posições de doutorado em
  consórcios, geralmente sem restrição de nacionalidade mas com regras de
  mobilidade (ex.: não ter residido no país de destino recentemente há
  mais de 12 meses). Checar a chamada vigente no portal
  Euraxess/Horizon Europe -- não automatizado.
- **Erasmus Mundus Joint Doctorates/Masters** -- consórcios específicos,
  cada um com seu próprio processo seletivo e critérios de elegibilidade
  geográfica.

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
