
![LogiTech Express](src/public/logo-logitech-express.png)

# Plataforma de Telemetria Logística e Persistência Poliglota.

Projeto desenvolvido na disciplina **Implementação de Gerenciamento de Banco de Dados com NoSQL**, com o objetivo de integrar persistência relacional, dados geoespaciais e visualização analítica em uma aplicação Streamlit.

## Contexto

A transportadora LogiTech Express opera uma frota de caminhões em diversas regiões do Brasil. A plataforma GeoLog foi desenvolvida para lidar com:

- **Telemetria e sensores IoT:** coordenadas GPS (GeoJSON), temperatura da carga e velocidade, armazenadas no MongoDB, com índice geoespacial `2dsphere` e buscas por proximidade.
- **Dados cadastrais:** motoristas e veículos, armazenados no PostgreSQL para garantir integridade referencial e consultas estruturadas.
- **Simulação de movimentação em tempo real:** o botão "Simular Movimentação" gera novas leituras para os veículos com pequenas variações aleatórias de GPS, velocidade e temperatura, grava os pontos no MongoDB e atualiza o mapa e os indicadores sem reiniciar a aplicação.

A aplicação cruza os dois bancos em memória (join poliglota) e apresenta os resultados num mapa, numa visão unificada da frota e num dashboard analítico.

> O enunciado original sugere SQLite para a parte relacional; o grupo adotou **PostgreSQL**. As ordens de serviço citadas no estudo de caso não fazem parte desta implementação.

## Desenvolvedores

- [Lucca de Sena Barbosa](https://github.com/luccasena)
- [Ryan Emanuel Lima Miranda](https://github.com/ryanlimaw)

## Tecnologias

- Python
- Streamlit
- PostgreSQL (psycopg2)
- MongoDB (pymongo)
- Folium e Plotly
- Docker Compose

## Arquitetura

| Banco | O que guarda |
|---|---|
| PostgreSQL | `motoristas` (id, nome, cnh, status) e `veiculos` (id, placa, modelo, motorista_id) |
| MongoDB | coleção `telemetria`: `veiculo_id`, `location` (GeoJSON Point `[longitude, latitude]`), `temperatura`, `velocidade`, `timestamp` |

- `src/db/`: conexões (`clients.py`) e carga inicial (`seed.py`).
- `src/services/`: acesso a cada banco (`veiculos_service.py`, `telemetria_service.py`) e a integração dos dois (`frota_service.py`).
- `src/pages/`: as páginas do Streamlit.

A aplicação garante, na primeira consulta ao MongoDB, os índices `location` (2dsphere) e `veiculo_id + timestamp`.

## Como executar

### Pré-requisitos

- Python instalado
- Docker e Docker Compose instalados

### 1. Instalar as dependências

```bash
python -m venv .venv
```

No Windows:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configurar o `.env`

O `.env` é usado pelo `docker-compose.yml` e pelo `seed.py`. Copie o exemplo:

```powershell
copy .env_example .env
```

(Linux/macOS: `cp .env_example .env`.) O exemplo já vem com os valores de desenvolvimento do `docker-compose.yml`. Se trocar usuário, senha ou porta, troque no `.env` e o compose acompanha:

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=geolog
POSTGRES_USER=<usuario>
POSTGRES_PASSWORD=<senha>

MONGO_USER=<usuario>
MONGO_PASSWORD=<senha>
MONGO_URI=mongodb://<usuario>:<senha>@localhost:27018
MONGO_DB=geolog
```

### 3. Configurar o `secrets.toml`

O `secrets.toml` é usado pela aplicação Streamlit (`src/db/clients.py`). Copie o exemplo e use os mesmos dados do `.env`:

```powershell
copy src\.streamlit\secrets-example.toml src\.streamlit\secrets.toml
```

```toml
[postgres]
host = "localhost"
port = 5433
database = "geolog"
user = "<usuario>"
password = "<senha>"

[mongodb]
uri = "mongodb://<usuario>:<senha>@localhost:27018"
database = "geolog"
```

O `.env` e o `secrets.toml` estão no `.gitignore` e não devem ser commitados.

### 4. Iniciar os bancos

```bash
docker compose up -d
```

PostgreSQL na porta 5433 e MongoDB na porta 27018.

### 5. Popular os bancos (seed)

No Windows:

```powershell
.\.venv\Scripts\python.exe src\db\seed.py
```

O seed recria as tabelas e a coleção a cada execução (os dados são sempre os mesmos):

- **PostgreSQL:** 3 motoristas e 3 veículos.
- **MongoDB:** histórico de telemetria com **12 leituras por veículo** (36 no total), de 10 em 10 minutos. A última leitura de cada veículo é a do seed sugerido no enunciado: o 101 em operação normal, o 102 com carga congelada e acima de 80 km/h, o 103 parado.

### 6. Executar a aplicação

```bash
streamlit run src/app.py
```

No Windows, com o ambiente virtual: `.\.venv\Scripts\python.exe -m streamlit run src\app.py`.

## Páginas

- **Geolog** (página inicial): busca geoespacial por raio a partir de um endereço ou de latitude e longitude. "Área Delimitada (Raio)" usa `$geoWithin`, e "Locais Próximos" usa `$geoNear`, com a distância até o ponto. Os veículos (posição atual) aparecem num mapa Folium com o círculo do raio, e placa, modelo e status vêm do PostgreSQL.
- **Visão Geral**: a visão unificada da frota. O cadastro do PostgreSQL cruzado com a última leitura de telemetria do MongoDB: motorista, placa, modelo, status, última temperatura, velocidade, coordenadas e horário da leitura.
- **Dashboard da Frota**: KPIs do estado atual (frota ativa, temperatura média atual, alertas de velocidade acima de 80 km/h e veículos parados, sempre pela última leitura de cada veículo), a situação de cada veículo, gráficos Plotly de velocidade atual, de motoristas por status e o histórico de temperatura por veículo.
