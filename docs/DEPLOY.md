# Deploying the dashboard

Streamlit Community Cloud, free. No secrets or API keys are needed.

Deployed on 2026-11-27: <https://energy-demand-forecast-pz2daz6h6ksbmcszecf7nl.streamlit.app/>

1. Go to <https://share.streamlit.io>, sign in with GitHub and choose to create an app from a repository.
2. Fill in:

| Field | Value |
|---|---|
| Repository | `thiagoCardoso13/energy-demand-forecast` |
| Branch | `main` |
| Main file path | `app.py` |
| Python version (advanced settings) | 3.12 |
| App URL | leave the suggested one |

3. Deploy, then check: the live view shows the latest day, the backtest view shows 365 days scored,
   and the data date is recent.

## Updates

The app reads the files in the repository, so the daily commit of `data/predictions.csv` is what
updates it. After a change to code, if the app still behaves as before, change `requirements.txt`
(a comment is enough) to force a clean restart.

Free apps go to sleep when unused and take a while to wake up.
