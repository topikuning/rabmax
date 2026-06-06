"""Stage 3-4 — Source & Builder."""

from app.services.builder.excel_writer import (
    PricedItemRecord,
    generate_workbook,
)
from app.services.builder.hsp_calculator import (
    HSPResult,
    PricedComponent,
    compute_hsp,
)
from app.services.builder.source import (
    price_match,
    source_ahsp_components,
)

__all__ = [
    "HSPResult",
    "PricedComponent",
    "PricedItemRecord",
    "compute_hsp",
    "generate_workbook",
    "price_match",
    "source_ahsp_components",
]
