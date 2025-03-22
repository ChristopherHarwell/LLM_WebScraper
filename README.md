# LLM Web Scraper Chatbot

A multi-agent web scraper chatbot that uses CrewAI and DeepSeek-Vision to scrape websites and answer questions about their content. The system handles CAPTCHAs, dynamic content, and provides reasoning-based answers with HTML element references.

## Features

- Multi-agent system using CrewAI for orchestration
- Web scraping with Playwright for JavaScript-heavy sites
- CAPTCHA detection and solving using DeepSeek-Vision
- Question answering with reasoning and HTML element references
- FastAPI backend with OpenAPI documentation

## Prerequisites

- Python 3.10 or higher
- Ollama installed and running locally
- DeepSeek-Vision model pulled in Ollama

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd llm-webscraper
```

2. Install dependencies using UV:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
.venv\Scripts\activate     # On Windows
uv pip install -e .
```

3. Install Playwright browsers:
```bash
playwright install
```

4. Install and setup Ollama:
```bash
# Follow Ollama installation instructions from https://ollama.ai
ollama pull deepseek-vision
```

## Usage

1. Start the FastAPI server:
```bash
uvicorn src.api.main:app --reload
```

2. The API will be available at http://localhost:8000
3. API documentation is available at http://localhost:8000/docs

## API Endpoints

- POST `/ask`
  - Input: JSON with `url` and `query` fields
  - Output: Answer with reasoning and relevant HTML element

## Project Structure

```
llm-webscraper/
├── src/
│   ├── agents/         # CrewAI agent definitions
│   ├── tools/          # Custom tools and utilities
│   └── api/            # FastAPI application
├── tests/              # Test files
├── pyproject.toml      # Project metadata and dependencies
└── README.md          # This file
```

## License

MIT 