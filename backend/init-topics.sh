#!/bin/sh
set -e

BOOTSTRAP_SERVER=${BOOTSTRAP_SERVER:-kafka:9092}

TOPICS=("docs.uploaded" "docs.parsed" "analysis.completed" "draft.created" "draft.rejected" "docs.upload.failed" "docs.parse.failed" "analysis.failed" "user.message")

echo "Waiting for Kafka to be ready at $BOOTSTRAP_SERVER..."
until kafka-topics --bootstrap-server "$BOOTSTRAP_SERVER" --list >/dev/null 2>&1; do
  echo "Kafka not ready yet..."
  sleep 5
done

echo "Kafka is ready. Creating topics..."
for t in "${TOPICS[@]}"; do
  kafka-topics --bootstrap-server "$BOOTSTRAP_SERVER" --create --topic "$t" --if-not-exists --partitions 1 --replication-factor 1
done

echo "All topics created!"
