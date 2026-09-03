<div align="center">

<img src="logo.png" alt="Fire Detection System Logo" width="180"/>

# 🔥 Fire Detection System

### NASA FIRMS Satellite Data & Machine Learning Powered Wildfire Early Warning and Risk Monitoring System

<p>
  <strong>AI / Machine Learning</strong> ·
  <strong>FastAPI</strong> ·
  <strong>React</strong> ·
  <strong>PostgreSQL</strong> ·
  <strong>Docker</strong>
</p>

[![React](https://img.shields.io/badge/React-19.2-61DAFB?logo=react\&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi\&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python\&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Ready-4169E1?logo=postgresql\&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker\&logoColor=white)](https://www.docker.com/)
[![ML](https://img.shields.io/badge/ML-LightGBM%20%7C%20CatBoost%20%7C%20XGBoost-orange)](https://scikit-learn.org/)

</div>

---

# 🎥 Project Demo

<p align="center">
  <a href="https://youtu.be/QJBz3zF7Pl4">
    <img src="https://img.youtube.com/vi/QJBz3zF7Pl4/maxresdefault.jpg" alt="Fire Detection System Demo" width="850">
  </a>
</p>

<p align="center">
  <a href="https://youtu.be/QJBz3zF7Pl4">
    ▶️ <strong>Watch the Full Project Demo</strong>
  </a>
</p>

---

# 📖 About The Project

**Fire Detection System** is an end-to-end AI-powered wildfire risk monitoring and early warning platform developed as an academic graduation project.

The system combines:

* 🛰️ NASA FIRMS satellite hotspot data
* 🌦️ Meteorological and Fire Weather Index (FWI) data
* 🧠 Machine Learning ensemble models
* 🗄️ PostgreSQL
* ⚡ FastAPI
* ⚛️ React
* 🗺️ Interactive geospatial visualization
* 🚨 Automated risk alerts
* 🐳 Docker-based deployment

The platform collects satellite hotspot observations, enriches them with weather and fire-danger features, processes them through trained machine learning models, and generates a **fire-risk probability for each detected location**.

The resulting predictions are exposed through a REST API and visualized through a modern web interface with interactive maps, dashboards, risk analysis and dynamic alerts.

---

# 🌟 Key Features

### 🛰️ NASA FIRMS Satellite Integration

The system periodically collects hotspot observations from **NASA FIRMS**.

Supported VIIRS sources include:

* VIIRS Suomi NPP
* VIIRS NOAA-20
* VIIRS NOAA-21

The collected hotspot observations form the primary satellite-based input of the prediction pipeline.

---

### 🌦️ Weather & Fire Weather Analysis

Satellite observations are enriched with environmental and meteorological information, including:

* Temperature
* Relative humidity
* Wind speed
* Fire Weather Index (FWI)
* Drought-related indicators
* Temporal features

This allows the ML pipeline to evaluate both satellite signals and environmental conditions associated with wildfire risk.

---

### 🧠 Multi-Tier Ensemble Machine Learning

Instead of relying on a single classifier, the final V3 architecture uses multiple trained models with different roles.

| Model                 | Role                     |
| --------------------- | ------------------------ |
| **LightGBM**          | Primary Watch            |
| **CatBoost**          | Holdout-best Alternative |
| **Boosting Ensemble** | Stable Prediction Layer  |
| **Random Forest**     | Balanced Verifier        |
| **ExtraTrees**        | Strict Verifier          |

This multi-tier architecture provides multiple levels of prediction and verification before producing high-confidence alerts.

---

### 🗺️ Real-Time Monitoring

The React frontend provides an interactive monitoring environment where users can:

* View active hotspot locations
* Inspect wildfire risk levels
* Analyze individual locations
* Monitor high-risk areas
* View active alerts
* Explore geospatial data through an interactive map
* Monitor system statistics

---

### 🚨 Dynamic Risk Alerts

High-risk and critical-risk locations can generate dynamic alerts within the monitoring interface.

This allows potentially dangerous areas to be highlighted without requiring users to manually inspect every hotspot.

---

### 🎨 Modern Interactive UI

The frontend uses modern animation and visualization technologies including:

* GSAP
* ScrollTrigger
* Framer Motion
* Lenis
* Leaflet
* Recharts
* Tailwind CSS

The result is a responsive interface designed for desktop, tablet and mobile devices.

---

### 🐳 Containerized Deployment

The application supports Docker-based development and production environments.

The full system can run with:

```text
Frontend
Backend
PostgreSQL
Scheduler / Worker
```

using Docker Compose.

---

# 🧠 Machine Learning Pipeline

The ML research environment contains an **18-stage data science and machine learning development pipeline**.

The workflow covers:

```text
Raw Satellite Data
        ↓
Data Cleaning
        ↓
Exploratory Analysis
        ↓
Feature Engineering
        ↓
Weather + FWI Enrichment
        ↓
Model Training
        ↓
Model Evaluation
        ↓
External Testing
        ↓
V2 → V3 Improvements
        ↓
Ensemble Models
        ↓
Final Model Artifacts
```

---

# 📊 Dataset

The model was trained using historical wildfire-related observations from **Greece**.

| Property               |      Value |
| ---------------------- | ---------: |
| Total Samples          | **12,397** |
| Features               |    **101** |
| Missing Values         |      **0** |
| Core Features          |     **44** |
| Weather & FWI Features |     **57** |

### Feature Distribution

#### 44 Core Features

Includes:

* NASA FIRMS sensor measurements
* FRP
* Brightness
* Spatial features
* Hotspot density
* Cluster information
* Date and time features

#### 57 Weather & FWI Features

Includes:

* Temperature
* Wind
* Humidity
* Fire Weather Index components
* Drought indicators
* Meteorological variables

---

# 🔬 Model Evolution — V2 → V3

One of the most important parts of the project was the transition from **V2 to V3**.

## V2 External Evaluation

After training, V2 was evaluated on an unseen **2022 external test dataset**.

The model successfully captured the general wildfire pattern, but performance dropped significantly during low-fire seasons.

The most challenging periods included:

* October
* November
* February

Recall during these periods was approximately:

### **36%**

This indicated that the model was missing a significant number of wildfire cases during low-season periods.

---

# 🚀 V3 Improvements

Several improvements were introduced to address the weaknesses identified in V2.

## 1. Sample Weighting

2022 wildfire observations were analyzed according to coordinate quality.

Higher-confidence observations such as:

```text
exact_coord_2km_24h
```

were treated differently from approximate observations.

Selected low-season wildfire samples were given additional importance during training.

Example:

```text
Low-season wildfire samples
            ↓
       1.25× weight
```

---

## 2. Hard Negative Samples

Difficult negative examples were introduced to improve the model's ability to distinguish between:

```text
Potential Wildfire Signal
        vs.
Non-Wildfire / False Positive Signal
```

This was intended to reduce unnecessary false alarms.

---

## 3. External Validation

The previously unseen 2022 dataset was used as an important evaluation reference during the V3 development process.

This helped identify weaknesses that were not obvious from standard training and validation results.

---

# 📈 V2 vs V3 Results

A significant improvement was observed on the evaluated 2022 data.

| Model  | 2022 F1 Score |
| ------ | ------------: |
| **V2** |          ~37% |
| **V3** |          ~87% |

### Result

**The V3 development process increased the evaluated F1 Score from approximately 37% to 87%.**

The improvement was achieved through a combination of:

* Sample weighting
* Low-season wildfire handling
* Hard negative samples
* Feature engineering
* External validation
* Multi-model ensemble architecture

> **Note:** These performance values refer specifically to the evaluated 2022 external test setup used during the project's model development process.

---

# 🏗️ System Architecture

The system follows an end-to-end data processing and inference architecture:

```text
                    ┌─────────────────────┐
                    │     NASA FIRMS      │
                    │   Satellite Data    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Data Collection   │
                    │      Service        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Weather / FWI Data  │
                    │   Enrichment Layer  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Feature Engineering │
                    │    101 Features     │
                    └──────────┬──────────┘
                               │
                               ▼
             ┌──────────────────────────────────┐
             │        V3 ML Prediction          │
             │                                  │
             │ LightGBM · CatBoost · Ensemble  │
             │ Random Forest · ExtraTrees       │
             └────────────────┬─────────────────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   Risk Probability  │
                    │     & Risk Level    │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
          ┌─────────────────┐   ┌─────────────────┐
          │   PostgreSQL    │   │    FastAPI      │
          │    Database     │   │      API        │
          └─────────────────┘   └────────┬────────┘
                                         │
                                         ▼
                              ┌─────────────────────┐
                              │   React Frontend    │
                              │                     │
                              │ Map · Dashboard     │
                              │ Analysis · Alerts   │
                              └─────────────────────┘
```

---

# 🧩 Technology Stack

## 🎨 Frontend

* React 19
* Vite
* Tailwind CSS v4
* GSAP
* GSAP ScrollTrigger
* Framer Motion
* Leaflet
* React-Leaflet
* Recharts
* Axios
* React Router
* Lenis
* Lucide React

## ⚙️ Backend

* Python 3.11+
* FastAPI
* Uvicorn
* SQLAlchemy
* Alembic
* PostgreSQL
* Psycopg2
* Pydantic

## 🤖 Machine Learning

* Scikit-learn
* XGBoost
* LightGBM
* CatBoost
* Pandas
* NumPy
* Joblib

## 🌍 Data Sources

* NASA FIRMS
* Open-Meteo
* Meteorological / FWI data

## 🐳 Infrastructure

* Docker
* Docker Compose
* Nginx
* APScheduler
* Pytest

---

# 🖥️ Frontend

The frontend acts as the user-facing operational monitoring layer.

### Main Pages

```text
/
├── Home
│
├── /analiz
│   └── Fire Analysis
│
└── /izleme
    └── Monitoring Center
```

### Frontend Structure

```text
src/

├── assets/
├── components/
├── pages/
│   ├── AlertCenter/
│   ├── Awareness/
│   ├── FireAnalysis/
│   ├── FireDashboard/
│   ├── Home/
│   └── Monitoring/
├── services/
├── styles/
├── utils/
├── App.jsx
└── main.jsx
```

---

# ⚙️ Backend

The backend is responsible for data collection, processing, ML inference, database operations and API services.

Main responsibilities include:

1. Collecting NASA FIRMS data
2. Fetching meteorological data
3. Enriching hotspot observations
4. Performing feature engineering
5. Running ML inference
6. Creating hotspot clusters
7. Storing operational data
8. Generating risk alerts
9. Serving frontend requests through REST APIs

---

# ⏱️ Scheduler / Worker Architecture

Periodic background tasks are handled through a separate scheduler/worker service.

Typical workflow:

```text
NASA FIRMS
    ↓
Hotspot Collection
    ↓
Weather Enrichment
    ↓
Feature Engineering
    ↓
ML Prediction
    ↓
Clustering
    ↓
Database Update
    ↓
Alert Generation
```

The scheduler uses **APScheduler** for periodic jobs.

---

# 🗺️ Hotspot Clustering

Nearby hotspot observations can be grouped into **fire clusters** based on spatial proximity and a defined time window.

The clustering layer helps:

* Reduce duplicate observations
* Reduce alert noise
* Group nearby hotspot signals
* Improve operational monitoring
* Simplify map visualization

---

# 🚨 Risk & Alert System

ML predictions are converted into risk levels that can be displayed through the monitoring interface.

Example levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

High and critical risk locations are prioritized within the monitoring interface.

---

# 🔌 REST API

The backend provides REST APIs through FastAPI.

Swagger UI:

```text
http://localhost:8000/docs
```

### Public Endpoints

| Endpoint             | Description                   |
| -------------------- | ----------------------------- |
| `GET /health`        | System health status          |
| `GET /map/hotspots`  | Active hotspot/risk locations |
| `GET /alerts/active` | Active alerts                 |

### Protected Endpoints

Protected operational endpoints require:

```text
X-API-Key: {API_KEY}
```

| Endpoint                          | Description                   |
| --------------------------------- | ----------------------------- |
| `POST /nasa/fetch-hotspots`       | Fetch NASA hotspot data       |
| `POST /scheduler/run-once`        | Trigger the pipeline manually |
| `POST /api/ml/predict-engineered` | Run ML prediction             |

---

# 🧪 Testing

The backend includes an automated **Pytest** test suite.

At the project delivery stage:

### **141+ tests passed successfully**

Run the tests with:

```bash
cd fire-detection-backend
pytest
```

---

# 🐳 Docker Deployment

The project supports both development and production environments.

## Development

```bash
cd fire-detection-backend

cp .env.example .env

docker compose -p fire-dev up -d --build
```

To start the scheduler:

```bash
docker compose \
  -p fire-dev \
  --profile scheduler \
  up -d --build
```

Services:

```text
Frontend    → 5173
Backend     → 8000
PostgreSQL  → 5432
```

Swagger:

```text
http://localhost:8000/docs
```

---

# 🚀 Production

Production deployment uses a separate Docker Compose configuration.

```bash
cp .env.production.example .env.production
```

Then:

```bash
docker compose \
  -p fire-prod \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  up -d --build
```

The production configuration includes:

* Nginx frontend serving
* Production backend configuration
* PostgreSQL
* Scheduler / Worker
* ML artifact validation
* No development reload mode
* Non-root application execution

---

# 🔐 Environment Variables

Configuration and secrets are managed through environment variables.

Example:

```env
DB_USER=
DB_PASSWORD=
DB_NAME=

NASA_API_KEY=
API_KEY=

OPENWEATHER_API_KEY=
```

> ⚠️ Never commit real API keys, passwords or credentials to the repository.

---

# 🤖 ML Model Artifacts

The final V3 models are exported as `.joblib` artifacts.

The final model architecture contains:

```text
final_models_v3/

├── LightGBM
├── CatBoost
├── Boosting Ensemble
├── Random Forest
└── ExtraTrees
```

Due to their size, trained model artifacts may be excluded from the Git repository.

The backend provides an artifact validation script:

```bash
python scripts/check_model_artifacts.py
```

---

# 📁 Repository Structure

```text
bitirmeprojesifull/

├── bitirmeprojesi_frontend/
│   └── React + Vite Frontend
│
├── fire-detection-backend/
│   └── FastAPI + PostgreSQL + ML Backend
│
├── docker-compose.prod.yml
├── TESLIM_DOKUMANTASYONU.md
├── start.sh
└── README.md
```

The ML research and development environment is maintained separately and contains the V2 → V3 experimentation and model development pipeline.

---

# 🚀 Quick Start

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd bitirmeprojesifull
```

Configure the backend:

```bash
cd fire-detection-backend
cp .env.example .env
```

Start the development environment:

```bash
docker compose -p fire-dev up -d --build
```

Start the scheduler:

```bash
docker compose \
  -p fire-dev \
  --profile scheduler \
  up -d --build
```

---

# 🎯 Project Goals

The main goal of this project is not simply to build an ML classifier, but to create an **end-to-end wildfire risk monitoring and early warning platform**.

The complete workflow can be summarized as:

```text
Satellite Data
      ↓
Weather Data
      ↓
Feature Engineering
      ↓
Machine Learning
      ↓
Risk Analysis
      ↓
Database
      ↓
REST API
      ↓
Interactive Map
      ↓
Monitoring
      ↓
Alerts
```

---

# 💡 Key Technical Highlights

This project demonstrates practical experience with:

* 🧠 Machine Learning model development
* 🔬 V2 → V3 model optimization
* 📊 Feature Engineering
* ⚖️ Sample Weighting
* 🎯 Hard Negative Samples
* 🛰️ NASA FIRMS integration
* 🌦️ Meteorological data enrichment
* 🗺️ Geospatial visualization
* 🔥 Hotspot clustering
* ⚡ FastAPI REST APIs
* 🗄️ PostgreSQL
* ⏱️ Background workers and scheduling
* 🧪 Automated testing
* 🐳 Docker & Docker Compose
* 🔐 API Key based endpoint protection
* ⚛️ React frontend development
* 🎨 GSAP / ScrollTrigger animations

---

# 🔮 Future Improvements

Possible future improvements include:

* Larger multi-year training datasets
* Additional satellite data sources
* More advanced temporal models
* Advanced geospatial features
* Real-time notification channels
* Cloud deployment
* Horizontal scaling
* Broader external validation across different geographic regions

---

# 📜 License

This project was developed as an **academic graduation project**.

It is intended for educational and research purposes.

Unauthorized commercial use is not permitted.

---

<div align="center">

# 🔥 Fire Detection System

### Satellite Data · Artificial Intelligence · Real-Time Monitoring · Early Warning

**Developed as an Academic Graduation Project**

</div>
