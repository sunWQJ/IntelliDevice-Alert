#!/usr/bin/env bash
set -e

NEO4J_CONTAINER=${NEO4J_CONTAINER:-neo4j}
USER=${NEO4J_USER:-neo4j}
PASS=${NEO4J_PASS:-intellidevice123}

docker exec -it "$NEO4J_CONTAINER" cypher-shell -u "$USER" -p "$PASS" "RETURN 1;"

docker exec -it "$NEO4J_CONTAINER" cypher-shell -u "$USER" -p "$PASS" "CREATE CONSTRAINT report_id_unique IF NOT EXISTS FOR (r:Report) REQUIRE r.id IS UNIQUE;"

echo "Neo4j init completed."