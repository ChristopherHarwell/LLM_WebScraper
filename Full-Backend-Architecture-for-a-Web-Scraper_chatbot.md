# Full Backend Architecture for a Web Scraper Chatbot

Figure: High-level architecture of the multi-agent web scraper chatbot pipeline.

![](./LLM%20Scraper%20Architecture.jpeg)

## Architecture Overview

The system is composed of several components working together to scrape web content, solve CAPTCHAs, and answer user queries. The diagram above illustrates the pipeline. Key components include:
	•	API Layer (FastAPI/Flask): Exposes an endpoint that accepts a user’s query and target URL. It triggers the scraping workflow and returns results.
	•	CrewAI Orchestrator: Manages multiple specialized AI agents (using CrewAI). Each agent has a specific role, tools, and goals ￼. The orchestrator delegates tasks to agents and ensures they work together to fulfill the query.
	•	Scraper Agent: Responsible for fetching the HTML content of the target website. It can use HTTP requests or a headless browser (Playwright/Selenium) for dynamic pages. This agent returns the raw HTML and detects if an image-based CAPTCHA is present.
	•	Captcha Solver Agent: Activates if a CAPTCHA is encountered. It downloads the CAPTCHA image and uses the vision-capable LLM (via Ollama) to perform OCR or interpret the image. The solved text is fed back to the Scraper agent, which can then submit the solution and continue scraping. (For complex CAPTCHAs like reCAPTCHA, external solver services or specialized plugins may be needed ￼.)
	•	LLM Agent (DeepSeek-Vision): Uses the DeepSeek-Vision model (run locally through Ollama) to analyze the scraped HTML content and images. This agent receives the full HTML (with any images in base64 format) and the user’s question, then responds with a reasoning-based answer and identifies the relevant HTML element(s) that contain the answer.
	•	DeepSeek-Vision via Ollama: The underlying Large Language Model, capable of multi-modal input (text HTML and images). DeepSeek-R1 models are known for strong reasoning (comparable to OpenAI’s GPT-4 class in open domain tasks ￼), and vision-enabled variants (e.g. LLaVA or Granite models) can interpret images and HTML layout ￼. Ollama serves this model locally via an API, enabling private and fast inference.

## Workflow Steps:
	1.	Input: User sends a query and a target URL to the API (e.g. “What is the price of this product?” with a product page URL).
	2.	Task Delegation: The API invokes the CrewAI orchestrator, which in turn creates a sequence of tasks for the agents. For example, a Task: Scrape Website is assigned to the Scraper agent, and a Task: Analyze Content is assigned to the LLM agent. Agents have clearly defined roles and tools to perform these tasks ￼.
	3.	Scraping: The Scraper agent fetches the page content. It might use a headless browser (via Playwright) if the page requires rendering or login. Using a headless browser helps in executing JavaScript and obtaining dynamic content, and can help navigate anti-scraping measures. If the page returns a typical anti-bot challenge or CAPTCHA, the agent detects it (e.g., by finding <img> tags or specific text like “verify you are human”).
	4.	CAPTCHA Handling: If a CAPTCHA is detected, the Scraper agent delegates a sub-task to the Captcha Solver agent (CrewAI supports task delegation between agents ￼). The Captcha agent downloads the CAPTCHA image and sends it (as base64 text) to the DeepSeek-Vision model. The LLM (which has vision OCR capability) returns the text it sees in the image (solving the CAPTCHA). The Scraper agent then submits this text (e.g., fills the CAPTCHA form or appends it to the request) and retries the request until the full HTML is obtained.
	5.	Content Analysis: Once HTML (and any important images) are retrieved, the orchestrator triggers the LLM Agent with the Analyze Content task. The agent’s prompt includes the user’s natural language question, the raw HTML content, and any image data (embedded as data URIs). The DeepSeek-Vision model (via Ollama) processes this multi-modal input and produces an answer along with an explanation of its reasoning. It also identifies which part of the HTML contains the answer – for example, providing an XPath or a snippet of the element.
	6.	Result Aggregation: The CrewAI orchestrator collects the LLM’s output. It may structure it into a final response, such as a JSON containing the answer, reasoning, and the HTML element (e.g., XPath or innerHTML) that supports the answer. This result is sent back through the API to the user.

