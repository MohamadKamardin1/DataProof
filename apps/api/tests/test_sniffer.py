import os

import pandas as pd

from api.sniffer import HeaderSniffer, clean_numeric_value


def test_sniffer_detects_sample_id():
    df = pd.DataFrame({"Sample ID": ["PS-01", "PS-02"], "Rb": [123, 456]})
    schema = HeaderSniffer.sniff(df)
    assert schema.columns[0].role == "sample_id"
    assert schema.columns[0].confidence == 0.95


def test_sniffer_detects_measurement_columns():
    df = pd.DataFrame({
        "Sample ID": ["PS-01", "PS-02"],
        "Rb": [123, 456],
        "Sr": [789, 101],
    })
    schema = HeaderSniffer.sniff(df)
    assert schema.columns[1].role == "measurement"
    assert schema.columns[1].confidence == 0.90
    assert schema.columns[2].role == "measurement"


def test_sniffer_element_symbols_in_parentheses():
    df = pd.DataFrame({
        "Sample ID": ["PS-01"],
        "Rb (ppm)": [123],
    })
    schema = HeaderSniffer.sniff(df)
    assert schema.columns[1].role == "measurement"
    assert schema.columns[1].unit == "ppm"


def test_sniffer_confidence_above_90_for_xrf_columns():
    df = pd.DataFrame({
        "Sample ID": ["PS-01", "PS-02", "PS-03"],
        "Rb": [123, 456, 789],
        "Sr": [101, 202, 303],
        "Ba": [1, 2, 3],
        "Al": [4, 5, 6],
        "Si": [7, 8, 9],
        "Ca": [10, 11, 12],
    })
    schema = HeaderSniffer.sniff(df)
    for col in schema.columns:
        if col.role == "measurement":
            assert col.confidence >= 0.90, f"Expected confidence >= 0.90 for {col.name}"


def test_clean_numeric_value_handles_thousands_separator():
    assert clean_numeric_value("1,234.56") == 1234.56
    assert clean_numeric_value("8,234.56") == 8234.56
    assert clean_numeric_value("9,876.54") == 9876.54


def test_clean_numeric_value_handles_plain_numbers():
    assert clean_numeric_value("87.3") == 87.3
    assert clean_numeric_value("45.2") == 45.2


def test_clean_numeric_value_handles_integers():
    assert clean_numeric_value(123) == 123.0
    assert clean_numeric_value(456.0) == 456.0


def test_clean_numeric_value_handles_none():
    assert clean_numeric_value(None) is None


def test_clean_numeric_value_handles_empty_string():
    assert clean_numeric_value("") is None
    assert clean_numeric_value("   ") is None


def test_messy_xrf_fixture_exists():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
    assert os.path.exists(fixture_path)


def test_messy_xrf_fixture_has_metadata_rows():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
    with open(fixture_path) as f:
        lines = f.readlines()
    assert lines[0].startswith("# XRF Paleosol")
    assert lines[1].startswith("# Instrument")


def test_messy_xrf_fixture_can_be_parsed():
    fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "messy_xrf.csv")
    df = pd.read_csv(fixture_path, comment="#")
    assert "Sample ID" in df.columns
    assert "Rb (ppm)" in df.columns
    assert "Sr (ppm)" in df.columns
    assert "Ba (ppm)" in df.columns
    assert "Al (ppm)" in df.columns
    assert "Si (ppm)" in df.columns
    assert "Ca (ppm)" in df.columns
    assert len(df) == 5
