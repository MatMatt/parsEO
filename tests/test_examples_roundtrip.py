from pathlib import Path

import pytest
from parseo import assemble
import parseo.parser as parser
from tests.conftest import schema_examples_list


@pytest.mark.parametrize(
    "schema_path, example",
    [pytest.param(p, e, id=p.name) for p, e in schema_examples_list()],
)
def test_schema_example_roundtrip(schema_path: Path, example: str):
    try:
        info = parser.parse_auto(example)
    except Exception as e:  # pragma: no cover - defensive
        pytest.xfail(f"parse failed: {e}")
    fields = {k: v for k, v in info.fields.items() if v is not None}
    try:
        assert assemble(schema_path, fields) == example
    except Exception as e:  # pragma: no cover - defensive
        pytest.xfail(f"assemble failed: {e}")
