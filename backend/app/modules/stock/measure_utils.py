import math
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, List, Optional


UNICODE_FRACTIONS = {
    "¼": "1/4",
    "½": "1/2",
    "¾": "3/4",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}

INCH_TO_MM = 25.4
MM_TOLERANCE = 0.35


@dataclass(frozen=True)
class MeasureNormalization:
    canonical_key: Optional[str]
    display: Optional[str]
    kind: str
    aliases: List[str]
    values_mm: List[float]


class StringClassification(Enum):
    EMPTY = "EMPTY"
    HEADER = "HEADER"
    FORMULA_ERROR = "FORMULA_ERROR"
    SUBTOTAL = "SUBTOTAL"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    CONTACT = "CONTACT"
    APPLICATION_NOTE = "APPLICATION_NOTE"
    TECHNICAL_CODE = "TECHNICAL_CODE"
    WEIGHT = "WEIGHT"
    DIMENSION = "DIMENSION"
    THICKNESS = "THICKNESS"
    LENGTH_GROUP = "LENGTH_GROUP"
    UNIT = "UNIT"
    VARIATION_GROUP = "VARIATION_GROUP"
    PRODUCT_NAME = "PRODUCT_NAME"
    CATEGORY_HEADER = "CATEGORY_HEADER"
    PRICE = "PRICE"
    QUARANTINE_CANDIDATE = "QUARANTINE_CANDIDATE"
    UNKNOWN = "UNKNOWN"


def _norm(value: Any) -> str:
    text = str(value or "").lower()
    trans = str.maketrans("áàâãäéèêëíìîïóòôõöúùûüç", "aaaaaeeeeiiiiooooouuuuc")
    return re.sub(r"\s+", " ", text).translate(trans).strip()


