# Marketplace Intelligence Agent — Architecture Spec

Build a complete production-ready Marketplace Intelligence Agent that analyzes ANY marketplace business — from food delivery to e-commerce to travel. Given a company name, marketplace type, and optional focus area, it produces a structured strategic analysis covering supply/demand dynamics, unit economics signals, network effects, competitive moats, and strategic risks.

This is a portfolio-grade product, not a tutorial project. The output should read like a senior marketplace PM's strategic briefing.

## Architecture

Three-agent pipeline using the OpenAI Agents SDK, with THREE data-gathering tools:

### Tools

**Tool 1: Tavily Web Search (Primary Intelligence)**
Searches the open web for company news, earnings commentary, strategy, and competitive landscape. The Researcher MUST run 6-8 targeted searches per company, adapting queries to the marketplace type.

For ALL marketplace types:
- "[company] earnings call revenue take rate GMV 2025 2026"
- "[company] marketplace strategy product launches 2025 2026"
- "[company] competitors competitive landscape market share"
- "[company] regulatory challenges antitrust 2025 2026"
- "[company] AI investments machine learning data science"

Vertical-specific searches:

E-Commerce (eBay, Amazon, Etsy, Mercari, Poshmark):
- "[company] seller fees policy changes commission structure"
- "[company] seller experience third party marketplace"
- "[company] buyer protection authentication program"
- "[company] advertising revenue promoted listings"
- "[company] fulfillment logistics shipping strategy"

Food Delivery (DoorDash, Uber Eats, Grubhub, SkipTheDishes):
- "[company] driver courier pay model tips"
- "[company] restaurant commission fees partnership"
- "[company] delivery fee pricing strategy subsidy"
- "[company] grocery convenience retail expansion"

Ride-Hailing (Uber, Lyft, Bolt):
- "[company] driver earnings surge pricing model"
- "[company] autonomous vehicles robotaxi strategy"
- "[company] rider retention pricing strategy"
- "[company] regulatory labor classification"

Travel (Airbnb, Booking.com, Hopper, VRBO, Expedia):
- "[company] host acquisition supply growth strategy"
- "[company] commission fee structure take rate"
- "[company] travel fintech insurance attach rate"
- "[company] regulatory short term rental restrictions"

Grocery (Instacart, Walmart, Amazon Fresh):
- "[company] shopper pay batch order model"
- "[company] grocery delivery profitability unit economics"
- "[company] retail media advertising revenue"
- "[company] partnership grocery chain expansion"

Services (Upwork, Fiverr, TaskRabbit, Thumbtack):
- "[company] freelancer fees service charges take rate"
- "[company] enterprise managed services strategy"
- "[company] AI matching quality scoring"
- "[company] freelancer retention churn platform switching"

**Tool 2: Reddit Sentiment Search (via Tavily)**
Uses Tavily to search Reddit specifically for supply-side sentiment. This surfaces insights that news articles miss — actual experiences from marketplace participants.

The tool runs 2-3 targeted Tavily searches scoped to Reddit using site:reddit.com:

Subreddit targeting by marketplace type:
- Food Delivery → "site:reddit.com/r/doordash_drivers OR site:reddit.com/r/UberEATS OR site:reddit.com/r/grubhubdrivers"
- Ride-Hailing → "site:reddit.com/r/uberdrivers OR site:reddit.com/r/lyftdrivers"
- E-Commerce → "site:reddit.com/r/eBaySellers OR site:reddit.com/r/AmazonSeller OR site:reddit.com/r/Etsy OR site:reddit.com/r/FulfillmentByAmazon"
- Travel → "site:reddit.com/r/AirbnbHosts OR site:reddit.com/r/vrbo OR site:reddit.com/r/travel"
- Grocery → "site:reddit.com/r/InstacartShoppers OR site:reddit.com/r/grocery"
- Services → "site:reddit.com/r/Upwork OR site:reddit.com/r/freelance OR site:reddit.com/r/TaskRabbit"
- General fallback → "site:reddit.com/r/gig_economy"

Search queries:
- "[company] site:reddit.com/r/[relevant_subreddits]" (general sentiment)
- "[company] fees changes complaints site:reddit.com" (pain points)
- "[company] vs [known competitor] site:reddit.com" (competitive switching)

IMPORTANT: Reddit skews negative — people post when frustrated, not when satisfied. The Analyst prompt must account for this bias and weight specific factual claims (fee changes, policy updates, earnings data) over general complaints.

