# NYC Housing & Transportation Analytics Dashboard

A Streamlit dashboard for exploring the relationship between NYC Housing Maintenance Code Complaints and serious-injury traffic crashes.

## Project files

- `app.py` — Streamlit application.
- `data/` — CSV exports from the completed Colab analysis.
- `requirements.txt` — Python dependencies.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. Open Streamlit Community Cloud and connect the repository.
3. Select `app.py` as the app entry point.
4. Deploy.

## Data sources

- NYC Housing Maintenance Code Complaints: https://data.cityofnewyork.us/resource/ygpa-z7cr
- SIRTA Serious Injury & Fatality Crashes: https://data.cityofnewyork.us/resource/xeqp-qz8h

## Data limitations

The supplied exports contain aggregated counts and do not include the underlying complaint-category or crash-category fields. The category selectors are therefore disabled rather than populated with invented categories. The transportation dataset covers serious-injury crash investigations, not all traffic crashes. Correlations describe association and do not establish causation.
