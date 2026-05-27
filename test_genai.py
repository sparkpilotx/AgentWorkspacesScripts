"""Test the Neo4j GenAI plugin (ai.text.* procedures) using OpenAI embeddings.

Exercises:
  1. List embedding providers via ai.text.embed.providers
  2. Encode a batch of texts via ai.text.embedBatch (OpenAI)
  3. Create a vector index and store embeddings as node properties
  4. Query by vector similarity (cosine) and verify ranked results
"""

import contextlib
import os
import sys
from typing import Any

_REQUIRED = (
  "NEO4J_URI",
  "NEO4J_USER",
  "NEO4J_PASSWORD",
  "OPENAI_API_KEY",
  "OPENAI_TEXT_EMBEDDING_MODEL",
)

_SAMPLE_TEXTS = [
  "Neo4j is a native graph database built for connected data.",
  "PostgreSQL is a powerful open-source relational database.",
  "Vector embeddings represent semantic meaning as numerical arrays.",
  "Cypher is the query language used to interact with Neo4j.",
  "Machine learning models learn patterns from large datasets.",
]

_QUERY_TEXT = "How do I query a graph database?"

_INDEX_NAME = "genai_test_idx"
_LABEL = "GenaiTestDoc"


def _validate_env() -> None:
  missing = [v for v in _REQUIRED if not os.environ.get(v)]
  if missing:
    print("Missing environment variables:", ", ".join(missing), file=sys.stderr)
    raise SystemExit(2)


def _driver() -> Any:
  from neo4j import GraphDatabase  # pyright: ignore[reportMissingTypeStubs]

  return GraphDatabase.driver(  # pyright: ignore[reportUnknownMemberType]
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
  )


def test_list_providers() -> None:
  print("--- 1. List embedding providers ---")
  drv = _driver()
  try:
    with drv.session(database="neo4j") as s:  # pyright: ignore[reportUnknownMemberType]
      rows = s.run("CALL ai.text.embed.providers()").data()
    names = [r["name"] for r in rows]
    assert "OpenAI" in names, f"OpenAI not in providers: {names}"
    print(f"  providers: {names}")
    print("  PASS\n")
  finally:
    drv.close()


def test_embed_batch() -> list[list[float]]:
  print("--- 2. Embed batch via ai.text.embedBatch (OpenAI) ---")
  token = os.environ["OPENAI_API_KEY"]
  model = os.environ["OPENAI_TEXT_EMBEDDING_MODEL"]
  drv = _driver()
  try:
    with drv.session(database="neo4j") as s:  # pyright: ignore[reportUnknownMemberType]
      rows = s.run(
        "CALL ai.text.embedBatch($texts, 'OpenAI', {token: $token, model: $model})",
        texts=_SAMPLE_TEXTS,
        token=token,
        model=model,
      ).data()
  finally:
    drv.close()

  assert len(rows) == len(_SAMPLE_TEXTS), f"Expected {len(_SAMPLE_TEXTS)} rows, got {len(rows)}"
  ordered = sorted(rows, key=lambda r: r["index"])
  vectors: list[list[float]] = []
  for r in ordered:
    vec: list[float] = r["vector"].to_native()
    assert len(vec) > 0, "Empty vector returned"
    vectors.append(vec)

  print(f"  embedded {len(vectors)} texts, dimension={len(vectors[0])}")
  print("  PASS\n")
  return vectors


def test_vector_index_and_search(vectors: list[list[float]]) -> None:
  print("--- 3. Store embeddings and create vector index ---")
  dim = len(vectors[0])
  token = os.environ["OPENAI_API_KEY"]
  model = os.environ["OPENAI_TEXT_EMBEDDING_MODEL"]
  drv = _driver()
  try:
    with drv.session(database="neo4j") as s:  # pyright: ignore[reportUnknownMemberType]
      # Clean up from any previous run
      s.run(f"MATCH (n:{_LABEL}) DETACH DELETE n")
      with contextlib.suppress(Exception):
        s.run(f"DROP INDEX {_INDEX_NAME}")

      # Create nodes with embeddings
      for text, vec in zip(_SAMPLE_TEXTS, vectors, strict=True):
        s.run(
          f"CREATE (:{_LABEL} {{text: $text, embedding: $vec}})",
          text=text,
          vec=vec,
        )
      print(f"  created {len(_SAMPLE_TEXTS)} :{_LABEL} nodes")

      # Create vector index
      s.run(f"""
        CREATE VECTOR INDEX {_INDEX_NAME}
        FOR (n:{_LABEL}) ON (n.embedding)
        OPTIONS {{indexConfig: {{`vector.dimensions`: {dim}, `vector.similarity_function`: 'cosine'}}}}
      """)
      print(f"  created vector index '{_INDEX_NAME}' (dim={dim}, cosine)")

      # Wait for index to come online
      for _ in range(20):
        status = s.run(
          "SHOW INDEXES YIELD name, state WHERE name = $name RETURN state",
          name=_INDEX_NAME,
        ).single()
        if status and status["state"] == "ONLINE":
          break
        import time

        time.sleep(0.5)
      print("  index is ONLINE")

    print("--- 4. Semantic similarity search ---")
    with drv.session(database="neo4j") as s:  # pyright: ignore[reportUnknownMemberType]
      # Embed the query text
      query_rows = s.run(
        "CALL ai.text.embedBatch($texts, 'OpenAI', {token: $token, model: $model})",
        texts=[_QUERY_TEXT],
        token=token,
        model=model,
      ).data()
      query_vec: list[float] = query_rows[0]["vector"].to_native()

      # Search by vector similarity
      results = s.run(
        f"""
        MATCH (n:{_LABEL})
        SEARCH n IN (VECTOR INDEX {_INDEX_NAME} FOR $vec LIMIT 3)
        SCORE AS score
        RETURN n.text AS text, score
        ORDER BY score DESC
        """,
        vec=query_vec,
      ).data()

    print(f"  query: '{_QUERY_TEXT}'")
    print("  top matches:")
    for i, r in enumerate(results, 1):
      print(f"    {i}. [{r['score']:.4f}] {r['text']}")

    # The Neo4j or Cypher text should rank highest for a graph DB query
    top_text = results[0]["text"].lower()
    assert "neo4j" in top_text or "cypher" in top_text or "graph" in top_text, (
      f"Unexpected top result: {results[0]['text']}"
    )
    print("  PASS\n")

    # Cleanup
    with drv.session(database="neo4j") as s:  # pyright: ignore[reportUnknownMemberType]
      s.run(f"MATCH (n:{_LABEL}) DETACH DELETE n")
      s.run(f"DROP INDEX {_INDEX_NAME}")
    print("  cleaned up test nodes and index")

  finally:
    drv.close()


def main() -> int:
  _validate_env()
  print(f"Neo4j GenAI plugin test — model: {os.environ['OPENAI_TEXT_EMBEDDING_MODEL']}\n")
  try:
    test_list_providers()
    vectors = test_embed_batch()
    test_vector_index_and_search(vectors)
    print("All tests PASSED.")
    return 0
  except AssertionError as exc:
    print(f"FAIL: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
  raise SystemExit(main())