Each agent operates semi-autonomously but cooperates through the CrewAI framework. For example, the Scraper agent could internally call a “Vision Tool” to solve a CAPTCHA (CrewAI provides a VisionTool for image tasks ￼), or explicitly delegate to a separate agent. The LLM agent uses the DeepSeek-Vision model to ensure it can handle both HTML structure and images in one go. DeepSeek’s models running via Ollama allow local deployment of powerful LLMs without external API calls ￼ ￼.

## Python Implementation Outline

Below is a structured Python-based implementation using FastAPI, CrewAI, Ollama (DeepSeek model), and Playwright. The implementation is organized into components for clarity:

Dependencies: crewai, crewai_tools, playwright (or selenium), beautifulsoup4 (for parsing), fastapi, uvicorn, and langchain_community for Ollama integration. For example, install with:

```sh
pip install crewai[tools] playwright fastapi langchain-community
```
and install Playwright browsers: playwright install.

1. CrewAI Agents and Tasks Setup

We first configure the LLM (DeepSeek-Vision via Ollama) and define our agents and tasks:

```py
from crewai import Agent, Task, Crew
from crewai_tools import ScrapeWebsiteTool, VisionTool
from langchain_community.llms import Ollama

# Initialize the local LLM through Ollama (DeepSeek vision-capable model)
ollama_llm = Ollama(model="deepseek-vision-7b")  # example model name

# Define the Scraper Agent with a scraping tool (Playwright or requests)
scraper_agent = Agent(
    role="web_scraper",
    goal="Fetch the HTML content (and images) of the target site.",
    tools=[ScrapeWebsiteTool()],  # basic scraping via requests; for JS sites, we'll override with Playwright
    allow_delegation=True,
    llm=ollama_llm  # The scraper might not need the LLM, but could use it for delegation if needed
)

# Define the Vision/CAPTCHA solver agent
vision_agent = Agent(
    role="captcha_solver",
    goal="Decode text from images (e.g., CAPTCHAs) using vision capabilities.",
    tools=[VisionTool()],  # CrewAI VisionTool can handle image-to-text
    llm=ollama_llm
)

# Define the main LLM analysis agent
analysis_agent = Agent(
    role="content_analyzer",
    goal="Analyze HTML content and answer questions, providing reasoning and HTML element references.",
    backstory="You are an expert at reading HTML and images, and extracting precise answers.",
    allow_delegation=False,
    llm=ollama_llm
)
```

In the above code, we use CrewAI’s built-in ScrapeWebsiteTool for simple HTML fetching ￼. In practice, we might extend it to use Playwright for complex sites. The VisionTool can be used to interpret images (by sending them to the LLM) ￼. We set allow_delegation=True on the scraper so it can delegate CAPTCHA solving to the vision agent.

Next, we define tasks that tie the workflow together:
```py
# Define tasks for the multi-agent workflow
task_scrape = Task(
    description="Scrape the website content and detect CAPTCHAs.",
    agent=scraper_agent,
    input={"url": None},  # We'll fill the URL at runtime
    expected_output="HTML content of the page (with images if needed)."
)
task_analyze = Task(
    description="Answer the user query based on the HTML and images. Identify the relevant HTML element.",
    agent=analysis_agent,
    input={"query": None, "html": None, "images": None},  # inputs provided after scraping
    expected_output="Answer to the query with reasoning and HTML element reference."
)

# Optional: a task solely for CAPTCHA solving (could also be internal to scraper_agent)
task_solve_captcha = Task(
    description="Solve CAPTCHA from image if present in page.",
    agent=vision_agent,
    input={"image_data": None},
    expected_output="Solved text from CAPTCHA image."
)
```

