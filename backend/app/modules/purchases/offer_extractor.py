"""Extracao deterministica de campos comerciais de paginas de produto."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


@dataclass(frozen=True)
class ExtractedPriceCondition:
    condition_type: str
    amount: Decimal
    installments: int | None = None
    installment_amount: Decimal | None = None
    discount_percent: Decimal | None = None
    source_label: str | None = None
    evidence_status: str = "confirmed"


@dataclass(frozen=True)
class ExtractedOffer:
    title: str | None
    store_name: str | None
    price_conditions: list[ExtractedPriceCondition]
    recommended_condition: str | None


def _money(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    cleaned = re.sub(r"[^\d,\.]", "", raw)
    if not cleaned:
        return None
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def _text(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _json_ld_prices(html: str) -> list[ExtractedPriceCondition]:
    conditions: list[ExtractedPriceCondition] = []
    for match in re.finditer(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(?P<body>[\s\S]*?)</script>",
        html,
        flags=re.IGNORECASE,
    ):
        try:
            data = json.loads(match.group("body").strip())
        except Exception:
            continue
        nodes = data if isinstance(data, list) else [data]
        for node in nodes:
            offers = node.get("offers") if isinstance(node, dict) else None
            if isinstance(offers, dict):
                offers = [offers]
            for offer in offers or []:
                price = _money(str(offer.get("price") or ""))
                if price is None:
                    continue
                conditions.append(ExtractedPriceCondition("current", price, source_label="dados estruturados"))
    return conditions


def extract_offer_from_html(html: str, *, url: str | None = None, fallback_title: str | None = None) -> ExtractedOffer:
    plain = _text(html)
    conditions = _json_ld_prices(html)

    title = None
    title_match = re.search(r"<title[^>]*>(?P<title>.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group("title")).strip()

    previous_patterns = [
        r"(?:de|preco anterior|preco riscado|valor anterior)\s*r?\$?\s*([\d\.\,]+)",
    ]
    pix_patterns = [
        r"r?\$?\s*([\d\.\,]+)\s*(?:no\s+)?(?:pix|a vista no pix|à vista no pix)",
        r"(?:pix|a vista no pix|à vista no pix|preco no pix|preco pix)\s*(?:por|:|-)?\s*r?\$?\s*([\d\.\,]+)",
    ]
    card_patterns = [
        r"r?\$?\s*([\d\.\,]+)\s*(?:parcelado|no\s+cartao|cartao)",
        r"(?:cartao|cartao de credito|parcelado)\s*(?:por|:|-)?\s*r?\$?\s*([\d\.\,]+)",
    ]
    current_patterns = [
        r"(?:por|preco|valor)\s*r?\$?\s*([\d\.\,]+)",
    ]

    def add_first(patterns: list[str], condition_type: str, source_label: str) -> None:
        for pattern in patterns:
            match = re.search(pattern, plain, flags=re.IGNORECASE)
            if not match:
                continue
            amount = _money(match.group(1))
            if amount is None:
                continue
            if not any(c.condition_type == condition_type and c.amount == amount for c in conditions):
                conditions.append(ExtractedPriceCondition(condition_type, amount, source_label=source_label))
            return

    add_first(previous_patterns, "previous", "preco anterior")
    add_first(pix_patterns, "pix", "preco Pix")
    add_first(card_patterns, "card", "preco cartao")
    if not conditions:
        add_first(current_patterns, "current", "preco anunciado")

    recommended = None
    for preferred in ("pix", "boleto", "current", "card"):
        if any(c.condition_type == preferred for c in conditions):
            recommended = preferred
            break
    if recommended is None and conditions:
        candidates = [c for c in conditions if c.condition_type != "previous"] or conditions
        recommended = min(candidates, key=lambda c: c.amount).condition_type

    return ExtractedOffer(
        title=title or fallback_title,
        store_name=None,
        price_conditions=conditions,
        recommended_condition=recommended,
    )