def classify_string(value: Optional[str]) -> StringClassification:
    text = str(value or "").strip()
    if not text:
        return StringClassification.EMPTY

    normalized = _norm(text)
    lower = normalized.lower()

    # Formula and spreadsheet error markers
    if re.search(r"#nome\?|#div/0!|#ref!|#value!|#erro|#ref|#value", lower):
        return StringClassification.FORMULA_ERROR

    # Headers and duplicated titles
    header_signals = [
        "material / descrição",
        "material/descrição",
        "material / descricao",
        "material/descricao",
        "descrição",
        "descricao",
        "produto",
        "item",
        "fornecedor",
        "atualizado",
        "empresa",
        "contato",
        "email",
        "telefone",
        "código cybersul",
        "preço",
        "preco",
        "valor",
    ]
    if any(signal in lower for signal in header_signals):
        return StringClassification.HEADER

    # Consolidation or totals
    if re.search(r"\b(subtotal|total|fechamento|consolidado|m[ée]dia|media)\b", lower):
        return StringClassification.SUBTOTAL

    # Contact information
    if re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text):
        return StringClassification.EMAIL
    if re.search(r"\b\(?\d{2,}\)?[\s\-./]*\d{4,}\b", text):
        return StringClassification.PHONE
    if re.search(r"\b(contato|telefone|fone|celular|whatsapp)\b", lower):
        return StringClassification.CONTACT

    # Application notes / observations
    if lower.startswith("p/") or lower.startswith("para ") or any(note in lower for note in ["obs:", "observa", "para etiqueta", "para colar", "plaqueta de dados"]):
        return StringClassification.APPLICATION_NOTE

    # Technical codes and isolated abbreviations with digits
    technical_code_patterns = [
        r"^f\d{3,4}[a-z]?$",
        r"^m[-\d\w]+$",
        r"^[a-z]{1,2}\d{2,4}[a-z]?$",
    ]
    if any(re.match(pattern, text, re.IGNORECASE) for pattern in technical_code_patterns) and re.search(r"\d", text):
        return StringClassification.TECHNICAL_CODE

    # Weight markers
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*kg/(?:m|barra|ch|pç|pc|chapa|pça|t|g)\s*$", lower):
        return StringClassification.WEIGHT
    if re.match(r"^\s*kg/(?:m|barra|ch|pç|pc|chapa|pça|t|g)\s*$", lower):
        return StringClassification.WEIGHT
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*kg\s*$", lower):
        return StringClassification.WEIGHT
    if re.match(r"^\s*kg\s*$", lower):
        return StringClassification.WEIGHT
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*kilo\s*$", lower):
        return StringClassification.WEIGHT

    # Dimension and thickness markers
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*(?:x|\*)\s*\d+(?:[.,]\d+)?(?:\s*(?:m|mm|cm))?\s*$", lower):
        return StringClassification.DIMENSION
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*(?:x|\*)\s*\d+(?:[.,]\d+)?\s*(?:x|\*)\s*\d+(?:[.,]\d+)?(?:\s*(?:m|mm|cm))?\s*$", lower):
        return StringClassification.DIMENSION
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*mm\s*$", lower):
        return StringClassification.THICKNESS
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*\"\s*$", text):
        return StringClassification.THICKNESS
    if re.match(r"^\s*\d+\/\d+\s*mm\s*$", lower):
        return StringClassification.THICKNESS
    if re.match(r"^\s*\d+\/\d+\"\s*$", text):
        return StringClassification.THICKNESS
    if re.match(r"^\s*\d+\.\d+\/\d+\"\s*$", text):
        return StringClassification.THICKNESS

    # Length groups such as 2 m or 3 m
    if re.match(r"^\s*\d+(?:[.,]\d+)?\s*m\s*$", lower):
        return StringClassification.LENGTH_GROUP

    # Units and plain units
    if lower in {"metro", "m", "peça", "peca", "unidade", "un", "pc", "pç", "kg", "kilo"}:
        return StringClassification.UNIT

    # Single-word variation labels
    if len(text.split()) == 1 and re.match(r"^[A-Za-zÀ-ÿ]+$", text):
        return StringClassification.VARIATION_GROUP

    # Detect product-like lines that also contain measures but are still product labels
    if re.search(r"\b\d+(?:[.,]\d+)?\s*(?:mm|cm|m)\b|\d+\/\d+\s*mm\b|\d+\/\d+\"|\d+(?:[.,]\d+)?\s*x\s*\d+(?:[.,]\d+)?\s*(?:mm|cm|m)?\b", lower) and re.search(r"[a-zà-ú]", lower):
        return StringClassification.PRODUCT_NAME

    return StringClassification.PRODUCT_NAME


def _prepare_text(value: Optional[str]) -> str:
    text = str(value or "").strip()
    for source, replacement in UNICODE_FRACTIONS.items():
        text = text.replace(source, f" {replacement}")
    return (
        text.replace("”", '"')
        .replace("“", '"')
        .replace("″", '"')
        .replace("’", "'")
        .replace("‘", "'")
        .replace("×", "x")
        .replace(" X ", " x ")
    )


def _format_mm(value: float) -> str:
    rounded = _round_mm(value)
    if abs(rounded - round(rounded)) < 0.005:
        return str(int(round(rounded)))
    text = f"{rounded:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _round_mm(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _format_inch(value: float) -> str:
    whole = int(math.floor(value + 1e-9))
    frac = value - whole
    candidates = [
        (1, 8),
        (1, 4),
        (3, 8),
        (1, 2),
        (5, 8),
        (3, 4),
        (7, 8),
    ]
    best_num = 0
    best_den = 1
    best_error = 1.0
    for num, den in candidates:
        error = abs(frac - (num / den))
        if error < best_error:
            best_num, best_den, best_error = num, den, error
    if best_error > 0.018:
        return f'{value:.2f}".'.replace('".', '"')
    if whole and best_num:
        return f'{whole}.{best_num}/{best_den}"'
    if whole:
        return f'{whole}"'
    return f'{best_num}/{best_den}"'


def _parse_number_token(token: str) -> Optional[float]:
    token = token.strip().replace(",", ".")
    if not token:
        return None
    if "/" in token:
        pieces = token.split("/")
        if len(pieces) != 2:
            return None
        try:
            den = float(pieces[1])
            return float(pieces[0]) / den if den else None
        except ValueError:
            return None
    try:
        return float(token)
    except ValueError:
        return None


