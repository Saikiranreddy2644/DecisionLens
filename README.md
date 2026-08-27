# DecisionLens

DecisionLens is an AI-assisted retail analytics and investigation system designed to detect unusual business events and investigate the factors contributing to them.

Instead of stopping at anomaly detection, DecisionLens performs a multi-perspective investigation across different business dimensions, including products, categories, stores, regions, pricing, historical trends, seasonality, correlations, and major contributors.

The results are presented through an interactive dashboard, providing explainable investigation findings, evidence, recommendations, and AI-generated summaries.

## Problem Statement

Retail businesses generate large volumes of transactional data, making it difficult to manually identify unusual changes in business performance and understand why they occurred.

Traditional analytics dashboards and anomaly detection systems can indicate that a metric is unusual, but they often do not provide a structured explanation of the business factors behind the anomaly.

For example, a sudden change in sales performance may be related to specific products, categories, stores, regions, pricing changes, seasonal patterns, or other contributing factors. Investigating these possibilities manually can be time-consuming and inconsistent.

DecisionLens addresses this problem by detecting unusual business events and automatically investigating them across multiple business dimensions to provide structured, explainable findings and recommendations.

## How DecisionLens Works

DecisionLens follows a structured investigation pipeline:

```text
Retail Dataset
      ↓
Data Preprocessing and Validation
      ↓
Feature Engineering
      ↓
Weekly KPI Generation
      ↓
Business Event Filtering
      ↓
Anomaly Detection
      ↓
Business Event Creation
      ↓
Multi-Perspective Investigation
      ↓
Evidence Aggregation
      ↓
Recommendation Generation
      ↓
AI-Generated Summary
      ↓
Interactive Dashboard
```

The pipeline processes retail data to identify unusual patterns and converts detected anomalies into business events. Each event is then investigated using multiple analyzers to identify potential contributing factors.

The findings are aggregated into an investigation report, which includes supporting evidence, identified contributors, recommendations, and an AI-generated natural-language summary.


## Key Features

- **Data Preprocessing and Validation** — Cleans, validates, and prepares retail datasets for analysis.
- **Weekly KPI Analysis** — Generates KPI data at the Store, Category, and Week level.
- **Anomaly Detection** — Identifies unusual business patterns using an Isolation Forest-based approach.
- **Business Event Creation** — Converts detected anomalies into structured business events for investigation.
- **Multi-Perspective Investigation** — Investigates events across products, categories, stores, regions, pricing, historical trends, seasonality, correlations, and top contributors.
- **Evidence Aggregation** — Combines findings from multiple analyzers into a structured investigation report.
- **Recommendation Engine** — Generates actionable recommendations based on investigation findings.
- **AI-Generated Summaries** — Uses an external AI model through the Groq API to generate natural-language investigation summaries.
- **Interactive Dashboard** — Provides pages for viewing investigations, events, analytics, and detailed findings.
- **Custom Dataset Analysis** — Allows users to analyze their own supported retail datasets through the application.

## System Architecture

```text
                        ┌─────────────────────┐
                        │   Retail Dataset    │
                        └──────────┬──────────┘
                                   │
                                   ▼
                    ┌─────────────────────────┐
                    │   Preprocessing Engine  │
                    │ Validation • Cleaning   │
                    │ Feature Engineering     │
                    └──────────┬──────────────┘
                               │
                               ▼
                    ┌─────────────────────────┐
                    │       KPI Engine        │
                    │ Weekly Business KPIs    │
                    └──────────┬──────────────┘
                               │
                               ▼
                    ┌─────────────────────────┐
                    │   Anomaly Detection     │
                    │ Business Event Filter   │
                    └──────────┬──────────────┘
                               │
                               ▼
                    ┌─────────────────────────┐
                    │   Investigation Engine  │
                    │  Multiple Analyzers     │
                    └──────────┬──────────────┘
                               │
                               ▼
                    ┌─────────────────────────┐
                    │   Evidence Aggregator   │
                    │   Recommendation Engine │
                    └──────────┬──────────────┘
                               │
                     ┌─────────┴─────────┐
                     ▼                   ▼
              ┌──────────────┐    ┌──────────────┐
              │    SQLite    │    │     Groq     │
              │   Database   │    │  AI Summary  │
              └──────┬───────┘    └──────┬───────┘
                     │                   │
                     └─────────┬─────────┘
                               ▼
                    ┌─────────────────────────┐
                    │   Streamlit Dashboard   │
                    │ Insights • Reports      │
                    │ Analytics • Upload      │
                    └─────────────────────────┘
```


## Investigation Engine

The Investigation Engine is responsible for analyzing each detected business event from multiple perspectives.

Instead of relying on a single explanation, DecisionLens evaluates different business dimensions to identify potential factors contributing to an unusual event.

### Investigation Analyzers

The system includes the following analyzers:

1. **Product Analyzer** — Examines product-level contributions to the event.
2. **Category Analyzer** — Analyzes category-level performance.
3. **Store Analyzer** — Identifies store-level factors and variations.
4. **Region Analyzer** — Examines regional performance patterns.
5. **Price Analyzer** — Investigates potential relationships between price changes and business performance.
6. **Historical Analyzer** — Compares the event with historical performance.
7. **Seasonality Analyzer** — Examines whether seasonal patterns may explain the event.
8. **Correlation Analyzer** — Identifies relationships between relevant business metrics.
9. **Top Contributor Analyzer** — Identifies the entities contributing most significantly to the observed change.