The task_scrape will later be given the actual URL. The task_analyze will receive the query and the scraped content. We include task_solve_captcha as a separate task for clarity, though in practice the scraper agent could call the vision agent’s tool directly.

2. HTML Scraping and CAPTCHA Detection

For more control, we can override the ScrapeWebsiteTool with a custom Playwright-based function. For example:
```py
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import base64
import re

def fetch_page_content(url: str):
    """Fetch page content, possibly using Playwright for dynamic pages."""
    # Use Playwright to handle dynamic content and potential JS challenges
    with sync_playwright() as pw:
        browser = pw.firefox.launch(headless=True)
        page = browser.new_page()
        response = page.goto(url, timeout=60000)
        html = page.content()
        # Save any important images (like CAPTCHA) from the page
        images = {}
        for img in page.query_selector_all("img"):
            src = img.get_attribute("src")
            if src:
                # If the src is a data URI or base64, keep as is; otherwise, download
                if src.startswith("data:image"):
                    images[src] = src  # already base64
                elif "captcha" in src.lower() or re.search(r'captcha', src, re.I):
                    # Likely a captcha image, download it
                    img_bytes = requests.get(src, headers={"Referer": url}).content
                    images[src] = "data:image/png;base64," + base64.b64encode(img_bytes).decode('utf-8')
        browser.close()
    return html, images
```

This function uses Playwright to load the page (with a Firefox headless browser) and get the final HTML. It also looks for <img> tags where the src suggests a CAPTCHA (e.g., filename containing “captcha”). If found, it downloads that image via requests and encodes it in base64. All images are stored in a dictionary images mapping the image URL to a data URI string. We intentionally prioritize detection of CAPTCHAs, but you could extend this to download all images if needed. (Note: For large pages, downloading every image might be unnecessary. Instead, one could just embed the URLs or pick images likely relevant to the query.)

CAPTCHA detection can also include checking for known page text like “enter the characters” or presence of a form named “captcha”. In practice, many scraping frameworks handle common anti-bot measures with stealth plugins or external solvers ￼, but our approach keeps it self-contained via the vision model.

Next, we integrate this function into the Scraper agent’s execution within CrewAI. CrewAI tasks can use Python functions via tools, or we can manually call this function in our flow and provide the output to the next task:

```py
def scrape_task_handler(url):
    html, images = fetch_page_content(url)
    # If a CAPTCHA was found and we have images
    for src, data_uri in images.items():
        if "captcha" in src.lower():
            # Use vision agent to solve it
            solved = crew.run_task(task_solve_captcha, inputs={"image_data": data_uri})
            # If solved, perhaps submit the solution via form or retry fetch_page_content with solution.
            # This part would depend on the site’s CAPTCHA mechanism.
            # For simplicity, assume CAPTCHA was solved as part of fetch_page_content if possible.
            print(f"CAPTCHA solved: {solved}")
    return {"html": html, "images": images}
```

Here we manually call the crew.run_task for the CAPTCHA solving (this assumes the Crew orchestrator crew is defined, see below). In a real pipeline, the Scraper agent could automatically delegate to the vision agent. For demonstration, we handle it explicitly.

3. Prompting the LLM (DeepSeek-Vision)

We need to craft a prompt to send the HTML and images to the LLM agent. DeepSeek-Vision (or similar multi-modal LLMs) expect text input; images can be passed as base64 data URLs embedded in the prompt. For example:

```py
def build_llm_prompt(query, html, images):
    # Embed images in the HTML by replacing img src with base64 data, for completeness
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src in images:
            img["src"] = images[src]  # replace src with data URI
    inline_html = str(soup)
    # Construct prompt with instructions
    prompt = f"""You are an expert web document analyst. 
You are given the HTML content of a webpage and possibly some images embedded.
Answer the user's query using the content. Provide a detailed reasoning, and identify the exact HTML element that contains the answer.

HTML Content:
\"\"\"{inline_html}\"\"\"

Question: {query}

Your response should include:
- The answer to the question.
- A brief reasoning explaining how you found it.
- The HTML element (e.g., an XPath or snippet) that supports the answer.
"""
    return prompt
```

