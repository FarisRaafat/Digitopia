# Semgrep Security Assistant

This project provides a Streamlit GUI to run Semgrep on an uploaded file or a zipped project, visualize the results, and chat with a Gemini-powered assistant (via LangChain) to get secure coding recommendations.

## Setup

1. Create and activate a virtual environment:

`powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
`

2. Install dependencies:

`powershell
pip install -r requirements.txt
`

3. Configure API keys in config.py:

- SEMGREP_APP_TOKEN for Semgrep authentication
- GEMINI_API_KEY for Gemini (Google Generative AI)

## Run the app

`powershell
streamlit run app.py
`

## How it works

- Semgrep is invoked via the CLI with --config=auto, outputting JSON which is parsed into a DataFrame with columns [file, line, rule, message, severity].
- Visualizations show findings per rule (bar chart) and severity distribution (pie chart).
- The chatbot uses LangChain with Gemini to provide concise secure coding recommendations based on the Semgrep findings.

## APIs/Libraries

- Semgrep: static analysis engine (semgrep CLI)
- Pandas/Matplotlib: data handling and visualization
- Streamlit: web UI
- LangChain + Gemini: LLM-based assistant for remediation guidance
