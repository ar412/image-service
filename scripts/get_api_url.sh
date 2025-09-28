#!/bin/bash

set -e

STACK_NAME="image-service-stack"
PROFILE="localstack"

API_URL=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[?OutputKey=='ImageServiceApi'].OutputValue" \
  --output text \
  --profile "${PROFILE}" 2>/dev/null)

if [ -z "${API_URL}" ]; then
  echo "Error: Could not find 'ImageServiceApi' output for stack '${STACK_NAME}'. Is it deployed?" >&2
  exit 1
fi

echo "${API_URL}"