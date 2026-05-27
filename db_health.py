import os
import sys
from collections.abc import Callable
from urllib.parse import urljoin

_NEO4J_ENV_VARS = ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD")
_PG_ENV_VARS = ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD")
_INFLUXDB_ENV_VARS = ("INFLUXDB3_HOST_URL", "INFLUXDB3_AUTH_TOKEN")

# Ubuntu 24.04 only has Neo4j; macOS has all three.
_ON_LINUX = sys.platform == "linux"

REQUIRED_ENV_VARS = (
  _NEO4J_ENV_VARS
  if _ON_LINUX
  else (
    *_NEO4J_ENV_VARS,
    *_PG_ENV_VARS,
    *_INFLUXDB_ENV_VARS,
  )
)


def validate_environment() -> None:
  missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
  if not missing:
    return

  print("Missing required environment variables:", file=sys.stderr)
  for name in missing:
    print(f"  {name}", file=sys.stderr)
  raise SystemExit(2)


def check_neo4j() -> tuple[str, str, str]:
  from neo4j import GraphDatabase

  driver = GraphDatabase.driver(  # pyright: ignore[reportUnknownMemberType]
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
  )
  try:
    with driver.session(database="neo4j") as session:  # pyright: ignore[reportUnknownMemberType]
      record = session.run("RETURN 1 AS ok").single()
      if record is None or record["ok"] != 1:
        raise RuntimeError("Neo4j health query returned no result")
  finally:
    driver.close()

  return ("Neo4j", "OK", "RETURN 1 on database neo4j")


def check_postgresql() -> tuple[str, str, str]:
  import psycopg

  with (
    psycopg.connect(
      host=os.environ["PGHOST"],
      port=os.environ["PGPORT"],
      user=os.environ["PGUSER"],
      password=os.environ["PGPASSWORD"],
      dbname="postgres",
      connect_timeout=10,
    ) as conn,
    conn.cursor() as cur,
  ):
    cur.execute("SELECT 1")
    cur.fetchone()

  return ("PostgreSQL", "OK", "SELECT 1 on database postgres")


def check_influxdb() -> tuple[str, str, str]:
  import requests

  url = urljoin(os.environ["INFLUXDB3_HOST_URL"].rstrip("/") + "/", "health")
  response = requests.get(
    url,
    headers={"Authorization": f"Bearer {os.environ['INFLUXDB3_AUTH_TOKEN']}"},
    timeout=10,
  )
  if response.status_code >= 400:
    raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")

  return ("InfluxDB", "OK", f"health endpoint HTTP {response.status_code}")


def run_check(name: str, check: Callable[[], tuple[str, str, str]]) -> tuple[str, str, str]:
  try:
    return check()
  except Exception as exc:
    return (name, "FAIL", f"{type(exc).__name__}: {exc}")


def main() -> int:
  validate_environment()

  checks: list[tuple[str, Callable[[], tuple[str, str, str]]]] = [
    ("Neo4j", check_neo4j),
  ]
  if not _ON_LINUX:
    checks += [
      ("PostgreSQL", check_postgresql),
      ("InfluxDB", check_influxdb),
    ]

  results = [run_check(name, check) for name, check in checks]

  for name, status, detail in results:
    print(f"{name}: {status} - {detail}")

  return 0 if all(status == "OK" for _, status, _ in results) else 1


if __name__ == "__main__":
  raise SystemExit(main())
