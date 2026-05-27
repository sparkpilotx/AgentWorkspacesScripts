# Initialize AgentWorkspaces isolated Codex environment and shared auth
init-codex:
    @./init-codex.sh

# Check connectivity to Neo4j, PostgreSQL, and InfluxDB
db-health:
    uv run db_health.py

# Drop all non-system Neo4j databases and reset the default neo4j database
reset-neo4j:
    uv run reset_neo4j.py

# Test the Neo4j GenAI plugin (embedding, vector index, similarity search)
test-genai:
    uv run test_genai.py

# Run format, lint, and typecheck in order
check: format lint typecheck

# Lint all scripts
lint:
    uv run --group dev ruff check .

# Format all scripts
format:
    uv run --group dev ruff format .

# Type-check all scripts
typecheck:
    uv run --group dev pyright
