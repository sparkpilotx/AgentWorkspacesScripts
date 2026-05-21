import os

KEEP = ["system", "neo4j"]


def main() -> int:
  from neo4j import GraphDatabase

  driver = GraphDatabase.driver(  # pyright: ignore[reportUnknownMemberType]
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
  )
  try:
    with driver.session(database="system") as session:  # pyright: ignore[reportUnknownMemberType]
      result = session.run("SHOW DATABASES YIELD name")
      names = [record["name"] for record in result if record["name"] not in KEEP]

      for name in names:
        print(f"Dropping: {name}")
        session.run(f"DROP DATABASE `{name}` IF EXISTS").consume()  # pyright: ignore[reportArgumentType] — DDL database names cannot be parameterized

      print("Resetting: neo4j")
      session.run("CREATE OR REPLACE DATABASE neo4j").consume()
  finally:
    driver.close()

  print(f"Done. Dropped {len(names)} databases, reset neo4j.")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
