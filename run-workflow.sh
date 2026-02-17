#!/bin/bash

workflow_type="$1"
case "$workflow_type" in
java | llm | python | sql)
  INPUTS="{\"filename\":\"$2\"}"
  ;;
sh)
  INPUTS="{\"filename\":\"$2\",\"arguments\":\"$3\"}"
  ;;
spark)
  INPUTS="{\"language\":\"$2\",\"filename\":\"$3\"}"
  ;;
*)
  echo "Invalid value for workflow type."
  exit 1
  ;;
esac

curl -X POST \
  -H "Accept: application/vnd.github+json" \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_REPOSITORY/actions/workflows/run-${workflow_type}.yml/dispatches" \
  -d "{\"ref\":\"master\",\"inputs\":$INPUTS}"
