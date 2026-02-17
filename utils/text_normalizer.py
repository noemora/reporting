"""Text normalization and cleaning utilities."""
import unicodedata
import pandas as pd


class TextNormalizer:
    """Handles text normalization and cleaning operations."""
    
    @staticmethod
    def normalize_column_name(value: str) -> str:
        """Normalize column names to make validation more tolerant."""
        value = TextNormalizer.fix_mojibake(value)
        value = value.strip().lower()
        value = unicodedata.normalize("NFKD", value)
        cleaned_chars = []
        for ch in value:
            if unicodedata.combining(ch):
                continue
            if ch.isalnum():
                cleaned_chars.append(ch)
            else:
                cleaned_chars.append(" ")
        value = "".join(cleaned_chars)
        value = " ".join(value.split())
        return value
    
    @staticmethod
    def fix_mojibake(value: str) -> str:
        """Fix common mojibake sequences for Spanish accents."""
        replacements = {
            "\xc3\xa1": "á",  # Ã¡ -> á
            "\xc3\xa9": "é",  # Ã© -> é
            "\xc3\xad": "í",  # Ã­ -> í
            "\xc3\xb3": "ó",  # Ã³ -> ó
            "\xc3\xba": "ú",  # Ãº -> ú
            "\xc3\xb1": "ñ",  # Ã± -> ñ
            "\xc3\x93": "Ó",  # Ã" -> Ó
            "\xc3\x9a": "Ú",  # Ãš -> Ú
            "\xc3\x81": "Á",  # Ã -> Á
            "\xc3\x89": "É",  # Ã‰ -> É
            "\xc3\x91": "Ñ",  # Ã' -> Ñ
        }
        for bad, good in replacements.items():
            value = value.replace(bad, good)
        return value
    
    @staticmethod
    def clean_text_series(data: pd.Series) -> pd.Series:
        """Clean text column values."""
        cleaned = data.astype(str).str.strip()
        cleaned = cleaned.replace("nan", pd.NA)
        return cleaned
    
    @staticmethod
    def normalize_environment(value: str) -> str:
        """Normalize environment names."""
        return str(value).strip().lower().replace("ó", "o")
