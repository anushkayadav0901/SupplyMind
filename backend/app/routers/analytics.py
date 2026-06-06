# backend/app/routers/analytics.py
"""
Analytics API — procurement intelligence endpoints for dashboard
visualisations and aggregated insights.

Endpoints:
    GET /analytics/overview             — top-level KPI summary
    GET /analytics/documents            — document processing stats
    GET /analytics/vendors              — vendor summary analytics
    GET /analytics/risk-distribution    — risk label + score distribution
    GET /analytics/spend-summary        — monetary spend analytics
    GET /analytics/top-vendors          — top vendors by total value
    GET /analytics/extraction-summary   — extraction quality metrics
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from backend.app.dependencies import DbSession
from backend.app.schemas import (
    AnalyticsOverviewResponse,
    DocumentAnalyticsResponse,
    ExtractionSummaryResponse,
    RiskDistributionResponse,
    SpendSummaryResponse,
    TopVendorsResponse,
    VendorAnalyticsResponse,
)
from backend.app.services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ── Service singleton ──────────────────────────────────────────
_analytics_service: Optional[AnalyticsService] = None


def _get_analytics_service() -> AnalyticsService:
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service


# =====================================================================
#  GET /analytics/overview
# =====================================================================

@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Dashboard overview — all key KPIs",
    description=(
        "Returns a single aggregated response containing document counts, "
        "vendor stats, risk distribution, and spend totals.  Designed for "
        "the main dashboard landing page."
    ),
)
def get_overview(db: DbSession) -> dict:
    """Top-level dashboard summary with all critical procurement KPIs."""
    svc = _get_analytics_service()
    return svc.get_overview(db)


# =====================================================================
#  GET /analytics/documents
# =====================================================================

@router.get(
    "/documents",
    response_model=DocumentAnalyticsResponse,
    summary="Document processing statistics",
    description=(
        "Detailed document analytics including status breakdown, "
        "OCR method distribution, MIME types, success rate, "
        "daily upload trends, and average file sizes."
    ),
)
def get_document_analytics(db: DbSession) -> dict:
    """Document processing pipeline analytics."""
    svc = _get_analytics_service()
    return svc.get_document_analytics(db)


# =====================================================================
#  GET /analytics/vendors
# =====================================================================

@router.get(
    "/vendors",
    response_model=VendorAnalyticsResponse,
    summary="Vendor summary analytics",
    description=(
        "Vendor distribution metrics including risk breakdown, "
        "document linkage stats, and contact completeness."
    ),
)
def get_vendor_analytics(db: DbSession) -> dict:
    """Vendor intelligence summary."""
    svc = _get_analytics_service()
    return svc.get_vendor_analytics(db)


# =====================================================================
#  GET /analytics/risk-distribution
# =====================================================================

@router.get(
    "/risk-distribution",
    response_model=RiskDistributionResponse,
    summary="Risk label and score distribution",
    description=(
        "Risk analytics across all vendors — label distribution, "
        "score histograms, average scores, and model version breakdown."
    ),
)
def get_risk_distribution(db: DbSession) -> dict:
    """Risk distribution analysis."""
    svc = _get_analytics_service()
    return svc.get_risk_distribution(db)


# =====================================================================
#  GET /analytics/spend-summary
# =====================================================================

@router.get(
    "/spend-summary",
    response_model=SpendSummaryResponse,
    summary="Monetary spend analytics",
    description=(
        "Spend analytics derived from extracted document data — "
        "total procurement value, averages, breakdowns by entity "
        "type and currency."
    ),
)
def get_spend_summary(db: DbSession) -> dict:
    """Procurement spend analysis."""
    svc = _get_analytics_service()
    return svc.get_spend_summary(db)


# =====================================================================
#  GET /analytics/top-vendors
# =====================================================================

@router.get(
    "/top-vendors",
    response_model=TopVendorsResponse,
    summary="Top vendors by total procurement value",
    description=(
        "Returns vendors ranked by total extracted monetary value. "
        "Includes document counts and latest risk status per vendor."
    ),
)
def get_top_vendors(
    db: DbSession,
    limit: int = Query(default=10, ge=1, le=50, description="Number of top vendors to return"),
) -> dict:
    """Top vendors ranked by total extracted value."""
    svc = _get_analytics_service()
    return svc.get_top_vendors(db, limit=limit)


# =====================================================================
#  GET /analytics/extraction-summary
# =====================================================================

@router.get(
    "/extraction-summary",
    response_model=ExtractionSummaryResponse,
    summary="Entity extraction quality and coverage",
    description=(
        "Extraction pipeline analytics — entity type breakdown, "
        "confidence distribution, vendor linkage rates, and "
        "field-level coverage stats."
    ),
)
def get_extraction_summary(db: DbSession) -> dict:
    """Extraction quality and coverage analytics."""
    svc = _get_analytics_service()
    return svc.get_extraction_summary(db)
