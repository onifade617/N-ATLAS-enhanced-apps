#!/usr/bin/env bash
# Render build: install, static files, database schema and reference data.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input

# All 37 states + 774 LGAs and ~55,000 health facilities (both idempotent; fast after the first deploy).
python manage.py load_geography
python manage.py load_facilities

# Demo accounts + synthetic population, only on an empty database (set LAFIYA_SEED_DEMO=0 to skip).
if [ "${LAFIYA_SEED_DEMO:-1}" = "1" ]; then
  python manage.py seed_lafiya --if-empty
fi