This function merges the HTML and images (by injecting base64 image data into <img> tags) and wraps it in a prompt template instructing the model to answer with reasoning and element identification. We delimit the HTML with triple quotes to clearly distinguish it in the prompt.

Note on large HTML: If the HTML is very long (exceeding the model’s context window), you might need to truncate or summarize it. One strategy is to first prompt the LLM to summarize or extract relevant sections (based on the query) from the HTML, then ask the question on that summary. Another strategy is chunking: split the HTML by sections (DOM sections, headings, etc.), ask the question for each chunk, then aggregate. DeepSeek models can handle fairly large contexts (some versions support 16K or more tokens), but it’s wise to manage input size proactively.

4. Running the Agents (Crew Orchestration)

Now we put it all together with CrewAI. We set up the Crew with our agents and use a process (sequential execution of tasks in our case):

```py
# Assemble the crew with agents
crew = Crew(agents=[scraper_agent, vision_agent, analysis_agent], tasks=[], verbose=2)

def answer_query(url: str, query: str):
    # Step 1: Scrape the content
    content = scrape_task_handler(url)
    html = content["html"]
    images = content["images"]
    # Step 2: Build prompt for analysis agent
    prompt = build_llm_prompt(query, html, images)
    # Step 3: Run the analysis task via the LLM agent
    analysis_input = {"query": query, "html": html, "images": images}
    result = crew.run_task(task_analyze, inputs=analysis_input)
    return result

# Example usage:
# res = answer_query("https://example.com/product/123", "What is the price of the product?")
# print(res)
```

We manually orchestrated the steps here for clarity: scraping then analysis. Alternatively, we could define crew.tasks = [task_scrape, task_analyze] and implement dependencies between tasks. For instance, after task_scrape completes, its output could be passed as input to task_analyze. CrewAI’s Process.sequential mode can run tasks one after the other ￼. In pseudo-code:

```py
task_scrape.input = {"url": target_url}
task_analyze.input = {"query": user_query, "html": "@output_of_task_scrape.html", "images": "@output_of_task_scrape.images"}
crew = Crew(agents=[scraper_agent, vision_agent, analysis_agent],
            tasks=[task_scrape, task_analyze],
            process=Process.sequential, verbose=2)
result = crew.kickoff()
```

CrewAI would handle passing outputs between tasks. Here "@output_of_task_scrape.html" denotes using the result of the first task as input to the second (this is an illustrative syntax; actual CrewAI may use a different mechanism to link task outputs).

The final result from task_analyze should include the answer, reasoning, and element. We might structure it as a dictionary, or the LLM might return a formatted string that we then parse. For example, the LLM’s answer might be in JSON (if we prompt it to output JSON). In that case, we parse the JSON to extract fields.

5. API Layer (FastAPI)

Finally, we create an API endpoint to expose this functionality. Using FastAPI:

