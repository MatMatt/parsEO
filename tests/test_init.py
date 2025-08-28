def test_star_import_exposes_parser():
    import parseo

    ns = {}
    exec("from parseo import *", ns)

    assert ns["parser"] is parseo.parser


def test_info_reports_version():
    """The info function should return the installed package version."""
    import parseo
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version

    try:
        expected = version("parseo")
    except PackageNotFoundError:
        expected = "unknown"

    assert parseo.info()["version"] == expected
