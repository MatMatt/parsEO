from parseo.parser import parse_auto

def test_s2_example():
    name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S2B"
    assert res.fields["processing_level"] == "MSIL2A"

def test_s1_example():
    name = "S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S1A"
    assert res.fields["sar_instrument_mode"] == "IW"
    assert res.fields["processing_level"] == "1SDV"


def test_s3_example():
    name = "S3A_OLCI_L2_20250105T103021_080_SEG01.tif"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S3A"
    assert res.match_family == "S3"


def test_s4_example():
    name = "S4A_UVN_L2_20250105T103021_EUROPE.tif"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S4A"
    assert res.match_family == "S4"


def test_s5p_example():
    name = "S5P_TROPOMI_L2_NO2_20250105T103021.nc"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S5P"
    assert res.match_family == "S5P"


def test_s6_example():
    name = "S6A_P4_20HzN_20221015T103529_20221015T112143_0001.nc"
    res = parse_auto(name)
    assert res is not None
    assert res.fields["platform"] == "S6A"
    assert res.match_family == "S6"
