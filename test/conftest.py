"""Shared fixtures for the Idea Diligence test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models import DecisionImpact, DiligenceState, EvidenceType


@pytest.fixture
def empty_state() -> DiligenceState:
    return DiligenceState(idea="A notebook app for leftover grocery ingredients")


def _add(state: DiligenceState, **kwargs) -> None:
    state.add_evidence(**kwargs)


@pytest.fixture
def go_state() -> DiligenceState:
    state = DiligenceState(idea="Waste-tracking tool for independent restaurants")
    _add(
        state,
        content="Owners describe food waste as a painful, urgent margin problem and are actively looking for help.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/waste-survey",
        confidence=0.9,
        category="problem",
    )
    _add(
        state,
        content="Users complain that incumbents are weak on waste analytics, leaving a clear gap.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/reviews",
        confidence=0.86,
        category="competitor",
    )
    _add(
        state,
        content="The category is underserved for a lightweight tool and reviews show an opportunity.",
        evidence_type=EvidenceType.INFERENCE,
        source="",
        confidence=0.6,
        category="opportunity",
    )
    _add(
        state,
        content="Pricing of $49–$99/month is viable with recurring revenue and healthy willingness to pay.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/pricing",
        confidence=0.84,
        category="pricing",
    )
    _add(
        state,
        content="Bottom-up TAM supports a large market with affordable CAC.",
        evidence_type=EvidenceType.INFERENCE,
        source="",
        confidence=0.62,
        category="market_size",
    )
    return state


@pytest.fixture
def kill_state() -> DiligenceState:
    state = DiligenceState(idea="A social network for leftover office snacks")
    _add(
        state,
        content="This is a nice to have with no demand and not a real problem.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/forums",
        confidence=0.8,
        category="problem",
    )
    _add(
        state,
        content="The market is saturated, crowded, and dominated by free alternatives.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/landscape",
        confidence=0.85,
        category="competitor",
    )
    _add(
        state,
        content="Economics are unviable: the market is too small and buyers cannot charge enough.",
        evidence_type=EvidenceType.INFERENCE,
        source="",
        confidence=0.55,
        category="pricing",
    )
    return state


@pytest.fixture
def modify_state() -> DiligenceState:
    state = DiligenceState(idea="Generic AI inventory app for all restaurants worldwide")
    _add(
        state,
        content="Independent kitchens do have a painful waste problem.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/pain",
        confidence=0.8,
        category="problem",
    )
    _add(
        state,
        content="The broader inventory suite market is crowded with many competitors and incumbents.",
        evidence_type=EvidenceType.FACT,
        source="https://example.com/competitors",
        confidence=0.83,
        category="competitor",
    )
    _add(
        state,
        content="A broad $300 suite looks unviable for independents even if a wedge could be viable.",
        evidence_type=EvidenceType.INFERENCE,
        source="",
        confidence=0.5,
        category="pricing",
    )
    state.add_unknown(
        "Will cooks actually log waste every day?",
        category="customer",
        importance=DecisionImpact.CRITICAL,
    )
    return state
