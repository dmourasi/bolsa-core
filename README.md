# bolsa-core

Núcleo compartilhado de bolsa-skill e bolsa-web: fontes de financiamento com
evidência de elegibilidade, leitura de currículo Lattes, cliente OpenAlex,
scoring determinístico e relatório.

Este pacote não tem interface de linha de comando nem servidor. Cada produto
(skill e web) importa o que precisa de `bolsa_core`.

```bash
uv sync
uv run pytest
```

Regras que valem para todo o núcleo:
- Nenhum prazo, valor, critério ou vaga é inventado. Sem fonte, o campo fica `unknown`.
- Nenhum dado pessoal estrutural (CPF, endereço, telefone, data de nascimento) entra nos modelos.
- `pymupdf`, `lxml` e `selectolax` são fixados em faixas testadas. `selectolax` está limitado a 0.x porque o código usa o backend Modest.
