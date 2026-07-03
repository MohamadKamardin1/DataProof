import re
from dataclasses import dataclass

import pandas as pd


@dataclass
class ColumnGuess:
    name: str
    role: str  # "sample_id", "measurement", "ignore"
    confidence: float
    unit: str | None = None
    data_type: str | None = None


@dataclass
class SchemaGuess:
    columns: list[ColumnGuess]


class HeaderSniffer:
    """Heuristic-based column type detection for scientific CSV/XLSX data."""

    # Known element symbols (chemistry) that often appear in measurement headers
    ELEMENT_SYMBOLS = {
        "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
        "Na", "Mg", "Al", "Si", "P", "S", "Cl", "K", "Ca", "Sc",
        "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga",
        "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb",
        "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb",
        "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm",
        "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
        "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl",
        "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa",
        "U", "Np", "Pu",
    }

    # Unit patterns commonly found in column headers
    UNIT_PATTERNS = {
        "ppm": r"\(ppm\)|\s+ppm$|ppm",
        "ppb": r"\(ppb\)|\s+ppb$|ppb",
        "%": r"\(%\)|\s+%$|wt%|weight%",
        "mg/g": r"\(mg/g\)|mg/g",
        "mg/kg": r"\(mg/kg\)|mg/kg",
        "mg/L": r"\(mg/L\)|mg/L",
        "wt%": r"\(wt%\)|wt%",
    }

    @classmethod
    def sniff(cls, df: pd.DataFrame) -> SchemaGuess:
        columns = []
        for col in df.columns:
            guess = cls._guess_column(col, df[col])
            columns.append(guess)
        return SchemaGuess(columns=columns)

    @classmethod
    def _guess_column(cls, name: str, series: pd.Series) -> ColumnGuess:
        clean_name = str(name).strip()
        upper_name = clean_name.upper()

        # 1. Check for Sample ID (highest priority)
        if cls._is_sample_id(clean_name, upper_name):
            return ColumnGuess(
                name=clean_name,
                role="sample_id",
                confidence=0.95,
                data_type="string",
            )

        # 2. Check if it's a measurement column
        is_measurement, unit = cls._is_measurement(clean_name, upper_name)
        if is_measurement:
            return ColumnGuess(
                name=clean_name,
                role="measurement",
                confidence=0.90,
                unit=unit,
                data_type="numeric",
            )

        # 3. Check if it's numeric data (fallback)
        if cls._is_numeric(series):
            return ColumnGuess(
                name=clean_name,
                role="measurement",
                confidence=0.70,
                unit=None,
                data_type="numeric",
            )

        return ColumnGuess(
            name=clean_name,
            role="ignore",
            confidence=0.50,
            data_type="string",
        )

    @classmethod
    def _is_sample_id(cls, clean_name: str, upper_name: str) -> bool:
        sample_id_patterns = [
            "SAMPLE ID", "SAMPLE_ID", "SAMPLEID", "SAMPLE",
            "SAMPLE NO", "SAMPLE NO.", "SAMPLE NUMBER",
            "ID", "IDENTIFIER", "SAMPLE NAME", "SAMPLE_CODE",
        ]
        return any(pattern in upper_name for pattern in sample_id_patterns)

    @classmethod
    def _is_measurement(cls, clean_name: str, upper_name: str) -> tuple[bool, str | None]:
        for elem in cls.ELEMENT_SYMBOLS:
            patterns = [
                rf"^{re.escape(elem)}$",
                rf"^{re.escape(elem)}\b",
                rf"\b{re.escape(elem)}\b",
                rf"\({re.escape(elem)}\)",
            ]
            for pattern in patterns:
                if re.search(pattern, clean_name, re.IGNORECASE):
                    unit = cls._extract_unit(clean_name)
                    return True, unit

        measurement_words = {"CONC", "CONCENTRATION", "VALUE", "AMOUNT", "MEASURE"}
        for word in measurement_words:
            if word in upper_name:
                unit = cls._extract_unit(clean_name)
                return True, unit

        return False, None

    @classmethod
    def _extract_unit(cls, header: str) -> str | None:
        for _unit_name, pattern in cls.UNIT_PATTERNS.items():
            if re.search(pattern, header, re.IGNORECASE):
                match = re.search(pattern, header, re.IGNORECASE)
                if match:
                    return match.group(0).strip("() ").lower()
        return None

    @classmethod
    def _is_numeric(cls, series: pd.Series) -> bool:
        non_null = series.dropna()
        if len(non_null) == 0:
            return False
        numeric = pd.to_numeric(non_null, errors="coerce")
        return numeric.notna().mean() >= 0.70


def clean_numeric_value(value) -> float | None:
    """Clean a raw string value into a float, handling common messiness."""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    if s.count(",") == 1 and s.count(".") == 0:
        parts = s.split(",")
        if len(parts[-1]) == 3 and all(p.isdigit() for p in parts):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    elif s.count(",") >= 1:
        s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None