def _parse_inch_segment(segment: str) -> Optional[float]:
    segment = segment.strip().replace(",", ".")
    if not segment:
        return None
    segment = re.sub(r'["\']', "", segment).strip()
    match = re.match(r"^(\d+)\s*[-. ]\s*(\d+\s*/\s*\d+)$", segment)
    if match:
        whole = _parse_number_token(match.group(1)) or 0.0
        frac = _parse_number_token(match.group(2).replace(" ", ""))
        return whole + frac if frac is not None else None
    return _parse_number_token(segment.replace(" ", ""))


def _extract_values(text: str) -> List[float]:
    # Pre-process fractions and quotes
    text = text.replace("”", '"').replace("“", '"').replace("″", '"')
    text = text.replace(" X ", " x ").replace("*", " x ")
    
    values: List[float] = []
    consumed_spans = []
    
    # 1. Multi-dimensional pattern search anywhere in the text: e.g. "3 x 1,25 m" or "0,5 x 52 x 3 mm"
    multi_pattern = re.compile(
        r"(\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)\s*x\s*(\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)\s*(?:x\s*(\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?)\s*)?\s*(mm|m|cm|pol|\"|polegada(?:s)?)\b",
        re.IGNORECASE
    )
    for match in multi_pattern.finditer(text):
        g1, g2, g3, unit = match.group(1), match.group(2), match.group(3), match.group(4).lower()
        unit_factor = 1.0
        is_inch = False
        if unit in ('pol', '"', 'polegada', 'polegadas'):
            is_inch = True
            unit_factor = INCH_TO_MM
        elif unit == 'm':
            unit_factor = 1000.0
        elif unit == 'cm':
            unit_factor = 10.0
            
        v1 = _parse_inch_segment(g1) * unit_factor if is_inch else _parse_number_token(g1) * unit_factor
        v2 = _parse_inch_segment(g2) * unit_factor if is_inch else _parse_number_token(g2) * unit_factor
        if v1 is not None and v2 is not None:
            values.append(round(v1, 4))
            values.append(round(v2, 4))
            if g3:
                v3 = _parse_inch_segment(g3) * unit_factor if is_inch else _parse_number_token(g3) * unit_factor
                if v3 is not None:
                    values.append(round(v3, 4))
            consumed_spans.append(match.span())
            break  # Only consume the first multi-dimensional match
            
    # 2. Inch pattern
    inch_pattern = re.compile(
        r"(?<!\w)(\d+(?:[.,]\d+)?(?:\s*[-. ]\s*\d+\s*/\s*\d+)?|\d+\s*/\s*\d+)\s*(?:\"|pol\b|polegada(?:s)?\b)",
        re.IGNORECASE,
    )
    for match in inch_pattern.finditer(text):
        if any(start <= match.start() < end for start, end in consumed_spans):
            continue
        value = _parse_inch_segment(match.group(1))
        if value is not None:
            values.append(round(value * INCH_TO_MM, 4))
            consumed_spans.append(match.span())
            
    # 3. MM pattern
    mm_pattern = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*mm\b", re.IGNORECASE)
    for match in mm_pattern.finditer(text):
        if any(start <= match.start() < end for start, end in consumed_spans):
            continue
        value = _parse_number_token(match.group(1))
        if value is not None:
            values.append(round(value, 4))
            consumed_spans.append(match.span())
            
    # 4. M pattern (meters)
    m_pattern = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*m\b", re.IGNORECASE)
    for match in m_pattern.finditer(text):
        if any(start <= match.start() < end for start, end in consumed_spans):
            continue
        start_idx = match.start()
        if start_idx > 0 and text[start_idx-1] in ('/', '\\'):
            continue
        value = _parse_number_token(match.group(1))
        if value is not None:
            values.append(round(value * 1000.0, 4))
            consumed_spans.append(match.span())
            
    return values[:4]