```Py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Web Scraper Chatbot API")

class QueryRequest(BaseModel):
    url: str
    query: str

@app.post("/ask")
def ask_page(request: QueryRequest):
    try:
        result = answer_query(request.url, request.query)
        return {"url": request.url, "query": request.query, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

This defines a POST endpoint /ask that expects a JSON body with url and query. It calls our answer_query function and returns the result in JSON. The result could be the raw LLM output or a structured dict; you might want to format it nicely before returning (e.g., separate keys for answer, reasoning, element).

FastAPI automatically generates documentation (OpenAPI schema), making it easy to test the endpoint via a web UI. We can run the app with Uvicorn (e.g., uvicorn app:app --reload).

## Additional Considerations

Managing Long HTML Inputs: Long pages may exceed the LLM’s input limits. To handle this, consider:
	•	Stripping irrelevant content: remove scripts, style tags, and large sections of HTML not related to text (navigation bars, footers, etc.) before sending to the LLM. Tools like BeautifulSoup help to extract main content. Alternatively, use an HTML-to-text library to get a simplified version of the page.
	•	Chunking: Split the HTML into logical sections (e.g., by <div> or <section> or by paragraphs) and let the LLM analyze each part for the answer, then combine results.
	•	Summarization: Ask the LLM (or a smaller preliminary LLM) to summarize the page first. For instance, a prompt like “Summarize this page content focusing on [the query topic]” can reduce the text size.

Rate Limiting & Politeness: Ensure the scraper respects target websites:
	•	Implement a delay or token bucket to avoid too many rapid requests to the same site ￼. For example, limit to 1 page per second or as indicated by robots.txt ￼.
	•	Check robots.txt rules for the site using Python’s urllib.robotparser or similar, if applicable, to avoid disallowed paths ￼.
	•	Use user-agent headers identifying your bot and provide contact info if doing wide scraping.

Headless Browser Use: We leveraged Playwright for complex pages. On deployment, make sure to handle:
	•	Browser installation: In a Docker container, include the necessary browsers (Playwright’s playwright install can do this in build).
	•	Timeout and error handling: If a page takes too long or the browser fails, have retry logic or fallback to a simpler requests approach. Catch exceptions from Playwright and return a clear error via the API if needed.
	•	JavaScript execution: For SPA applications, you might need to wait for certain network calls or elements to load (Playwright’s page.wait_for_selector() can help).

Security: Be cautious if exposing this API publicly:
	•	Only allow scraping of allowed domains or add authentication to the API, to prevent abuse (someone could input arbitrary URLs).
	•	Sanitize the output if you plan to render the returned HTML element to users. The element could contain scripts or malicious content. It might be safer to return an XPath or text content of the element rather than raw HTML.

Deployment: Containerize the application for consistency:
	•	Use a base image (Python 3.10+ with needed packages). Install system dependencies for Playwright (it provides convenience scripts for Debian-based images).
	•	Run Ollama as a sidecar service on the same host or inside the container (Ollama is a separate binary that serves the model on localhost:11434 by default ￼). Ensure the model deepseek-vision is downloaded (ollama pull deepseek-vision).
	•	In docker-compose or Kubernetes, you might have one service for the FastAPI app and one for the Ollama server, or run Ollama in-process if an API is available via Python (in our example we used a LangChain wrapper which likely calls the Ollama backend).

Testing: For development, use dummy sites or local HTML files:
	•	Create a simple HTML page that contains a known answer to a question (and perhaps an image). Test the pipeline on it.
	•	Simulate a CAPTCHA by including an image with known text and see if the vision agent correctly reads it.
	•	Unit test the fetch_page_content function (possibly using a library like responses or Playwright’s own testing framework to simulate page content).
	•	Mock the LLM during testing of the API to return a predetermined answer (to avoid needing the heavy model running).
	•	Use FastAPI’s TestClient to simulate API calls to /ask and verify the structure of the response.

By following this architecture, we create a robust backend that orchestrates multiple AI agents to perform end-to-end web browsing, data extraction, and question answering. CrewAI’s framework allows each agent to focus on a sub-task (scraping, image OCR, reasoning) and collaborate ￼. The use of a local DeepSeek-Vision model via Ollama provides privacy and avoids external API costs, while still benefiting from advanced multi-modal understanding. This design is scalable and can be extended with more agents or tools (for example, an agent specialized in extracting structured data or an agent that uses a vector database for memory).

## References:
	•	CrewAI Documentation – Introduction & Tools ￼ ￼
	•	Ollama and DeepSeek – Local LLM serving with vision support ￼ ￼
	•	Playwright CAPTCHA Handling – Techniques to bypass CAPTCHAs ￼
	•	Web Scraping Best Practices – Rate limiting and compliance ￼ ￼