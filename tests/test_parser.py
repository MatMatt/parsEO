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