def normalize_measure(*parts: Optional[str]) -> MeasureNormalization:
    values: List[float] = []
    prepared_parts: List[str] = []
    for part in parts:
        if not part:
            continue
        prepared = _prepare_text(part)
        prepared_parts.append(prepared)
        part_values = _extract_values(prepared)
        if not values:
            values.extend(part_values)
            continue
        for value in part_values:
            rounded = _round_mm(value)
            if any(abs(rounded - _round_mm(existing)) <= 0.02 for existing in values):
                continue
            values.append(value)

    if not values:
        return MeasureNormalization(None, None, "none", [], [])

    rounded_values = [_round_mm(value) for value in values]
    kind = "complete" if len(values) >= 2 else "partial"
    canonical_values = [f"{value:.2f}" for value in rounded_values]
    canonical_key = f"{'mm' if kind == 'complete' else 'partial'}:" + "x".join(canonical_values)

    metric_joined = " x ".join(_format_mm(value) for value in rounded_values)
    display = f"{metric_joined} mm" if kind == "complete" else f"Espessura: {_format_mm(rounded_values[0])} mm"

    inch_joined = " x ".join(_format_inch(value / INCH_TO_MM) for value in rounded_values)
    aliases = {
        metric_joined,
        f"{metric_joined} mm",
        metric_joined.replace(",", "."),
        f"{metric_joined.replace(',', '.')} mm",
        inch_joined,
        inch_joined.replace('"', ""),
        _norm(metric_joined),
        _norm(inch_joined),
    }
    aliases.update(_norm(part) for part in prepared_parts if part)

    return MeasureNormalization(
        canonical_key=canonical_key,
        display=display,
        kind=kind,
        aliases=sorted(alias for alias in aliases if alias),
        values_mm=rounded_values,
    )


def measures_equivalent(left: Optional[str], right: Optional[str]) -> bool:
    left_norm = normalize_measure(left)
    right_norm = normalize_measure(right)
    if not left_norm.values_mm or len(left_norm.values_mm) != len(right_norm.values_mm):
        return False
    return all(abs(a - b) <= MM_TOLERANCE for a, b in zip(left_norm.values_mm, right_norm.values_mm))


def strip_measurements_from_name(name: str) -> str:
    if not name:
        return ""
    
    # Padrão seguro para capturar frações mistas (1.1/2"), frações simples (3/16")
    # ou valores numéricos seguidos de unidades de medida (" ou mm ou pol)
    MEASURE_PATTERN = r'(?:(?:\d+[-. ]\d+/\d+|\d+/\d+)(?:\s*(?:pol|polegada|mm|"))?|\d+(?:[.,]\d+)?\s*(?:pol|polegada|mm|"))'
    
    # 1. Remover medidas entre parênteses: e.g. " (38,1 mm x 3,18 mm)"
    cleaned = re.sub(
        r'\s*\(\s*' + MEASURE_PATTERN + r'(?:\s*x\s*' + MEASURE_PATTERN + r')?\s*\)',
        '',
        name,
        flags=re.IGNORECASE
    )
    
    # 2. Remover sufixos de medidas após traço: e.g. " - 1.1/2\" x 1/8\"" ou " - 3\""
    cleaned = re.sub(
        r'\s*-\s*' + MEASURE_PATTERN + r'(?:\s*x\s*' + MEASURE_PATTERN + r')?',
        '',
        cleaned,
        flags=re.IGNORECASE
    )
    
    # 3. Limpar espaços extras e caracteres separadores residuais nas bordas
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip(" -:,()")
    return cleaned


