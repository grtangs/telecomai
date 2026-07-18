# Telecom Customer Support Agent

This is a python + uv + langchain/langgraph based application with loops solving an interesting problem for telecom domain using Gradio frontend and DeepSeek API.

## Features
- **Triage Node**: Classifies queries into Billing, Technical Support, Plan Upgrade, or General.
- **Autonomous Technical Support Loop**: Runs diagnostic check, attempts router reboot, checks again, attempts port reset, checks again, and escalates to a technician if degraded signals persist.
- **Gradio Dashboard**: Visual customer profile, live router diagnostic stats, LangGraph execution logs, and chatbot.

## Running Locally
```bash
# Add your DEEPSEEK_API_KEY to a .env file
uv run python app.py
```
