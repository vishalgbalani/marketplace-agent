import os
import json
import requests
from typing import AsyncGenerator, Optional
from dotenv import load_dotenv
from agents import Agent, Runner, function_tool
from tavily import TavilyClient
from .models import MarketplaceAnalysis

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Per-request URL collector. Populated by tools, read by the pipeline.
_collected_urls: list = []

# --- Vertical-specific search queries ---

VERTICAL_SEARCHES = {
    "E-Commerce": [
        "{company} seller fees policy changes commission structure",
        "{company} seller experience third party marketplace",
        "{company} buyer protection authentication program",
        "{company} advertising revenue promoted listings",
        "{company} fulfillment logistics shipping strategy",
    ],
    "Food Delivery": [
        "{company} driver courier pay model tips",
        "{company} restaurant commission fees partnership",
        "{company} delivery fee pricing strategy subsidy",
        "{company} grocery convenience retail expansion",
    ],
    "Ride-Hailing": [
        "{company} driver earnings surge pricing model",
        "{company} autonomous vehicles robotaxi strategy",
        "{company} rider retention pricing strategy",
        "{company} regulatory labor classification",
    ],
    "Travel": [
        "{company} host acquisition supply growth strategy",
        "{company} commission fee structure take rate",
        "{company} travel fintech insurance attach rate",
        "{company} regulatory short term rental restrictions",
    ],
    "Grocery": [
        "{company} shopper pay batch order model",
        "{company} grocery delivery profitability unit economics",
        "{company} retail media advertising revenue",
        "{company} partnership grocery chain expansion",
    ],
    "Services": [
        "{company} freelancer fees service charges take rate",
        "{company} enterprise managed services strategy",
        "{company} AI matching quality scoring",
        "{company} freelancer retention churn platform switching",
    ],
}

REDDIT_SUBREDDITS = {
    "E-Commerce": "site:reddit.com/r/eBaySellers OR site:reddit.com/r/AmazonSeller OR site:reddit.com/r/Etsy OR site:reddit.com/r/FulfillmentByAmazon",
    "Food Delivery": "site:reddit.com/r/doordash_drivers OR site:reddit.com/r/UberEATS OR site:reddit.com/r/grubhubdrivers",
    "Ride-Hailing": "site:reddit.com/r/uberdrivers OR site:reddit.com/r/lyftdrivers",
    "Travel": "site:reddit.com/r/AirbnbHosts OR site:reddit.com/r/vrbo OR site:reddit.com/r/travel",
    "Grocery": "site:reddit.com/r/InstacartShoppers OR site:reddit.com/r/grocery",
    "Services": "site:reddit.com/r/Upwork OR site:reddit.com/r/freelance OR site:reddit.com/r/TaskRabbit",
}

HIRING_SIGNAL_GUIDE = {
    "E-Commerce": "Trust & Safety roles → authentication/fraud investment; Ads/Monetization roles → promoted listings expansion; Payments/Fintech roles → managed payments evolution; Seller Experience PM roles → supply-side investment; ML/Search roles → discovery algorithm investment",
    "Food Delivery": "ML/Pricing roles → algorithmic pricing investment; Operations in new cities → geographic expansion; Restaurant partnerships → supply acquisition push; Autonomous/Robotics roles → automation strategy",
    "Travel": "Fintech/Insurance roles → attach rate strategy; Revenue Management roles → pricing sophistication; Host/Supply roles → supply acquisition; ML/Personalization → recommendation engine investment",
    "default": "Heavy ML/AI hiring → algorithmic investment; Operations roles in new cities → geographic expansion; Customer support cuts → automation push; PM roles mentioning specific areas → strategic priorities; Data engineering hiring → data infrastructure build-out",
}


# --- Tools ---

@function_tool
def search_web(query: str) -> str:
    """Search the web for marketplace intelligence using Tavily."""
    try:
        results = tavily_client.search(query=query, max_results=5)
        formatted = []
        for r in results.get("results", []):
            url = r["url"]
            _collected_urls.append(url)
            formatted.append(f"Title: {r['title']}\nURL: {url}\nSnippet: {r['content'][:500]}")
        return "\n\n---\n\n".join(formatted) if formatted else "No results found."
    except Exception as e:
        return f"Web search error: {str(e)}"


@function_tool
def search_reddit_sentiment(query: str) -> str:
    """Search Reddit for supply-side sentiment using Tavily scoped to Reddit."""
    try:
        results = tavily_client.search(query=query, max_results=5, include_domains=["reddit.com"])
        formatted = []
        for r in results.get("results", []):
            url = r["url"]
            _collected_urls.append(url)
            formatted.append(f"Subreddit/URL: {url}\nContent: {r['content'][:600]}")
        return "\n\n---\n\n".join(formatted) if formatted else "No Reddit results found."
    except Exception as e:
        return f"Reddit search error: {str(e)}"