def is_invalid_product_name(name: Optional[str]) -> bool:
    if not name:
        return True
    name_clean = re.sub(r"\s+", " ", str(name)).strip()
    if not name_clean:
        return True
    
    name_lower = name_clean.lower()
    
    # 1. Header/Formula/Error/Consolidation
    header_keywords = [
        "material / descrição", "material/descrição", "material / descricao", "preço", 
        "final", "fornecedor", "atualizado", "empresa", "contato", "email", "telefone", 
        "#nome?", "subtotal", "total", "média", "media", "fórmula", "formula", "reajuste", 
        "ipi", "código cybersul", "fechamento", "consolidado"
    ]
    if any(k in name_lower for k in header_keywords) or name_lower.startswith("#") or "?" in name_lower:
        return True
        
    # 2. Application/Observation
    obs_keywords = ["p/placa", "p/base", "para colar", "plaqueta de dados", "para etiqueta", "observações", "observação", "obs:", "p/ etiqueta"]
    if any(k in name_lower for k in obs_keywords) or name_lower.startswith("p/") or name_lower.startswith("para "):
        return True
        
    # 3. Weight/Unit patterns
    weight_patterns = [
        r'^\s*\d+(?:[.,]\d+)?\s*kg/(?:m|barra|ch|pç|pc|chapa|pça|t|g|barra)\s*$',
        r'^\s*kg/(?:m|barra|ch|pç|pc|chapa|pça|t|g|barra)\s*$',
        r'^\s*\d+(?:[.,]\d+)?\s*kg\s*$',
        r'^\s*\d+(?:[.,]\d+)?\s*kilo\s*$',
        r'^\s*preço\s*(?:por|/)\s*(?:metro|kilo|kg)\s*$',
        r'^\s*metro\b.*$',
        r'^\s*peça\b.*$',
        r'^\s*kg\s*$',
        r'^\s*kilo\s*$',
        r'^\s*unidade\s*$',
        r'^\s*peça\s*$',
    ]
    for pattern in weight_patterns:
        if re.match(pattern, name_lower):
            return True
            
    # 4. Isolated Dimension patterns: e.g. "2 x 1,22 m" or "0,5 x 052 mm"
    dim_patterns = [
        r'^\s*\d+(?:[.,]\d+)?\s*(?:x|\*)\s*\d+(?:[.,]\d+)?(?:\s*(?:m|mm|cm))?\s*$',
        r'^\s*\d+(?:[.,]\d+)?\s*(?:x|\*)\s*\d+(?:[.,]\d+)?\s*(?:x|\*)\s*\d+(?:[.,]\d+)?(?:\s*(?:m|mm|cm))?\s*$',
    ]
    for pattern in dim_patterns:
        if re.match(pattern, name_lower):
            return True
            
    # 5. Isolated Thickness patterns: e.g. "2 mm" or "3/16\""
    thick_patterns = [
        r'^\s*\d+(?:[.,]\d+)?\s*mm\s*$',
        r'^\s*\d+/\d+\s*mm\s*$',
        r'^\s*\d+/\d+"\s*$',
        r'^\s*\d+\.\d+/\d+"\s*$',
    ]
    for pattern in thick_patterns:
        if re.match(pattern, name_lower):
            return True
            
    # 6. Technical Code isolated
    technical_codes = {"f304", "f316", "f316l", "m-2b-r", "m-2b-r-3m"}
    if name_lower in technical_codes:
        return True
        
    # 7. Technical Code with prefixes: e.g. "CS 103A", "VPC1005017", "COD3056"
    if re.match(r"^\s*[A-Z]{2,4}[-\s]?\d+", name_clean):
        return True
        
    return False


def humanize_product_name(name: Optional[str]) -> str:
    if not name:
        return ""
    name_clean = re.sub(r"\s+", " ", str(name)).strip()
    
    # 1. Normalize shorthands
    name_clean = re.sub(r'\bCh(?:\.)?\s+', 'Chapa ', name_clean, flags=re.IGNORECASE)
    name_clean = re.sub(r'\bChapa\s+de\b', 'Chapa', name_clean, flags=re.IGNORECASE)
    name_clean = re.sub(r'\bTubo\s+de\b', 'Tubo', name_clean, flags=re.IGNORECASE)
    name_clean = re.sub(r'\bGalv(?:\.)?\b', 'Galvanizado', name_clean, flags=re.IGNORECASE)
    
    # 2. Strip measurements
    name_clean = strip_measurements_from_name(name_clean)
    
    # 3. Map technical shorthands to human names if isolated
    name_upper = name_clean.upper()
    if name_upper == "F304":
        name_clean = "Fita Aço Inox 304"
    elif name_upper in ("F316", "F316L"):
        name_clean = "Fita Aço Inox 316"
        
    return name_clean


