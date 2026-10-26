# Environmental Pollution Prediction and Monitoring System

## About the Project

This is a final-year project focused on environmental pollution prediction and monitoring using machine learning and data analysis. It focuses on air quality, water quality, and soil fertility.

The system combines a Python backend with a web interface to present environmental data and prediction results.

## Key Features

- Air quality prediction and monitoring
- Water quality classification
- Soil fertility classification
- Machine learning-based predictions
- Air quality forecasting
- Database storage of prediction results
- Live environmental data and IoT monitoring features

## Technologies Used

- **Programming Language:** Python
- **Backend:** Flask
- **Frontend:** HTML, CSS, JavaScript
- **Machine Learning:** XGBoost, Prophet
- **Explainable AI:** SHAP
- **Data Analysis:** Pandas, Jupyter Notebook
- **Database:** SQLite

## Project Structure

- `backend/` – Flask application, API routes, database operations, and forecasting
- `frontend/` – Web pages, styling, and JavaScript
- `data/` – Raw and processed environmental datasets
- `models/` – Trained machine learning models
- `Notebooks/` – Data exploration, preprocessing, and model development

## Getting Started

### Prerequisites

- Python
- pip
- The required Python packages
- Any required API credentials for live data collection

### Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/Madushika23/environmental-pollution-prediction-monitoring.git
   ```

2. Open the project directory and move into the backend folder:

   ```bash
   cd environmental-pollution-prediction-monitoring/backend
   ```

3. Install the required packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Configure the required environment variables locally. Do not upload API keys or passwords to GitHub.

5. Start the application:

   ```bash
   python app.py
   ```

6. Open the application in your browser:

   http://127.0.0.1:5000

## Project Status

The initial source code, datasets, notebooks, and trained models have been uploaded. Testing, documentation, and further improvements will continue as development progresses.

## Disclaimer

This project is intended for educational and research purposes. Prediction results should be validated before being used for real-world environmental decisions.