**Tool 3: JSearch Job Postings (via RapidAPI)**
Uses the JSearch API (endpoint: https://jsearch.p.rapidapi.com/search) to pull actual current job postings. Job postings are leading indicators of company strategy.

Implementation:
```python
@function_tool
def search_job_postings(company_name: str) -> str:
    """Search for recent job postings to identify strategic hiring signals."""
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": os.getenv("JSEARCH_API_KEY"),
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": f"{company_name} jobs",
        "num_pages": 1,
        "date_posted": "month"
    }
    response = requests.get(url, headers=headers, params=params)
    results = response.json().get("data", [])
    # Format: job title, location, posted date
    # Limit to 20 most recent
```

The Analyst should interpret hiring patterns by vertical:

E-Commerce hiring signals:
- Trust & Safety roles → authentication/fraud investment
- Ads/Monetization roles → promoted listings expansion
- Payments/Fintech roles → managed payments evolution
- Seller Experience PM roles → supply-side investment
- ML/Search roles → discovery algorithm investment

Food Delivery hiring signals:
- ML/Pricing roles → algorithmic pricing investment
- Operations in new cities → geographic expansion
- Restaurant partnerships → supply acquisition push
- Autonomous/Robotics roles → automation strategy

Travel hiring signals:
- Fintech/Insurance roles → attach rate strategy
- Revenue Management roles → pricing sophistication
- Host/Supply roles → supply acquisition
- ML/Personalization → recommendation engine investment

General signals:
- Heavy ML/AI hiring → algorithmic investment
- Operations roles in new cities → geographic expansion
- Customer support cuts → automation push
- Product manager roles mentioning specific areas → strategic priorities
- Data engineering hiring → data infrastructure build-out

### Agents

1. **Marketplace Researcher** — orchestrates all three tools to gather comprehensive intelligence. Runs Tavily web searches first for broad context, then Tavily Reddit searches for supply-side sentiment, then JSearch for hiring signals. Synthesizes all findings into a research summary clearly labeling which data came from which source (Web, Reddit, Job Postings).

2. **Marketplace Strategist** — takes research findings and analyzes through a senior marketplace PM lens. Must explicitly consider:
   - Supply-side dynamics (acquisition, retention, churn, multi-tenanting behavior)
   - Demand-side patterns (frequency, basket size/AOV, retention, price sensitivity)
   - Unit economics signals (take rate trends, contribution margin, subsidy dependency, path to profitability)
   - Network effects (local vs global, cross-side vs same-side, liquidity thresholds)
   - Competitive moats (data advantages, supply lock-in, brand, switching costs, regulatory capture)
   - Disintermediation risks (where value leaks off-platform, direct relationships)
   - Reddit sentiment calibration (weight factual claims over general complaints, note negativity bias)
   - Hiring signals (what job postings reveal about strategic direction and investment areas)
   - Vertical-specific dynamics:
     - E-Commerce: seller tools ecosystem, advertising/monetization flywheel, authentication/trust, managed payments
     - Food Delivery: restaurant economics, delivery radius optimization, grocery/retail expansion
     - Travel: rate parity, channel management, fintech attach, regulatory by market
     - Services: quality matching, managed services vs open marketplace, skill verification

   If a focus area is provided, weight analysis toward that area.

3. **Strategy Writer** — produces a structured strategic briefing using Pydantic output model. Writes like a senior strategy consultant, not a generic AI summary. Uses specific data points from the research, not vague generalizations.

## Pydantic Output Models

```python
class MarketplaceAnalysis(BaseModel):
    company_name: str
    marketplace_type: str  # e.g. "two-sided e-commerce marketplace", "three-sided food delivery marketplace"
    marketplace_overview: str  # 3-5 sentences: what it is, who the sides are, how value flows, current scale
    supply_side_analysis: List[str]  # 5-7 insights on seller/driver/host dynamics — include Reddit sentiment where relevant
    demand_side_analysis: List[str]  # 5-7 insights on buyer/rider/guest behavior, acquisition channels, retention
    unit_economics_signals: List[str]  # 5-7 signals on take rate, margins, CAC/LTV from earnings and news
    network_effects: List[str]  # 3-5 observations on local vs global, cross-side vs same-side, liquidity
    competitive_moats: List[str]  # 3-5 what's defensible (data, brand, supply lock-in, switching costs)
    vulnerabilities: List[str]  # 3-5 what's vulnerable (disintermediation, regulatory, margin pressure, commoditization)
    hiring_signals: List[str]  # 3-5 insights from job postings about strategic direction and investment priorities
    supply_side_sentiment: str  # 2-3 paragraph summary of Reddit sentiment from workers/sellers/hosts, explicitly noting negativity bias and distinguishing factual claims from complaints
    growth_levers: List[str]  # 5-7 opportunities (new verticals, pricing, geographic expansion, ad monetization, fintech)
    strategic_risks: List[str]  # 3-5 biggest risks (regulatory, competitive, structural, technological disruption)
    pm_recommendations: List[str]  # 5-7 specific recommendations for what a PM at this company should focus on
    data_sources_used: List[str]  # Which sources contributed: "Web Search", "Reddit Sentiment", "Job Postings"
    sources: List[str]  # URLs of sources used (web + reddit links)
```

## Production Setup

1. `app/main.py` — FastAPI server with CORS, GET /health, POST /analyze endpoint with SSE streaming. Add IP-based rate limiting: 3 requests per IP per day with friendly 429 JSON message: {"error": "Daily limit reached (3 analyses per day). This is a free demo — thanks for trying it!"}
2. `app/pipeline.py` — Three-agent pipeline using factory pattern for the Researcher. Async generator yielding stage events with descriptive messages:
   - "Searching web for company intelligence..."
   - "Scanning Reddit for supply-side sentiment..."
   - "Analyzing job postings for hiring signals..."
   - "Marketplace strategist is analyzing dynamics..."
   - "Writing strategic briefing..."
3. `app/models.py` — MarketplaceRequest and MarketplaceAnalysis Pydantic models
4. `index.html` — Professional frontend with:
   - Title: "Marketplace Intelligence Agent"
   - Subtitle: "Strategic analysis of marketplace dynamics — built for marketplace PMs, operators, and investors."
   - Company name input (required), placeholder "e.g. DoorDash, eBay, Airbnb, Uber, Etsy"
   - Marketplace type dropdown: "E-Commerce", "Food Delivery", "Ride-Hailing", "Travel", "Grocery", "Services", "Other"
   - Optional focus area input, placeholder "e.g. seller experience, pricing strategy, supply acquisition, advertising monetization"
   - "Analyze Marketplace" button
   - Streaming progress indicators showing each data source being queried
   - Formatted output with clear section headers, each field in its own card/section
   - Supply-side sentiment section should have a visually distinct background (light yellow or amber) with a small note: "Source: Reddit communities — note: Reddit sentiment skews negative"
   - Hiring signals section should have a note: "Source: Live job postings via JSearch"
   - A "Data Sources" badge area showing which sources successfully contributed (checkmarks for each: Web, Reddit, Jobs)
   - Footer: "Powered by GPT-4o-mini · Tavily · Reddit · JSearch"
5. `test_api.py` — Test script that analyzes "eBay" as an e-commerce marketplace
6. `Procfile`, `railway.toml`, `requirements.txt`

## Key Details

- Use `from agents import Agent, Runner, function_tool` (NOT openai_agents)
- Use gpt-4o-mini as the model (cost efficiency)
- API keys loaded from environment: OPENAI_API_KEY, TAVILY_API_KEY, JSEARCH_API_KEY
- Unique session ID per request via uuid
- SSE streams real-time status updates showing which data source is currently being queried
- The Researcher agent's instructions must tell it to use ALL THREE tools and clearly label which data came from which source
- The Researcher should adapt its search queries based on the marketplace_type provided
- The Researcher should run tools in order: Tavily web → Tavily Reddit → JSearch
- Test script should use "eBay" as default company to verify e-commerce vertical works

## Error Handling

Each tool should have try/except blocks. If Reddit-scoped search or JSearch fails:
- Log the error
- Return a message like "Reddit sentiment data unavailable for this query" or "Job posting data unavailable"
- Continue the pipeline with remaining data sources
- The final output should note which sources were successfully queried in data_sources_used
- The Data Sources badges on the frontend should reflect which sources actually returned data

This graceful degradation is critical — the agent should ALWAYS produce output even if 1-2 data sources fail. Tavily web search alone should produce a useful baseline analysis.

## Cost Management Notes

- gpt-4o-mini keeps LLM costs under $0.01 per analysis
- Tavily free tier: 1,000 searches/month (each analysis uses ~10 searches including Reddit)
- JSearch free tier: 500 requests/month (each analysis uses ~2 calls)
- Rate limiting at 3/IP/day prevents runaway costs from LinkedIn traffic
- All API costs scale linearly — monitor RapidAPI dashboard for usage

Deliver all files ready to run locally and deploy to Railway.