The outputs from these analyzers are combined by the **Evidence Aggregator** to produce a structured investigation report.

## Technologies Used

### Core Technologies

- **Python** — Core programming language used to build the system.
- **Pandas** — Data manipulation and analysis.
- **NumPy** — Numerical operations.
- **Scikit-learn** — Machine learning and anomaly detection using Isolation Forest.
- **SQLite** — Local database for storing investigation results.
- **Streamlit** — Interactive web-based dashboard.

### AI Integration

- **Groq API** — Used to access an external AI model for generating natural-language investigation summaries.

### Development and Testing

- **Visual Studio Code (VS Code)** — Primary development environment.
- **Jupyter Notebook** — Used for preprocessing experiments and exploratory testing.
- **Git and GitHub** — Version control and project hosting.

 ## Project Structure

```text
DecisionLens/
│
├── anomaly_detection/        # Anomaly detection and business event logic
├── preprocessing/            # Data validation, cleaning, and feature engineering
├── kpi_engine/               # Weekly KPI computation
├── investigation_engine/     # Multi-perspective investigation and reporting
├── database/                 # SQLite database management and schema
├── dashboard/                # Streamlit application and dashboard pages
│   ├── pages/                # Dashboard pages
│   └── demo_data/            # Demo dataset generation and sample data
├── tests/                    # Pipeline and component testing
├── data/                     # Raw and generated datasets
├── dataset/                  # Additional datasets used for testing
├── notebooks/                # Exploratory and preprocessing notebooks
├── utils/                    # Utility modules
│
├── config.py                 # Project configuration
├── requirements.txt          # Python dependencies
├── .gitignore                # Files excluded from Git
└── README.md                 # Project documentation

```
## Installation and Setup

### Prerequisites

Make sure you have the following installed:

- Python 3.x
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Saikiranreddy2644/DecisionLens.git
cd DecisionLens
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**Windows**

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

The project requires the following Python libraries:

- pandas
- numpy
- scikit-learn
- streamlit
- plotly
- requests

### 5. Configure the Groq API Key

DecisionLens uses the Groq API to generate AI-based investigation summaries.

Create a `.env` file in the project root and add your API key:

```text
GROQ_API_KEY=your_api_key_here
```

> **Important:** Never commit your `.env` file or API key to GitHub. The `.env` file should remain excluded through `.gitignore`.

### 6. Run the Application

From the project root, start the Streamlit dashboard:

```bash
streamlit run dashboard/app.py
```

The application will start and open in your web browser.

## How to Use DecisionLens

### 1. Launch the Application

Start the Streamlit dashboard:

```bash
streamlit run dashboard/app.py
```

### 2. Explore the Dashboard

The application provides multiple pages for exploring the investigation results:

- **Overview** — View a high-level summary of the detected business events and investigations.
- **Events** — Browse detected business events.
- **Investigation Detail** — View detailed evidence and findings for individual investigations.
- **Analytics** — Explore investigation and business insights through visualizations.
- **Try It Yourself** — Upload and analyze a supported retail dataset.

### 3. Run an Investigation

DecisionLens processes the retail dataset through the following stages:

1. Data preprocessing and validation
2. KPI computation
3. Business event filtering
4. Anomaly detection
5. Business event creation
6. Multi-perspective investigation
7. Evidence aggregation
8. Recommendation generation
9. AI-generated investigation summary

The investigation results can then be explored through the Streamlit dashboard.

## Supported Dataset Structure

DecisionLens is designed primarily for retail transaction datasets.

The preprocessing engine identifies and maps supported retail data columns before running the investigation pipeline.

Typical retail data may include information such as:

- Order or transaction identifier
- Order date
- Product
- Category
- Store or location
- Region
- Sales or revenue
- Quantity
- Price or discount

The system performs preprocessing and column mapping before generating KPIs and running anomaly detection.

**Note:** The current version of DecisionLens is designed and tested primarily for store- and category-based retail analysis. Dataset compatibility may depend on the availability of the required business dimensions and metrics.

## Testing and Validation


DecisionLens was developed using a primary retail dataset and was further tested on four additional datasets to evaluate the behavior of the preprocessing and investigation pipeline across different dataset structures and scenarios.

The project also includes a separate demo dataset used for demonstrating the application through the dashboard.


The testing included:

- **Analyzer Testing** — Individual investigation analyzers were tested to verify that they produced expected outputs.
- **Pipeline Testing** — The complete pipeline was tested from preprocessing through anomaly detection, investigation, and report generation.
- **Synthetic Scenario Testing** — Multiple synthetic scenarios were used to test different types of business anomalies, including product-driven, store-wide, price-driven, and normal scenarios.
- **Dataset Generalization Testing** — Additional retail datasets were used to check whether the preprocessing and investigation pipeline could handle different dataset structures.
- **Dashboard Testing** — Dashboard pages and data access functionality were tested to verify that investigation results were displayed correctly.

The current version has been tested primarily for retail datasets and store- and category-based analysis.

## Current Limitations

- The current version is designed primarily for retail transaction data.
- The investigation workflow is currently focused on store- and category-based analysis.
- Dataset compatibility depends on the availability and successful mapping of the required business dimensions and metrics.
- The system has been tested on a limited number of datasets and is not intended to guarantee compatibility with every retail dataset.
- Investigation results identify potential contributing factors based on the available data and should be interpreted as decision-support insights rather than definitive causal conclusions.






