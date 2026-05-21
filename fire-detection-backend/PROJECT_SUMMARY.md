# Project Summary

## Proje Adi

Fire Detection System

## Amac

NASA FIRMS sicak nokta verilerini kullanarak yangin riski tasiyan bolgeleri tespit etmek ve bu verileri frontend harita/dashboard uzerinde gostermek.

## Ana Bilesenler

- FastAPI backend
- PostgreSQL database
- V3 machine learning model
- NASA FIRMS integration
- Weather feature pipeline
- Scheduler system
- Alert system
- React/Vite frontend
- Docker Compose configuration
- Alembic migration altyapisi

## Ana Akis

```text
NASA FIRMS -> Backend -> Weather Features -> ML Model -> Prediction -> Alert -> Frontend
```

## Guvenlik

Operasyonel endpointler `X-API-Key` ile korunur.

Public endpointler:

- GET /health
- GET /map/status
- GET /map/stats
- GET /map/hotspots
- GET /scheduler/status

Protected endpointler:

- POST /nasa/fetch-hotspots
- POST /scheduler/run-once
- Alert update/delete islemleri
- Weather enrichment islemleri

## Test Sonucu

```text
Backend pytest: 137 passed
Frontend build: passed
```

## Final Durum

Proje final demo ve bitirme projesi sunumu icin hazirdir.
