# Analytical Ecosystem

A modular, containerized analytics platform. Pick the services you need - databases, notebooks, orchestration, visualization - and spin them up with a single command.

## Quick Start

```bash
# Interactive mode - select services from a menu
./ecosystem

# Or specify services directly
./ecosystem --profiles postgres,jupyter,metabase start

# Check status
./ecosystem status

# Stop everything
./ecosystem stop
```

## Available Services

| Category | Service | Port | Description |
|----------|---------|------|-------------|
| **Database** | PostgreSQL | 5432 | Relational database |
| **Database** | MySQL | 3306 | Relational database |
| **Storage** | MinIO | 9000/9001 | S3-compatible object storage |
| **Cache** | Redis | 6379 | In-memory data store |
| **Search** | Elasticsearch | 9200 | Search and analytics engine |
| **Search** | Kibana | 5601 | Elasticsearch visualization |
| **Notebook** | JupyterLab | 8888 | Interactive notebooks with Python, R, Julia |
| **Visualization** | Metabase | 3000 | Business intelligence dashboards |
| **Visualization** | Big Beautiful Screens | 8000 | Real-time display dashboards |
| **Visualization** | Grafana | 3001 | Metrics and monitoring dashboards |
| **Orchestration** | Airflow | 8080 | Workflow orchestration with Docker operator |
| **Orchestration** | Ofelia | - | Lightweight cron scheduler |

## CLI Commands

```bash
./ecosystem                              # Interactive mode
./ecosystem list                         # List available services
./ecosystem --profiles postgres,jupyter start   # Start specific services
./ecosystem stop                         # Stop all services
./ecosystem restart                      # Restart services
./ecosystem status                       # Show running services
./ecosystem test                         # Run health checks
./ecosystem logs [service]               # Show logs (follows)
./ecosystem shell <service>              # Open shell in container
./ecosystem build                        # Build service images
./ecosystem clean                        # Stop and remove all volumes (data reset)
./ecosystem env --output .env            # Generate an env file from fragments
./ecosystem --verbose status             # Show docker compose warnings
```

## Architecture

```
analytical-ecosystem/
├── ecosystem                   # CLI entry point (bash wrapper)
├── ecosystem.py                # Python CLI
├── requirements.txt            # Python dependencies
├── cli/                        # CLI modules
│   ├── config.py               # Service discovery
│   ├── docker.py               # Docker Compose wrapper
│   ├── commands.py             # Command implementations
│   └── ui.py                   # Interactive mode
├── orchestration/
│   ├── docker/                 # Docker Compose setup
│   │   └── docker-compose.yml
│   └── kubernetes/             # Future K8s support
├── services/                   # Service-specific configs
│   ├── postgres/
│   │   └── service.yaml        # Service metadata
│   ├── jupyter/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── service.yaml
│   └── ...
├── shared/                     # Shared directories (mounted into containers)
│   ├── dags/                   # Airflow DAGs (also accessible from Jupyter)
│   ├── notebooks/              # Jupyter notebooks
│   └── data/                   # Shared data files
└── .env                        # Configuration
```

## Adding a New Service

1. Create a directory under `services/`:
   ```bash
   mkdir services/myservice
   ```

2. Add a `service.yaml`:
   ```yaml
   name: My Service
   category: visualization  # database, storage, cache, search, notebook, visualization, orchestration
   port: 8000
   url: "http://localhost:8000"

   healthcheck:
     type: http  # or "exec"
     endpoint: "http://localhost:8000/health"
   ```

   You can use `${VAR:-default}` placeholders in `service.yaml`. The CLI expands them
   from `.env` and your shell environment so URLs and health checks stay in sync.

3. Add the service to `orchestration/docker/docker-compose.yml`

4. The CLI will auto-discover it on next run

## Shared Directories

The `shared/` directory is mounted into relevant containers:

| Directory | Mounted In | Path In Container |
|-----------|-----------|-------------------|
| `shared/dags/` | Airflow, Jupyter | `/opt/airflow/dags`, `/home/jovyan/work/dags` |
| `shared/notebooks/` | Jupyter | `/home/jovyan/work/notebooks` |
| `shared/data/` | Jupyter | `/home/jovyan/work/data` |

This means you can:
- Edit DAGs from your host machine OR from Jupyter
- Share data between services
- Version control your DAGs and notebooks

## Configuration

Copy `.env.example` to `.env` to customize ports, credentials, etc:

```bash
cp .env.example .env
```

The CLI reads `.env` to render service URLs, credentials, and health checks.

### Service env fragments

Each service can include a `services/<service>/env.example` fragment. Generate a
consolidated file with the CLI:

```bash
# Generate a .env for specific services
./ecosystem --profiles postgres,jupyter env --output .env

# Generate a full example for all services
./ecosystem env --output .env.example
```

Shared settings live in `env/common.env` and are included automatically.

## Service Details

### Airflow
- **URL**: http://localhost:8080
- **Credentials**: admin / admin
- **Docker Operator**: Pre-configured, can run containers on the host

### Jupyter
- **URL**: http://localhost:8888
- **Pre-installed**: pandas, numpy, scikit-learn, altair, dbt, SQL magic, and more
- **Database connectors**: PostgreSQL, MySQL, Elasticsearch, Redis

### Metabase
- **URL**: http://localhost:3000
- **First-time setup**: Create admin account, then connect to your database

### Grafana
- **URL**: http://localhost:3001
- **Credentials**: admin / admin

### Connecting Services

All services run on the `analytical-ecosystem` network. Use service names as hostnames:

```python
# From Jupyter, connect to PostgreSQL
%load_ext sql
%sql postgresql://analyticsUser:analyticsPass@postgres:5432/analytics

# Connect to Elasticsearch
from elasticsearch import Elasticsearch
es = Elasticsearch("http://elasticsearch:9200")
```

## Requirements

- Docker and Docker Compose
- Python 3.10+ (for CLI, auto-creates venv on first run)
- Optional: install test dependencies with `pip install -r requirements-dev.txt`

## Future Plans

- Kubernetes orchestration (`orchestration/kubernetes/`)
- Additional services (Superset, Prefect, etc.)
- Pre-built example pipelines

## Development

Run the test suite:

```bash
pytest
```
