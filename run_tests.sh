#!/bin/bash

# Start testing db container
docker run -d --rm \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=postgres \
            -e POSTGRES_DB=postgres \
            -p 5433:5432 \
            --name postgres \
            postgres:15
exit_code=$?

sleep 2

if [[ $exit_code -eq 0 ]]; then
    # Run all tests
    #DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres pytest
    # Run selected tests (just like github actions)
    #DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres pytest -m "integration" --strict-markers --cov=src tests/ --cov-report=xml
    DATABASE_URL=postgresql://postgres:postgres@localhost:5433/postgres poetry run pytest -m "integration" --strict-markers --cov=src tests/ --cov-report=xml

else
    echo "Error al iniciar el contenedor de db para tests."
fi