@function_tool
def search_job_postings(company_name: str) -> str:
    """Search for recent job postings to identify strategic hiring signals."""
    try:
        api_key = os.getenv("JSEARCH_API_KEY")
        if not api_key:
            return "Job posting data unavailable: JSEARCH_API_KEY not configured."
        url = "https://jsearch.p.rapidapi.com/search"
        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        }
        params = {
            "query": f"{company_name} jobs",
            "num_pages": 1,
            "date_posted": "month",
        }
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        results = response.json().get("data", [])[:20]
        if not results:
            return f"No recent job postings found for {company_name}."
        formatted = []
        for job in results:
            title = job.get("job_title", "Unknown")
            employer = job.get("employer_name", "Unknown")
            location = job.get("job_city", "Remote")
            state = job.get("job_state", "")
            posted = job.get("job_posted_at_datetime_utc", "Unknown date")
            formatted.append(f"• {title} at {employer} — {location}, {state} (Posted: {posted[:10] if len(posted) >= 10 else posted})")
        return f"Recent job postings for {company_name} ({len(formatted)} found):\n" + "\n".join(formatted)
    except Exception as e:
        return f"Job posting data unavailable: {str(e)}"


# --- Agent factory ---

def build_researcher(company: str, marketplace_type: str, focus_area: Optional[str]) -> Agent:
    vertical_queries = VERTICAL_SEARCHES.get(marketplace_type, [])
    vertical_queries_text = "\n".join(f"  - \"{q.format(company=company)}\"" for q in vertical_queries)

    reddit_scope = REDDIT_SUBREDDITS.get(marketplace_type, "site:reddit.com/r/gig_economy")

    return Agent(
        name="Marketplace Researcher",
        model="gpt-4o-mini",
        instructions=f"""You are a senior marketplace research analyst. Gather comprehensive intelligence on {company} ({marketplace_type} marketplace).
{f'Special focus area: {focus_area}' if focus_area else ''}

You MUST use ALL THREE tools in this exact order and clearly label data sources:

**STEP 1 — Web Search (use search_web tool)**
Run these searches one at a time:
  - "{company} earnings call revenue take rate GMV 2025 2026"
  - "{company} marketplace strategy product launches 2025 2026"
  - "{company} competitors competitive landscape market share"
  - "{company} regulatory challenges antitrust 2025 2026"
  - "{company} AI investments machine learning data science"
Vertical-specific searches:
{vertical_queries_text}

**STEP 2 — Reddit Sentiment (use search_reddit_sentiment tool)**
Run these searches:
  - "{company} {reddit_scope}"
  - "{company} fees changes complaints site:reddit.com"
  - "{company} vs competitor site:reddit.com"

**STEP 3 — Job Postings (use search_job_postings tool)**
Search for: "{company}"

After gathering all data, synthesize into a research summary with these clearly labeled sections:
[WEB SEARCH FINDINGS] — key facts, financials, strategy, competitive landscape
[REDDIT SENTIMENT] — supply-side sentiment, common complaints, factual claims vs. venting
[JOB POSTING SIGNALS] — hiring patterns and what they signal about strategy

Include all relevant source URLs.""",
        tools=[search_web, search_reddit_sentiment, search_job_postings],
    )


strategist_agent = Agent(
    name="Marketplace Strategist",
    model="gpt-4o-mini",
    instructions="""You are a senior marketplace PM and strategy consultant. You receive research findings from the Marketplace Researcher and must produce a deep strategic analysis.

Analyze through these lenses:
1. **Supply-side dynamics**: acquisition, retention, churn, multi-tenanting, pricing satisfaction
2. **Demand-side patterns**: frequency, basket size/AOV, retention, price sensitivity, acquisition channels
3. **Unit economics signals**: take rate trends, contribution margin, subsidy dependency, path to profitability
4. **Network effects**: local vs global, cross-side vs same-side, liquidity thresholds
5. **Competitive moats**: data advantages, supply lock-in, brand, switching costs, regulatory capture
6. **Disintermediation risks**: where value leaks off-platform, direct relationships
7. **Reddit sentiment calibration**: weight factual claims (fee changes, policy updates, earnings data) over general complaints. Reddit skews negative — people post when frustrated, not satisfied. Note this bias explicitly.
8. **Hiring signals**: interpret job postings as leading indicators of strategy. What areas is the company investing in?

If a focus area was provided, weight your analysis toward that area.

Produce your analysis as structured sections matching the MarketplaceAnalysis schema fields. Be specific — cite data points, not vague generalizations. Write like a senior strategy consultant, not a generic AI.""",
)


