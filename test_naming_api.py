import pytest
from naming_api import generate_sentinel_filename, parse_sentinel_filename_verbose


def test_generate_sentinel1_filename_round_trip():
    filename = generate_sentinel_filename(
        satellite="S1A",
        mode="IW",
        product_type="GRDH",
        resolution="HIGH",
        sensing_start="2023-09-15 10:15:30",
        orbit_number=1,
        data_take_id="0001D5",
        processing_baseline="N0200",
        product_discriminator="ABCD",
    )
    assert filename == "S1A_IW_GRDH_HIGH_20230915T101530_R001_0001D5_ABCD"
    parsed = parse_sentinel_filename_verbose(filename)
    assert parsed["Satellite"].startswith("Satellite: S1A")
    assert parsed["Mode"].startswith("Mode: IW")


def test_generate_sentinel2_filename_round_trip():
    expected = (
        "S2B_MSIL2A_20250814T103629_N0511_R008_T33VVJ_20250814T114103.SAFE"
    )
    filename = generate_sentinel_filename(
        satellite="S2B",
        product_type="MSI",
        level="L2A",
        sensing_start="2025-08-14 10:36:29",
        processing_baseline="N0511",
        orbit_number=8,
        tile_id="T33VVJ",
        product_discriminator="20250814T114103",
    )
    assert filename == expected
    parsed = parse_sentinel_filename_verbose(filename)
    assert parsed["Instrument"].startswith("Instrument: MSI")
    assert parsed["Level"].startswith("Product Level: L2A")