# Run Knowledge Graph Studio with Docker

Docker Compose builds the React/Nginx and FastAPI/Python images. The optional database services use the official PostgreSQL 16 and Neo4j 5.26 images. Compose connects the containers by service name on its default network.

## 1. Start the stack

Start Docker Desktop with Linux containers, or use Docker Engine with the Compose plugin. Run these commands from the repository root in PowerShell.

```powershell
Set-Location docker
Copy-Item .env.example .env
docker compose --profile postgres --profile neo4j up -d --build
docker compose --profile postgres --profile neo4j ps
Invoke-RestMethod http://127.0.0.1:8080/api/v1/health
```

Open **http://127.0.0.1:8080** and sign in with **admin / admin** for local use. Set `KG_WEB_PORT` in `.env` if you need a different host port. For the built-in sample or CSV uploads, you can start just the app with `docker compose up -d --build`.

After editing or pulling code, use the [rebuild commands in the root README](../README.md#rebuild-after-code-changes).

## 2. Connect PostgreSQL

In the React app, create a session, complete the scope, and choose PostgreSQL on the source screen. With the example environment, enter these values.

| Field | Value |
|---|---|
| Host | `postgres` |
| Port | `5432` |
| Database | `retail` |
| User | `kg_reader` |
| Password | `LOCAL_POSTGRES_READER_PASSWORD` from `docker/.env` |
| Schema | `public` |
| SSL mode | `prefer` |

On first start with an empty volume, PostgreSQL loads the repository's retail sample and `kg_meta` schema, then creates the read-only sample login. After changing the example reader password before first startup, use the new value in the UI and update `PGPASSWORD` if using the CLI. For a populated volume, change the password in PostgreSQL as well.

To keep using an existing database, leave the PostgreSQL profile off and enter your database host and read-only credentials in the UI. For a database listening on your Windows host, use `host.docker.internal` from Docker Desktop. The database must accept connections from Docker. To move an existing database into Docker, restore a compatible PostgreSQL backup into a separate database or volume.

## 3. Connect Neo4j

The example sets the backend URI to `bolt://neo4j:7687`. Once the graph build and validation are complete, enable Neo4j loading when saving a snapshot. For an existing Neo4j instance, leave the Neo4j profile off, set `NEO4J_URI`, `NEO4J_USER` and `NEO4J_PASSWORD` in `docker/.env`, and run `docker compose up -d` to apply them. For a fresh local instance, `LOCAL_NEO4J_PASSWORD` and `NEO4J_PASSWORD` should match. A populated Neo4j volume keeps the credentials already configured in the database.

## 4. Run the CLI or manage the stack

```powershell
docker compose run --rm backend python scripts/run_pipeline.py
docker compose run --rm backend python scripts/run_pipeline.py --csv-dir data/samples/customer360
docker compose --profile postgres --profile neo4j logs --tail=100
docker compose --profile postgres --profile neo4j down
```

The frontend is the only service published to the host. It proxies `/api/v1` to `backend:8000`. Both databases are reachable by the backend over Compose networking. For direct database CLI access, use `docker compose exec postgres psql -U postgres -d retail` or `docker compose exec neo4j cypher-shell -u neo4j`.

Named volumes preserve saved artifacts and database data after `down`. Keep one backend worker because active API sessions and build jobs live in memory and are lost when the backend restarts. Avoid `down -v` unless you intend to delete all three volumes.

Keep `docker/.env` local. Before sharing the stack, replace the sample credentials and JWT signing key. Keep the bcrypt hash single-quoted in `.env` so Compose preserves the dollar signs.
