#!/bin/bash
set -e

# This script runs a TLS-enabled Elasticsearch container in docker
# and uses it as a vector store for similarity search
#
# Usage:
#
#   sh elasticsearch_as_vector_store.sh --tlsEnabled true
#   sh elasticsearch_as_vector_store.sh --tlsEnabled false
#   sh elasticsearch_as_vector_store.sh

ES_IMAGE=docker.elastic.co/elasticsearch/elasticsearch:8.12.0
TLS_ENABLED=false

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
    --tlsEnabled)
      TLS_ENABLED=$2
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
    esac
  done
}

generate_certs() {
  echo "-> Generating CA private key"
  openssl genrsa -out ca.key 2048

  echo "-> Creating a self-signed CA certificate"
  openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt -subj "/CN=MyCA"

  echo "-> Generating Elasticsearch server private key"
  openssl genrsa -out server.key 2048

  echo "-> Creating a server CSR (Certificate Signing Request)"
  openssl req -new -key server.key -out server.csr -subj "/CN=localhost"

  echo "-> Signing the server certificate with generated CA"
  openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 365 -sha256
}

start_es() {
  ES_PASSWORD=$(openssl rand -base64 24)
  if [[ "$TLS_ENABLED" == "true" ]]; then
    echo "Generating TLS certs.."
    generate_certs
    chmod 644 server.key server.crt ca.crt

    echo -e "\nStarting Elasticsearch with TLS..."
    docker run -d \
      --name "es-with-tls" \
      -p 9200:9200 \
      -e "discovery.type=single-node" \
      -e "xpack.security.enabled=true" \
      -e "ELASTIC_PASSWORD=$ES_PASSWORD" \
      -e "xpack.security.http.ssl.enabled=true" \
      -e "xpack.security.http.ssl.key=/usr/share/elasticsearch/config/server.key" \
      -e "xpack.security.http.ssl.certificate=/usr/share/elasticsearch/config/server.crt" \
      -e "xpack.security.http.ssl.certificate_authorities=/usr/share/elasticsearch/config/ca.crt" \
      -v "./server.key:/usr/share/elasticsearch/config/server.key" \
      -v "./server.crt:/usr/share/elasticsearch/config/server.crt" \
      -v "./ca.crt:/usr/share/elasticsearch/config/ca.crt" \
      $ES_IMAGE
  else
    echo "Starting Elasticsearch without TLS..."
    docker run -d \
      --name "es-without-tls" \
      -p 9200:9200 \
      -e "discovery.type=single-node" \
      -e "xpack.security.enabled=true" \
      -e "ELASTIC_PASSWORD=$ES_PASSWORD" \
      $ES_IMAGE
  fi
}

generate_api_key() {
  METHOD="POST"
  URL="_security/api_key"
  DATA='{
      "name": "my-vector-store-api-key",
      "expiration": "1d"
    }'

  echo -e "\nGenerating Elasticsearch API key..."
  if [[ "$TLS_ENABLED" == "true" ]]; then
    RESPONSE=$(
      curl --cacert ca.crt \
        -u elastic:$ES_PASSWORD \
        -X "$METHOD" "https://localhost:9200/$URL" \
        -H "Content-Type: application/json" \
        -d "$DATA"
    )
  else
    RESPONSE=$(
      curl \
        -u elastic:$ES_PASSWORD \
        -X "$METHOD" "http://localhost:9200/$URL" \
        -H "Content-Type: application/json" \
        -d "$DATA"
    )
  fi

  API_KEY=$(echo "$RESPONSE" | jq -r '.encoded')
}

es_curl() {
  METHOD="$1"
  URL="$2"
  DATA="$3"

  if [[ "$TLS_ENABLED" == "true" ]]; then
    curl --cacert ca.crt \
      -X "$METHOD" "https://localhost:9200/$URL" \
      -H "Authorization: ApiKey $API_KEY" \
      -H "Content-Type: application/json" \
      -d "$DATA"
  else
    curl \
      -X "$METHOD" "http://localhost:9200/$URL" \
      -H "Authorization: ApiKey $API_KEY" \
      -H "Content-Type: application/json" \
      -d "$DATA"
  fi
}

create_es_index() {
  echo -e "\nCreating index..."
  es_curl PUT "my-vector-store-index" '{
    "mappings": {
      "properties": {
        "text": { "type": "text" },
        "embedding": {
          "type": "dense_vector",
          "dims": 3,
          "index": true,
          "similarity": "cosine"
        }
      }
    }
  }'
}

insert_vectors_in_index() {
  echo -e "\n\nInserting vectors in index..."
  es_curl POST "my-vector-store-index/_doc/1" '{
    "text":"Hello world",
    "embedding":[0.1,0.2,0.3]
  }'
  es_curl POST "my-vector-store-index/_doc/2" '{
    "text":"Machine learning",
    "embedding":[0.2,0.1,0.0]
  }'
}

run_search() {
  echo -e "\n\nRunning vector search..."
  es_curl POST "my-vector-store-index/_search" '{
    "knn": {
      "field": "embedding",
      "query_vector": [0.1, 0.2, 0.25],
      "k": 2,
      "num_candidates": 100
    }
  }'
}

main() {
  parse_args "$@"
  start_es
  sleep 20

  generate_api_key
  create_es_index
  insert_vectors_in_index
  sleep 2

  run_search
  echo -e "\n"
}

main "$@"