writer_agent = Agent(
    name="Strategy Writer",
    model="gpt-4o-mini",
    instructions="""You are a senior strategy writer. Take the strategic analysis and produce a final structured briefing.

You MUST output valid JSON matching this exact schema:
{
  "company_name": "string",
  "marketplace_type": "string (e.g. 'two-sided e-commerce marketplace')",
  "marketplace_overview": "string (3-5 sentences: what it is, who the sides are, how value flows, current scale)",
  "supply_side_analysis": ["5-7 specific insights"],
  "demand_side_analysis": ["5-7 specific insights"],
  "unit_economics_signals": ["5-7 signals with data points"],
  "network_effects": ["3-5 observations"],
  "competitive_moats": ["3-5 defensible advantages"],
  "vulnerabilities": ["3-5 vulnerabilities"],
  "hiring_signals": ["3-5 insights from job postings"],
  "supply_side_sentiment": "string (2-3 paragraphs from Reddit, noting negativity bias)",
  "growth_levers": ["5-7 opportunities"],
  "strategic_risks": ["3-5 biggest risks"],
  "pm_recommendations": ["5-7 specific PM recommendations"],
  "data_sources_used": ["Web Search", "Reddit Sentiment", "Job Postings"],
  "sources": ["list of URLs"]
}

Write like a senior strategy consultant. Use specific data points. Every insight should be actionable and grounded in the research data. Output ONLY the JSON, no other text.""",
)


# --- Pipeline ---

async def run_pipeline(company: str, marketplace_type: str, focus_area: Optional[str]) -> AsyncGenerator[dict, None]:
    """Run the three-agent pipeline, yielding SSE events at each stage."""

    # Reset per-request URL collector
    _collected_urls.clear()

    # Stage 1: Research
    yield {"stage": "research", "status": "running", "message": "Searching web for company intelligence..."}

    researcher = build_researcher(company, marketplace_type, focus_area)

    focus_text = f" with focus on {focus_area}" if focus_area else ""
    research_prompt = f"Research {company} as a {marketplace_type} marketplace{focus_text}. Use ALL three tools (web search, Reddit sentiment, job postings) and synthesize findings."

    try:
        research_result = await Runner.run(researcher, research_prompt)
        research_output = research_result.final_output
    except Exception as e:
        yield {"stage": "research", "status": "error", "message": f"Research failed: {str(e)}"}
        return

    yield {"stage": "research", "status": "complete", "message": "Research gathering complete."}

    # Stage 2: Analysis
    yield {"stage": "analysis", "status": "running", "message": "Marketplace strategist is analyzing dynamics..."}

    analysis_prompt = f"""Analyze this marketplace research on {company} ({marketplace_type}).
{f'Focus area: {focus_area}' if focus_area else ''}

Research findings:
{research_output}

Produce a comprehensive strategic analysis covering all framework dimensions."""

    try:
        analysis_result = await Runner.run(strategist_agent, analysis_prompt)
        analysis_output = analysis_result.final_output
    except Exception as e:
        yield {"stage": "analysis", "status": "error", "message": f"Analysis failed: {str(e)}"}
        return

    yield {"stage": "analysis", "status": "complete", "message": "Strategic analysis complete."}

    # Stage 3: Writing
    yield {"stage": "writing", "status": "running", "message": "Writing strategic briefing..."}

    writing_prompt = f"""Create the final structured JSON briefing for {company} ({marketplace_type}).

Strategic analysis:
{analysis_output}

Output ONLY valid JSON matching the MarketplaceAnalysis schema."""

    try:
        writing_result = await Runner.run(writer_agent, writing_prompt)
        raw_output = writing_result.final_output

        # Parse the JSON output
        cleaned = raw_output.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        analysis_data = json.loads(cleaned)
        # Override sources with the full URLs collected directly from tool results
        analysis_data["sources"] = list(dict.fromkeys(_collected_urls))  # dedupe, preserve order
        analysis = MarketplaceAnalysis(**analysis_data)

        yield {"stage": "writing", "status": "complete", "message": "Strategic briefing complete."}
        yield {"stage": "done", "status": "complete", "data": analysis.model_dump()}

    except json.JSONDecodeError as e:
        yield {"stage": "writing", "status": "error", "message": f"Failed to parse output as JSON: {str(e)}", "raw_output": raw_output}
    except Exception as e:
        yield {"stage": "writing", "status": "error", "message": f"Writing failed: {str(e)}"}
