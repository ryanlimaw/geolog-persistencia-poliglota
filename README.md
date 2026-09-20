
![LogiTech Express](src/public/logo-logitech-express.png)

# Plataforma de Telemetria Logística e Persistência Poliglota.

Projeto desenvolvido na disciplina **Implementação de Gerenciamento de Banco de Dados com NoSQL**, com o objetivo de integrar persistência relacional, dados geoespaciais e visualização analítica em uma aplicação Streamlit.

## Contexto

A transportadora LogiTech Express opera uma frota de caminhões em diversas regiões do Brasil. A plataforma GeoLog foi desenvolvida para lidar com:

- **Telemetria e sensores IoT:** coordenadas GPS, temperatura e logs em alta frequência, armazenados no MongoDB, com suporte a índices geoespaciais e buscas por proximidade.
- **Dados transacionais e cadastrais:** motoristas, veículos e ordens de serviço, armazenados em banco relacional para garantir integridade e consultas estruturadas.

A solução integra consultas relacionais, queries geoespaciais e um dashboard para acompanhamento da frota.

## Desenvolvedores

- [Lucca de Sena Barbosa](https://github.com/luccasena)
- [Ryan Emanuel Lima Miranda](https://github.com/ryanlimaw)

## Tecnologias

- Python
- Streamlit
- PostgreSQL
- MongoDB
- Docker Compose

## Como executar

### Pré-requisitos

- Python instalado
- Docker e Docker Compose instalados

### 1. Configurar o `.env`

Preencha o arquivo `.env`:

```env
POSTGRES_PORT=
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=

MONGO_URI=
MONGO_DB=
```

### 2. Configurar o `secrets.toml`

Preencha `src/.streamlit/secrets.toml`:

```toml
[connections.postgres]
url = ""

[mongodb]
uri = ""
database = ""
```

### 3. Iniciar os bancos

```bash
docker compose up -d
```

### 4. Popular os bancos

No Windows:

```powershell
.\.venv\Scripts\python.exe src\db\seed.py
```

### 5. Executar a aplicação

```bash
streamlit run src/app.py
```
