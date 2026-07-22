#!/usr/bin/env bash
# Generate the typed Angular API client from the backend OpenAPI spec.
# By default it reads the committed spec (frontend/openapi.json) so it works
# offline; pass a URL to regenerate from a running backend, e.g.:
#   ./gen-api.sh http://localhost:8000/openapi.json
set -euo pipefail
SPEC="${1:-openapi.json}"
npx openapi-generator-cli generate \
  -i "$SPEC" \
  -g typescript-angular \
  -o src/app/core/api \
  --additional-properties=ngVersion=18.0.0,providedInRoot=true,withInterfaces=true
