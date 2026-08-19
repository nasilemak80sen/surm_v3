"""
SURM application configuration.

This module contains static reference data used by the application.

It should NOT contain user-specific study data.
"""

from __future__ import annotations


# ============================================================================
# DISCIPLINES
# ============================================================================

DISCIPLINES = [
    "Geology",
    "Geophysics",
    "Geomechanics",
    "PP",
    "RE",
    "PT",
    "PT/PP",
    "PT/RE",
]


# ============================================================================
# RISK CATEGORIES
# ============================================================================

RISKS = [
    "Resource",
    "Production",
    "Recovery",
    "Development",
    "Economics",
    "Schedule",
    "Well",
    "Facilities",
    "HSE",
    "Integrity",
    "Data",
    "Technology",
]


# ============================================================================
# APPLICATION MAPPING
# ============================================================================

SURM_MAPPING = {
    "disciplines": DISCIPLINES,
    "risks": RISKS,
}


def get_mapping() -> dict:
    """
    Return the application's static mapping.

    A new dictionary is returned so callers cannot accidentally
    mutate the global configuration object.
    """

    return {
        "disciplines": list(DISCIPLINES),
        "risks": list(RISKS),
    }