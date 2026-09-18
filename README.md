# YOOL Connection Forecasting

A Flask dashboard that visualizes platform connection activity and forecasts hourly connection counts for a given day, built on top of a MySQL scheduling database.

## Overview

The platform schedules online courses ("classes"/"meetings") across subjects, levels and time slots. This project pulls that scheduling and enrollment data from MySQL, visualizes historical connection patterns, and trains a model to predict how many connections a given hour of a given day will see — intended to support server-resource planning around expected load.

## Features

- **Dashboard** (`/dashboard`) — daily and hourly connection charts (Plotly.js, Chart.js), served both as a full page and via an AJAX endpoint for the hourly breakdown.
- **Prediction** (`/prediction`) — for a chosen date, predicts the number of connections expected in each hour of the day (7:00–23:00).
- **DB connectivity check** (`/test-db`).

## Data Retrieval & Prediction Workflow

For a given date, `model_prediction.prediction_jour()` queries the MySQL database (joining the course-planning, meeting, subject, level, category and pricing tables) for every scheduled session that day, engineers features from it (level/category/subject/day one-hot encodings, price and duration fields, time-of-day components), and feeds them to a pre-trained XGBoost regressor to predict a connection count per session. Predictions are then aggregated into an hour-by-hour total and rendered on the dashboard/prediction pages.

## Final Model

**XGBoost** (`XGBRegressor`, loaded from `application/xgb_model.joblib`) is the model actually used in this code for hourly connection prediction.

Prophet was evaluated during the project but is not part of this codebase — it is not imported or used anywhere here, and is mentioned only for completeness: it was tried and not carried forward to the final implementation.

## Technologies

Python, Flask, SQLAlchemy + PyMySQL (MySQL), pandas, scikit-learn, XGBoost, joblib, Plotly.js and Chart.js (client-side charting, loaded via CDN in the templates).

## Data

This repository does not include the underlying MySQL database or any real connection/enrollment records. The application expects a MySQL database matching the schema referenced in `application/model_prediction.py` and `application/routes.py`. The historical training extract used to fit the included model is also excluded (`application/yool-v2_train_2.csv` is gitignored) since it contains real course, pricing and connection data.

## Installation

```bash
pip install -r requirements.txt
```

Edit `application/config.json` with your local MySQL connection details:

```json
{
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "yschool_dev",
    "port": 3306
}
```

## Usage

```bash
python run.py
```

## Project Structure

```
application/
├── __init__.py            # Flask app + SQLAlchemy engine setup
├── routes.py               # dashboard, prediction, and DB-check routes
├── data_preprocessing.py   # feature engineering for the prediction model
├── model_prediction.py     # loads xgb_model.joblib and runs hourly predictions
├── xgb_model.joblib         # trained XGBoost regressor
├── config.json              # local MySQL connection settings
├── templates/                # dashboard.html, index.html, prediction.html
└── static/
run.py
requirements.txt
```

## Limitations

No automated tests. No `.env`-based configuration (connection settings are read from `application/config.json`). The prediction model was trained on a specific historical dataset that is not included here, so predictions cannot be reproduced without an equivalent dataset and database.
