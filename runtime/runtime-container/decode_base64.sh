#!/bin/bash
set -e

if [ -z "$ZIP_BASE64" ]; then
  echo "Erro: A variável de ambiente ZIP_BASE64 não está definida."
  exit 1
fi

if [ -z "$ZIP_FILE_PATH" ]; then
  echo "Erro: A variável de ambiente ZIP_FILE_PATH não está definida."
  exit 1
fi

echo "Decodificando o arquivo ZIP..."
echo "$ZIP_BASE64" | base64 -d > "$ZIP_FILE_PATH"

echo "Arquivo ZIP decodificado salvo em $ZIP_FILE_PATH."

exec "$@"
