from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DuesAgeingBands(BaseModel):
    band_0_30_days: Decimal
    band_31_60_days: Decimal
    band_61_90_days: Decimal
    band_90_plus_days: Decimal
    total_outstanding: Decimal


class FinancialMetrics(BaseModel):
    total_billed: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    collection_rate_percent: Decimal
    ageing: DuesAgeingBands


class ComplaintsMetrics(BaseModel):
    total_complaints: int
    open_unresolved_count: int
    closed_resolved_count: int
    overdue_count: int
    reopened_count: int
    reopened_rate_percent: Decimal
    mean_resolution_hours: Decimal | None = None
    median_resolution_hours: Decimal | None = None
    mean_first_response_hours: Decimal | None = None


class PaymentMatchingMetrics(BaseModel):
    total_rows_imported: int
    auto_matched_count: int
    review_queue_count: int
    manually_approved_count: int
    held_or_rejected_count: int
    auto_match_coverage_percent: Decimal


class ClientTargetComparison(BaseModel):
    kpi_name: str
    client_target_description: str
    demo_sample_value: str
    target_status_label: str = "Client target, not an achieved result"


class CommitteeReportResponse(BaseModel):
    reporting_period: str  # e.g. "2026-11"
    generated_at_utc: datetime
    data_cutoff_time: str
    timezone: str = "Asia/Kolkata"
    financials: FinancialMetrics
    complaints: ComplaintsMetrics
    payment_matching: PaymentMatchingMetrics
    client_targets: list[ClientTargetComparison]
    kpi_definitions: dict[str, str]
