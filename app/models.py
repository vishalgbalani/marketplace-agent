from pydantic import BaseModel
from typing import List, Optional


class MarketplaceRequest(BaseModel):
    company_name: str
    marketplace_type: str
    focus_area: Optional[str] = None


class MarketplaceAnalysis(BaseModel):
    company_name: str
    marketplace_type: str
    marketplace_overview: str
    supply_side_analysis: List[str]
    demand_side_analysis: List[str]
    unit_economics_signals: List[str]
    network_effects: List[str]
    competitive_moats: List[str]
    vulnerabilities: List[str]
    hiring_signals: List[str]
    supply_side_sentiment: str
    growth_levers: List[str]
    strategic_risks: List[str]
    pm_recommendations: List[str]
    data_sources_used: List[str]
    sources: List[str]
