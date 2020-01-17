#!/usr/bin/env bash
set -eu

source .env/bin/activate
exec "$@"
