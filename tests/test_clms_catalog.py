import pytest

from parseo import cli
from parseo.clms_catalog import parse_html


def test_parse_html_extracts_titles():
    html = """
    <html><body>
    <h2 class='dataset-title'>Product A</h2>
    <h2 class='dataset-title'>Product B</h2>
    <h2 class='dataset-title'>Product A</h2>
    </body></html>
    """
    assert parse_html(html) == ["Product A", "Product B"]


def test_cli_clms_products_reads_env(monkeypatch, capsys):
    monkeypatch.setenv("CLMS_DATASET_CATALOG_URL", "https://example.test/catalog")

    def fake_fetch(url=None):  # type: ignore[override]
        assert url is None
        return ["Dataset One", "Dataset Two"]

    monkeypatch.setattr("parseo.cli.fetch_clms_products", fake_fetch)
    rc = cli.main(["clms-products"])
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["Dataset One", "Dataset Two"]


def test_cli_clms_products_accepts_custom_url(monkeypatch, capsys):
    seen = {}

    def fake_fetch(url=None):  # type: ignore[override]
        seen["url"] = url
        return []

    monkeypatch.setattr("parseo.cli.fetch_clms_products", fake_fetch)
    rc = cli.main(["clms-products", "--catalog-url", "https://custom.example"])
    assert rc == 0
    assert seen["url"] == "https://custom.example"
    assert capsys.readouterr().out == ""


def test_cli_clms_products_reports_missing_url(monkeypatch):
    def fake_fetch(url=None):  # type: ignore[override]
        raise ValueError("Catalog URL not provided")

    monkeypatch.setattr("parseo.cli.fetch_clms_products", fake_fetch)
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["clms-products"])
    assert "Catalog URL not provided" in str(excinfo.value)
