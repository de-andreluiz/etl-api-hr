# ETL API RH — OXEN

## Título e descrição

Este repositório contém pipelines de **extração, transformação e carga (ETL)** de dados de **Recursos Humanos** para a empresa fictícia **OXEN**. Os dados saem de uma **API REST** de ponto e entram no **Microsoft SQL Server** como tabelas `api_*`, uma por domínio de negócio.

A organização é por **domínio** em `date/<domínio>/` e por **janela temporal** em `jsons/<ano>/<período>/`. O período pode ser um mês isolado (`01` … `12`), trimestre agregado (`01-03`, …) ou exceções específicas de ano (ver abaixo).

## Mapa de domínios e destino SQL

Cada pasta possui um orquestrador `execute_*.py`, scripts de download em `jsons/` e um `*_treat.py` que materializa a tabela indicada:

| Pasta | Orquestrador | Tratamento | Tabela |
|--------|----------------|-------------|--------|
| `date/jornada/` | `execute_jornadas.py` | `jornada_treat.py` | `api_Jornada` |
| `date/afastamento/` | `execute_afastamentos.py` | `afastamento_treat.py` | `api_Afastamentos` |
| `date/faltas/` | `execute_faltas.py` | `falta_treat.py` | `api_Faltas` |
| `date/bancoHoras/` | `execute_bancohoras.py` | `bancoHoras_treat.py` | `api_BancoHoras` |
| `date/registroPonto/` | `execute_ponto.py` | `ponto_treat.py` | `api_RegistroPonto` |
| `date/auditoria/` | `execute_auditorias.py` | `auditoria_treat.py` | `api_Auditoria` |
| `date/ocorrencias/` | `execute_ocorrencias.py` | `ocorrencias_treat.py` | `api_Ocorrencias` |
| `date/horasExtras/` | `execute_horaextra.py` | `horaExtra_treat.py` | `api_HorasExtras` |

## Orquestradores (`execute_*.py`)

Todos seguem a mesma ideia; a descrição abaixo corresponde ao fluxo de `execute_jornadas.py` (os demais são análogos em estrutura).

**Descoberta de scripts:** percorre-se `jsons/` com `os.listdir`, aceitando apenas pastas de ano numérico e, dentro delas, subpastas de período. Em cada pasta de período, o primeiro arquivo `*.py` encontrado é registrado como o extrator daquele intervalo (há no máximo um `.py` por pasta de período).

**Seleção de período (“modo inteligente”):** a partir da data atual calculam-se mês/ano correntes e mês/ano anteriores. Uma função interna mapeia `(mês, ano)` para o **nome da pasta** de período:

- **Ano ≥ 2026:** um diretório por mês, nome `01` … `12`.
- **Ano 2024:** agrupamentos trimestrais (`01-03`, `04-06`, `07-09`), `10-11` e `12` sozinho.
- **Demais anos (ex.: 2025):** trimestres `01-03`, `04-06`; meses 7–12 em pastas individuais `07` … `12`.

Monta-se um dicionário `{ ano: [ períodos ] }` contendo primeiro o período do **mês anterior** e depois o do **mês atual** (sem duplicar). Só entram na fila períodos que existem na árvore descoberta.

**Execução:** para cada par ano/período ordenado, o orquestrador chama `subprocess.run([sys.executable, script_path], …)` — ou seja, **processo Python filho separado** por extrator. Em falha (exit code ≠ 0), há **até 5 tentativas** com **espera de 30 s** entre elas. O stdout/stderr do filho é capturado para log.

**Artefato esperado:** cada extrator grava um `.json` com o mesmo nome base do `.py` no mesmo diretório (ex.: `jornada01.py` → `jornada01.json`). O `.gitignore` ignora `*.json`; só o código de extração permanece versionado.

## Scripts de extração (`jsons/.../*.py`)

**HTTP:** uso de `requests` (em geral `requests.Session().post`). A URL é montada em tempo de execução:

`f"{os.environ['HR_API_BASE_URL'].rstrip('/')}/external_api/v1/reports/<recurso>"`,

onde `<recurso>` varia por domínio (ex.: `work_days`, `absences`, `missing_days`, `time_balances`, `time_cards`, `audit`, `occurrences`, `extra_times`).

**Cabeçalhos:** `access-token` vindo de `os.getenv("HR_API_ACCESS_TOKEN")`, mais `Content-Type: application/json` e, onde aplicável, `Accept-Encoding: gzip`.

**Corpo:** objeto JSON com chave `report` contendo parâmetros da API: `start_date`, `end_date`, `group_by`, `row_filters`, `columns`, `format` (tipicamente `json`). Cada arquivo `.py` fixa o intervalo de datas e o conjunto de colunas daquele recorte (mensal ou trimestral).

**Persistência:** em sucesso (`status_code == 200`), o corpo é interpretado com `response.json()` e escrito em disco com `json.dump(..., ensure_ascii=False, indent=4)`.

**Configuração:** `load_dotenv()` carrega `.env` no processo; a URL base exige `HR_API_BASE_URL` presente no ambiente após o load.

## Scripts de carga (`*_treat.py`)

**Inventário de entrada:** `glob.glob` recursivo em `jsons/**/*.json`, filtrando por padrão de nome quando necessário (ex.: apenas arquivos cujo nome contém o prefixo do domínio).

**Leitura e normalização:** abre-se cada JSON; espera-se uma chave `data` no topo. A estrutura interna é aninhada (listas de blocos com `data`, métricas em `summary`, listas de horas extras, etc.). Funções como `normalize_data` percorrem essas árvores, achatam campos semânticos (datas, matrícula, equipes, totais de horas) e devolvem **lista de dicionários** homogêneos — uma linha lógica por registro.

**Tipagem para carga:** os registros viram `pandas.DataFrame`, `fillna('')` e `astype(str)` para alinhar tudo a texto antes do SQL.

**Conexão:** string ODBC explícita para **ODBC Driver 18 for SQL Server**: `SERVER`, `DATABASE`, `UID`, `PWD` a partir de variáveis de ambiente (`DB_SERVER`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD`), com `Encrypt=yes`, `TrustServerCertificate=yes` e timeouts de conexão/login de 60 s. `pyodbc.connect` + `autocommit = False`.

**DDL:** se a flag interna `SKIP_DROP` for falsa (padrão), executa-se `DROP TABLE` condicional via `INFORMATION_SCHEMA.TABLES` e em seguida `CREATE TABLE` com colunas `NVARCHAR` de tamanhos definidos no script. O esquema é **próprio de cada domínio** (número e nomes de colunas batem com o `INSERT`).

**Carga:** `cursor.fast_executemany = True` e `executemany` com placeholders `?` e lotes de tamanho `BATCH_SIZE` (ex.: 5000 em jornada). Cada lote é `commit`ado. Em `OperationalError`, o código tenta **reabrir a conexão** até 3 vezes com `time.sleep(2)` entre tentativas; `ProgrammingError` em dados pode abortar o lote com log.

**Efeito colateral:** ao rodar com `SKIP_DROP` falso, a tabela de destino é **recriada do zero** a cada execução completa — ou seja, a carga é do tipo **full replace** daquele conjunto de arquivos JSON processados, não merge incremental por chave.

## Tecnologias

Python 3, **requests**, **pandas**, **pyodbc**, **python-dotenv**, **tqdm** (progresso nos tratamentos), SQL Server via **ODBC Driver 18**.

---

*Projeto de portfólio — contexto corporativo fictício **OXEN**.*
