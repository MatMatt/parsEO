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
