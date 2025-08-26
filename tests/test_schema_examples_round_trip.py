import parseo.parser as parser
from parseo.parser import parse_auto
from parseo import assemble


def test_schema_examples_round_trip():
    pkg = parser.__package__
    parser._get_schema_paths.cache_clear()
    for schema_path in parser._get_schema_paths(pkg):
        schema = parser._load_json_from_path(schema_path)
        examples = schema.get("examples")
        if not isinstance(examples, list):
            continue
        for example in examples:
            if not isinstance(example, str):
                continue
            result = parse_auto(example)
            assert result.valid, f"Parsing failed for {example}"
            fields = {k: v for k, v in result.fields.items() if v is not None}
            assembled = assemble(schema_path, fields)
            assert assembled == example

