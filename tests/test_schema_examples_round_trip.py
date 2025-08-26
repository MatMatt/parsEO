import parseo.parser as parser


def test_schema_examples_round_trip():
    failures = parser.validate_schema_examples()
    assert not failures, failures

