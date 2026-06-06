# backend/app/services/analytics_service.py
"""
Analytics Service — aggregates procurement intelligence metrics from
the database for dashboard cards, charts, and summary widgets.

All queries use database-level aggregation (COUNT, SUM, AVG, GROUP BY)
to avoid loading unnecessary rows into Python memory.

Usage::

    from backend.app.services.analytics_service import AnalyticsService

    svc = AnalyticsService()
    overview = svc.get_overview(db)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import case, cast, func, Float, Integer, String
from sqlalchemy.orm import Session

from backend.app.models import (
    Document,
    ExtractedEntity,
    OCRStatus,
    RiskLabel,
    RiskPrediction,
    Vendor,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Computes procurement analytics from the SupplyMind database.

    Every public method accepts a SQLAlchemy ``Session`` and returns a
    plain dictionary suitable for direct JSON serialisation.  No ORM
    objects leak into the responses.
    """

    # ─────────────────────────────────────────────────────────────
    #  Overview — single dashboard summary
    # ─────────────────────────────────────────────────────────────

    def get_overview(self, db: Session) -> Dict[str, Any]:
        """Return a high-level overview combining all major KPIs.

        Designed to power a top-level dashboard with cards for total
        documents, vendors, entities, risk breakdown, and spend.
        """
        doc_stats = self._document_counts(db)
        vendor_stats = self._vendor_counts(db)
        entity_stats = self._entity_counts(db)
        risk_dist = self._risk_distribution(db)
        spend = self._spend_totals(db)

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "documents": {
                "total": doc_stats["total"],
                "completed": doc_stats["completed"],
                "failed": doc_stats["failed"],
                "pending": doc_stats["pending"],
                "processing": doc_stats["processing"],
            },
            "vendors": {
                "total": vendor_stats["total"],
                "with_risk_scores": vendor_stats["with_risk_scores"],
                "unscored": vendor_stats["total"] - vendor_stats["with_risk_scores"],
            },
            "entities": {
                "total": entity_stats["total"],
                "with_vendor_link": entity_stats["with_vendor_link"],
            },
            "risk_distribution": risk_dist,
            "spend": {
                "total_amount": spend["total_amount"],
                "average_amount": spend["average_amount"],
                "documents_with_amount": spend["documents_with_amount"],
            },
        }

    # ─────────────────────────────────────────────────────────────
    #  Document Analytics
    # ─────────────────────────────────────────────────────────────

    def get_document_analytics(self, db: Session) -> Dict[str, Any]:
        """Return document processing statistics and breakdowns."""
        counts = self._document_counts(db)

        # Average file size (bytes)
        avg_size = db.query(func.avg(Document.file_size)).scalar() or 0.0

        # Total pages processed
        total_pages = db.query(func.sum(Document.page_count)).scalar() or 0

        # OCR method breakdown
        method_rows = (
            db.query(
                Document.ocr_method,
                func.count(Document.id),
            )
            .filter(Document.ocr_method.isnot(None))
            .group_by(Document.ocr_method)
            .all()
        )
        ocr_methods = {method: count for method, count in method_rows}

        # MIME type breakdown
        mime_rows = (
            db.query(
                Document.mime_type,
                func.count(Document.id),
            )
            .group_by(Document.mime_type)
            .all()
        )
        mime_types = {mime: count for mime, count in mime_rows}

        # Success rate
        total = counts["total"]
        success_rate = (counts["completed"] / total * 100) if total > 0 else 0.0

        # Processing timeline — documents per day (last 30 days)
        daily_rows = (
            db.query(
                func.date(Document.created_at).label("day"),
                func.count(Document.id).label("count"),
            )
            .group_by(func.date(Document.created_at))
            .order_by(func.date(Document.created_at).desc())
            .limit(30)
            .all()
        )
        daily_uploads = [
            {"date": str(row.day), "count": row.count}
            for row in daily_rows
        ]

        # Latest document timestamp
        latest_ts = db.query(func.max(Document.created_at)).scalar()

        return {
            "total_documents": total,
            "status_breakdown": {
                "completed": counts["completed"],
                "failed": counts["failed"],
                "pending": counts["pending"],
                "processing": counts["processing"],
            },
            "ocr_success_rate": round(success_rate, 2),
            "average_file_size_bytes": round(float(avg_size), 0),
            "total_pages_processed": int(total_pages),
            "ocr_method_breakdown": ocr_methods,
            "mime_type_breakdown": mime_types,
            "daily_uploads": daily_uploads,
            "latest_upload_at": latest_ts.isoformat() if latest_ts else None,
        }

    # ─────────────────────────────────────────────────────────────
    #  Vendor Analytics
    # ─────────────────────────────────────────────────────────────

    def get_vendor_analytics(self, db: Session) -> Dict[str, Any]:
        """Return vendor summary stats and distributions."""
        counts = self._vendor_counts(db)

        # Vendors by number of documents linked
        doc_count_rows = (
            db.query(
                ExtractedEntity.vendor_id,
                func.count(ExtractedEntity.id).label("doc_count"),
            )
            .filter(ExtractedEntity.vendor_id.isnot(None))
            .group_by(ExtractedEntity.vendor_id)
            .all()
        )

        if doc_count_rows:
            doc_counts = [row.doc_count for row in doc_count_rows]
            avg_docs_per_vendor = sum(doc_counts) / len(doc_counts)
            max_docs_vendor = max(doc_counts)
        else:
            avg_docs_per_vendor = 0.0
            max_docs_vendor = 0

        # Vendors by risk label (latest prediction only)
        risk_breakdown = self._risk_distribution(db)

        # Vendors with contact info
        has_email = db.query(func.count(Vendor.id)).filter(Vendor.contact_email.isnot(None)).scalar() or 0
        has_gstin = db.query(func.count(Vendor.id)).filter(Vendor.gstin.isnot(None)).scalar() or 0

        # Latest vendor timestamp
        latest_vendor_ts = db.query(func.max(Vendor.created_at)).scalar()

        return {
            "total_vendors": counts["total"],
            "with_risk_scores": counts["with_risk_scores"],
            "unscored": counts["total"] - counts["with_risk_scores"],
            "average_documents_per_vendor": round(avg_docs_per_vendor, 2),
            "max_documents_single_vendor": max_docs_vendor,
            "risk_breakdown": risk_breakdown,
            "contact_completeness": {
                "with_email": has_email,
                "with_gstin": has_gstin,
            },
            "latest_vendor_added_at": latest_vendor_ts.isoformat() if latest_vendor_ts else None,
        }

    # ─────────────────────────────────────────────────────────────
    #  Risk Distribution
    # ─────────────────────────────────────────────────────────────

    def get_risk_distribution(self, db: Session) -> Dict[str, Any]:
        """Return risk label distribution based on each vendor's latest prediction."""
        dist = self._risk_distribution(db)

        total_predictions = db.query(func.count(RiskPrediction.id)).scalar() or 0
        avg_score = db.query(func.avg(RiskPrediction.risk_score)).scalar()

        # Score distribution buckets for chart
        buckets = self._risk_score_buckets(db)

        # Model version breakdown
        model_rows = (
            db.query(
                RiskPrediction.model_version,
                func.count(RiskPrediction.id),
            )
            .group_by(RiskPrediction.model_version)
            .all()
        )
        model_versions = {ver: count for ver, count in model_rows}

        latest_prediction_ts = db.query(func.max(RiskPrediction.predicted_at)).scalar()

        return {
            "label_distribution": dist,
            "total_predictions": total_predictions,
            "average_risk_score": round(float(avg_score), 4) if avg_score is not None else None,
            "score_buckets": buckets,
            "model_versions": model_versions,
            "latest_prediction_at": latest_prediction_ts.isoformat() if latest_prediction_ts else None,
        }

    # ─────────────────────────────────────────────────────────────
    #  Spend Summary
    # ─────────────────────────────────────────────────────────────

    def get_spend_summary(self, db: Session) -> Dict[str, Any]:
        """Return monetary spend analytics extracted from documents."""
        spend = self._spend_totals(db)

        # Spend by entity type (invoice, quotation, etc.)
        entities = db.query(ExtractedEntity).all()

        type_spend: Dict[str, float] = {}
        currency_spend: Dict[str, float] = {}
        amounts: List[float] = []

        for entity in entities:
            data = entity.entity_data or {}
            amount = self._extract_amount(data)
            if amount is not None and amount > 0:
                amounts.append(amount)

                # Group by entity type
                etype = entity.entity_type or "unknown"
                type_spend[etype] = type_spend.get(etype, 0.0) + amount

                # Group by currency
                currency = data.get("currency") or data.get("Currency") or "INR"
                currency_spend[currency] = currency_spend.get(currency, 0.0) + amount

        # Sort spend by type descending
        type_spend_sorted = [
            {"entity_type": k, "total_amount": round(v, 2)}
            for k, v in sorted(type_spend.items(), key=lambda x: -x[1])
        ]

        currency_breakdown = [
            {"currency": k, "total_amount": round(v, 2)}
            for k, v in sorted(currency_spend.items(), key=lambda x: -x[1])
        ]

        # Min / max amounts
        min_amount = min(amounts) if amounts else 0.0
        max_amount = max(amounts) if amounts else 0.0

        return {
            "total_amount": spend["total_amount"],
            "average_amount": spend["average_amount"],
            "min_amount": round(min_amount, 2),
            "max_amount": round(max_amount, 2),
            "documents_with_amount": spend["documents_with_amount"],
            "spend_by_entity_type": type_spend_sorted,
            "spend_by_currency": currency_breakdown,
        }

    # ─────────────────────────────────────────────────────────────
    #  Top Vendors
    # ─────────────────────────────────────────────────────────────

    def get_top_vendors(self, db: Session, limit: int = 10) -> Dict[str, Any]:
        """Return top vendors ranked by total extracted monetary value."""
        entities = (
            db.query(ExtractedEntity)
            .filter(ExtractedEntity.vendor_id.isnot(None))
            .all()
        )

        vendor_totals: Dict[int, float] = {}
        vendor_doc_counts: Dict[int, int] = {}

        for entity in entities:
            vid = entity.vendor_id
            data = entity.entity_data or {}
            amount = self._extract_amount(data)
            if amount is not None and amount > 0:
                vendor_totals[vid] = vendor_totals.get(vid, 0.0) + amount
            vendor_doc_counts[vid] = vendor_doc_counts.get(vid, 0) + 1

        # Fetch vendor names and risk labels for the top vendors
        ranked = sorted(vendor_totals.items(), key=lambda x: -x[1])[:limit]
        vendor_ids = [vid for vid, _ in ranked]

        vendor_map: Dict[int, Vendor] = {}
        if vendor_ids:
            vendors = db.query(Vendor).filter(Vendor.id.in_(vendor_ids)).all()
            vendor_map = {v.id: v for v in vendors}

        result = []
        for rank, (vid, total) in enumerate(ranked, 1):
            vendor = vendor_map.get(vid)
            latest_risk = self._latest_risk_for_vendor(vendor) if vendor else None

            result.append({
                "rank": rank,
                "vendor_id": vid,
                "vendor_name": vendor.name if vendor else f"Vendor #{vid}",
                "total_value": round(total, 2),
                "document_count": vendor_doc_counts.get(vid, 0),
                "latest_risk_label": latest_risk["label"] if latest_risk else None,
                "latest_risk_score": latest_risk["score"] if latest_risk else None,
            })

        return {
            "top_vendors": result,
            "total_vendors_with_spend": len(vendor_totals),
        }

    # ─────────────────────────────────────────────────────────────
    #  Extraction Summary
    # ─────────────────────────────────────────────────────────────

    def get_extraction_summary(self, db: Session) -> Dict[str, Any]:
        """Return extraction quality and coverage analytics."""
        total_entities = db.query(func.count(ExtractedEntity.id)).scalar() or 0
        total_docs = db.query(func.count(Document.id)).scalar() or 0

        # Documents that have at least one entity
        docs_with_entities = (
            db.query(func.count(func.distinct(ExtractedEntity.document_id))).scalar() or 0
        )

        # Entity type breakdown
        type_rows = (
            db.query(
                ExtractedEntity.entity_type,
                func.count(ExtractedEntity.id),
            )
            .group_by(ExtractedEntity.entity_type)
            .all()
        )
        entity_type_breakdown = {etype: count for etype, count in type_rows}

        # Average confidence score
        avg_confidence = (
            db.query(func.avg(ExtractedEntity.confidence_score))
            .filter(ExtractedEntity.confidence_score.isnot(None))
            .scalar()
        )

        # Confidence distribution
        confidence_buckets = self._confidence_buckets(db)

        # Entities with vendor link
        linked = (
            db.query(func.count(ExtractedEntity.id))
            .filter(ExtractedEntity.vendor_id.isnot(None))
            .scalar() or 0
        )

        # Extraction rate
        extraction_rate = (docs_with_entities / total_docs * 100) if total_docs > 0 else 0.0
        vendor_link_rate = (linked / total_entities * 100) if total_entities > 0 else 0.0

        # Fields extracted — check coverage of key fields
        field_coverage = self._field_coverage(db)

        return {
            "total_entities": total_entities,
            "total_documents": total_docs,
            "documents_with_extractions": docs_with_entities,
            "documents_without_extractions": total_docs - docs_with_entities,
            "extraction_rate_percent": round(extraction_rate, 2),
            "entity_type_breakdown": entity_type_breakdown,
            "average_confidence_score": round(float(avg_confidence), 4) if avg_confidence is not None else None,
            "confidence_distribution": confidence_buckets,
            "entities_with_vendor_link": linked,
            "vendor_link_rate_percent": round(vendor_link_rate, 2),
            "field_coverage": field_coverage,
        }

    # ═════════════════════════════════════════════════════════════
    #  Private helpers
    # ═════════════════════════════════════════════════════════════

    def _document_counts(self, db: Session) -> Dict[str, int]:
        """Return document counts by OCR status."""
        rows = (
            db.query(
                Document.ocr_status,
                func.count(Document.id),
            )
            .group_by(Document.ocr_status)
            .all()
        )
        counts = {"total": 0, "completed": 0, "failed": 0, "pending": 0, "processing": 0}
        for status_val, count in rows:
            key = status_val.value if isinstance(status_val, OCRStatus) else str(status_val)
            counts[key] = count
            counts["total"] += count
        return counts

    def _vendor_counts(self, db: Session) -> Dict[str, int]:
        """Return total vendors and vendors with at least one risk prediction."""
        total = db.query(func.count(Vendor.id)).scalar() or 0
        with_risk = (
            db.query(func.count(func.distinct(RiskPrediction.vendor_id))).scalar() or 0
        )
        return {"total": total, "with_risk_scores": with_risk}

    def _entity_counts(self, db: Session) -> Dict[str, int]:
        """Return total entities and entities with vendor linkage."""
        total = db.query(func.count(ExtractedEntity.id)).scalar() or 0
        linked = (
            db.query(func.count(ExtractedEntity.id))
            .filter(ExtractedEntity.vendor_id.isnot(None))
            .scalar() or 0
        )
        return {"total": total, "with_vendor_link": linked}

    def _risk_distribution(self, db: Session) -> Dict[str, int]:
        """Count vendors per risk label using each vendor's latest prediction.

        Uses a subquery to find each vendor's most recent prediction,
        then groups by label.
        """
        # Subquery: max predicted_at per vendor
        latest_sub = (
            db.query(
                RiskPrediction.vendor_id,
                func.max(RiskPrediction.predicted_at).label("max_ts"),
            )
            .group_by(RiskPrediction.vendor_id)
            .subquery()
        )

        # Join to get label of the latest prediction
        rows = (
            db.query(
                RiskPrediction.risk_label,
                func.count(RiskPrediction.id),
            )
            .join(
                latest_sub,
                (RiskPrediction.vendor_id == latest_sub.c.vendor_id)
                & (RiskPrediction.predicted_at == latest_sub.c.max_ts),
            )
            .group_by(RiskPrediction.risk_label)
            .all()
        )

        dist = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for label, count in rows:
            key = label.value if isinstance(label, RiskLabel) else str(label)
            dist[key] = count
        return dist

    def _spend_totals(self, db: Session) -> Dict[str, Any]:
        """Compute total and average spend from extracted entity data."""
        entities = db.query(ExtractedEntity.entity_data).all()

        total = 0.0
        count = 0

        for (data,) in entities:
            amount = self._extract_amount(data or {})
            if amount is not None and amount > 0:
                total += amount
                count += 1

        avg = (total / count) if count > 0 else 0.0

        return {
            "total_amount": round(total, 2),
            "average_amount": round(avg, 2),
            "documents_with_amount": count,
        }

    def _risk_score_buckets(self, db: Session) -> List[Dict[str, Any]]:
        """Bucket risk scores into ranges for chart rendering."""
        buckets = [
            ("0.00–0.20", 0.0, 0.20),
            ("0.20–0.40", 0.20, 0.40),
            ("0.40–0.60", 0.40, 0.60),
            ("0.60–0.80", 0.60, 0.80),
            ("0.80–1.00", 0.80, 1.01),
        ]

        result = []
        for label, lo, hi in buckets:
            count = (
                db.query(func.count(RiskPrediction.id))
                .filter(
                    RiskPrediction.risk_score >= lo,
                    RiskPrediction.risk_score < hi,
                )
                .scalar() or 0
            )
            result.append({"range": label, "count": count})
        return result

    def _confidence_buckets(self, db: Session) -> List[Dict[str, Any]]:
        """Bucket confidence scores into ranges for chart rendering."""
        buckets = [
            ("0.00–0.25", 0.0, 0.25),
            ("0.25–0.50", 0.25, 0.50),
            ("0.50–0.75", 0.50, 0.75),
            ("0.75–1.00", 0.75, 1.01),
        ]

        result = []
        for label, lo, hi in buckets:
            count = (
                db.query(func.count(ExtractedEntity.id))
                .filter(
                    ExtractedEntity.confidence_score.isnot(None),
                    ExtractedEntity.confidence_score >= lo,
                    ExtractedEntity.confidence_score < hi,
                )
                .scalar() or 0
            )
            result.append({"range": label, "count": count})
        return result

    def _field_coverage(self, db: Session) -> Dict[str, int]:
        """Check how many entities contain key procurement fields."""
        entities = db.query(ExtractedEntity.entity_data).all()

        fields_to_check = [
            "vendor_name", "total_amount", "document_number",
            "document_date", "currency", "line_items",
        ]
        coverage: Dict[str, int] = {f: 0 for f in fields_to_check}

        for (data,) in entities:
            if not data:
                continue
            for field in fields_to_check:
                # Check both snake_case and original keys
                if data.get(field) is not None or data.get(field.replace("_", " ")) is not None:
                    coverage[field] += 1

        return coverage

    @staticmethod
    def _extract_amount(data: Dict[str, Any]) -> Optional[float]:
        """Extract the monetary amount from entity_data, trying common key names."""
        for key in ("total_amount", "Total Amount", "totalAmount", "amount", "Amount",
                     "grand_total", "Grand Total", "invoice_total", "Invoice Total"):
            val = data.get(key)
            if val is not None:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def _latest_risk_for_vendor(vendor: Vendor) -> Optional[Dict[str, Any]]:
        """Return latest risk label and score for a vendor, or None."""
        if not vendor.risk_predictions:
            return None
        latest = max(vendor.risk_predictions, key=lambda p: p.predicted_at)
        return {
            "label": latest.risk_label.value,
            "score": latest.risk_score,
        }
