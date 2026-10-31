# Decisões de arquitetura (ADRs)

Registro curto das decisões que mais afetam o desenho do pipeline. Formato
inspirado em [ADR](https://adr.github.io/): contexto, decisão e consequências.

---

## ADR-001 — ELT em vez de ETL

**Contexto.** A API entrega um snapshot pequeno (100 moedas). O valor do dado
está na série histórica, e o esquema pode evoluir.

**Decisão.** Gravar o JSON cru no lake primeiro (bronze) e transformar depois,
já dentro do warehouse, com dbt.

**Consequências.**

- (+) Reprocessar o histórico sem chamar a API de novo
- (+) Transformação versionada e testável em SQL
- (+) O lake vira fonte da verdade do "como veio"
- (−) Mais storage e um passo a mais de infraestrutura

---

## ADR-002 — Object storage S3-compatível (RustFS) como camada bronze

**Contexto.** Precisávamos de um data lake local, sem custo de nuvem, que
conversasse com o ecossistema S3. O MinIO era a escolha óbvia — mas encerrou o
modelo open source e removeu as imagens públicas do Docker Hub, o que quebrou
qualquer compose que o referenciava.

**Decisão.** RustFS (Apache 2.0, S3-compatible) rodando em container, com escrita
via `boto3` e assinatura `s3v4`, particionamento `dt=YYYY-MM-DD/hora=HH/`. Toda a
configuração é genérica (`S3_*`), sem menção ao fornecedor no código.

**Consequências.**

- (+) API idêntica à S3: o mesmo código roda em AWS S3, R2 ou GCS depois
- (+) Console web para inspeção manual
- (+) Bucket criado pelo próprio pipeline (`ensure_bucket`), sem container extra
- (−) Projeto mais novo que o MinIO; a compatibilidade S3 cobre o que usamos
- (−) Disco local é o limite de escala

---

## ADR-003 — dbt para a transformação

**Contexto.** Alternativas: pandas dentro da DAG, stored procedures ou dbt.

**Decisão.** dbt com modelos em camadas (`staging` view → `marts` tabelas) e
testes declarativos.

**Consequências.**

- (+) Testes e documentação junto do modelo
- (+) Linhagem e `dbt docs` de graça
- (+) Incremental sem escrever SQL de merge na mão
- (−) Dependência extra na imagem e um pouco mais de curva de aprendizado

---

## ADR-004 — Idempotência via `data_interval_start`

**Contexto.** Retries são o normal em pipelines. Usar `now()` como timestamp de
ingestão faz cada retry criar um snapshot "novo" com o mesmo conteúdo.

**Decisão.** `ingested_at` recebe o início do intervalo lógico da DAG
(`context["data_interval_start"]`), e a escrita é UPSERT
(`on conflict (ingested_at) do update`).

**Consequências.**

- (+) Rodar de novo a mesma hora sobrescreve, não duplica
- (+) Backfill fica trivial (basta rodar o intervalo)
- (−) Exige disciplina: nunca usar `now()` como chave

---

## ADR-005 — Postgres como data warehouse

**Contexto.** O volume é modesto (100 linhas por hora), e o objetivo é aprendizado
com uma stack que existe no mercado.

**Decisão.** Postgres 16 dedicado (`dw`), separado do Postgres de metadados do
Airflow, exposto na porta 5433.

**Consequências.**

- (+) SQL completo, JSONB nativo, zero custo
- (+) Separação clara entre metadados e dados de negócio
- (−) Não é um warehouse colunar; para escala real, trocar por BigQuery/Snowflake/Redshift

---

## ADR-006 — XCom só com referências

**Contexto.** O caminho mais óbvio seria a task de extração devolver a lista de
moedas para a task seguinte.

**Decisão.** A task devolve apenas `bucket`, `key` e contagens; o payload é lido
do lake pela próxima task.

**Consequências.**

- (+) Não infla o banco de metadados do Airflow
- (+) O lake passa a ser o contrato entre as etapas
- (−) Uma leitura extra no S3 (desprezível nesse volume)

---

## ADR-007 — Segredos apenas por variáveis de ambiente

**Contexto.** Projeto de portfólio, mas precisa mostrar prática de segurança.

**Decisão.** Nenhuma credencial no código. Defaults no `docker-compose.yml`
para rodar out-of-the-box, sobrescritos por `.env` (que está no `.gitignore`).

**Consequências.**

- (+) Fácil trocar por Secrets Backend / Vault / SSM
- (−) Os defaults são fracos por definição — documentado no README
