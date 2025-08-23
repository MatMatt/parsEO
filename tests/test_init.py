def test_star_import_exposes_parser():
    import parseo

    ns = {}
    exec("from parseo import *", ns)

    assert ns["parser"] is parseo.parser
