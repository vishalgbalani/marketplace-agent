"""Test script — analyzes eBay as an e-commerce marketplace."""
import asyncio
import json
import httpx

API_URL = "http://localhost:8000/analyze"


async def main():
    payload = {
        "company_name": "eBay",
        "marketplace_type": "E-Commerce",
        "focus_area": "seller experience",
    }

    print(f"Analyzing: {payload['company_name']} ({payload['marketplace_type']})")
    print(f"Focus: {payload.get('focus_area', 'None')}")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=300) as client:
        async with client.stream("POST", API_URL, json=payload) as response:
            if response.status_code != 200:
                print(f"Error: {response.status_code}")
                text = await response.aread()
                print(text.decode())
                return

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                try:
                    event = json.loads(line[6:])
                except json.JSONDecodeError:
                    continue

                stage = event.get("stage")
                status = event.get("status")
                message = event.get("message", "")

                if stage == "done":
                    data = event["data"]
                    print("\n" + "=" * 60)
                    print(f"MARKETPLACE ANALYSIS: {data['company_name']}")
                    print(f"Type: {data['marketplace_type']}")
                    print("=" * 60)
                    print(f"\nOverview:\n{data['marketplace_overview']}")

                    for section, key in [
                        ("Supply-Side Analysis", "supply_side_analysis"),
                        ("Demand-Side Analysis", "demand_side_analysis"),
                        ("Unit Economics Signals", "unit_economics_signals"),
                        ("Network Effects", "network_effects"),
                        ("Competitive Moats", "competitive_moats"),
                        ("Vulnerabilities", "vulnerabilities"),
                        ("Hiring Signals", "hiring_signals"),
                        ("Growth Levers", "growth_levers"),
                        ("Strategic Risks", "strategic_risks"),
                        ("PM Recommendations", "pm_recommendations"),
                    ]:
                        print(f"\n{section}:")
                        for item in data.get(key, []):
                            print(f"  → {item}")

                    print(f"\nSupply-Side Sentiment:\n{data.get('supply_side_sentiment', 'N/A')}")
                    print(f"\nData Sources: {', '.join(data.get('data_sources_used', []))}")
                    print(f"Sources: {len(data.get('sources', []))} URLs collected")
                else:
                    icon = "✓" if status == "complete" else "⟳" if status == "running" else "✗"
                    print(f"  [{icon}] {message}")


if __name__ == "__main__":
    asyncio.run(main())
