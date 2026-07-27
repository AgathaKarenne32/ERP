#!/bin/bash
# Cria o segundo banco (anotaai) no mesmo container Postgres.
# O banco 'ecletica' já é criado automaticamente pela imagem via POSTGRES_DB.
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE anotaai;
EOSQL
