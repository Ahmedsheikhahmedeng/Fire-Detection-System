#!/bin/bash

set -e

export TEST_DATABASE_URL="postgresql://deneme:@localhost:5432/fire_detection_test"

echo "Running backend test suite..."
python -m pytest tests -q

echo "Running coverage..."
python -m pytest tests --cov=app --cov-report=term-missing
