
import pathlib, pytest
from .conftest import load_schema_by_name, match_example

SCHEMA_FILENAMES = [
    "wic_s2_filename_structure.json",
    "wic_s1_filename_structure.json",
    "wic_comb_filename_structure.json",
    "icd_filename_structure.json",
    "fsc_filename_structure.json",
    "gfsc_filename_structure.json",
    "sws_filename_structure.json",
    "wds_filename_structure.json",
    "sp_s2_filename_structure.json",
    "sp_comb_filename_structure.json",
    "cc_filename_structure.json",
]

@pytest.mark.parametrize("schema_fname", SCHEMA_FILENAMES)
def test_valid_examples_match(tmp_path, schema_fname):
    repo_root = pathlib.Path(__file__).parents[1]
    src_root = repo_root / "src"
    schema, path = load_schema_by_name(str(src_root), schema_fname)

    patt = schema["filename_pattern"]
    examples = schema.get("valid_examples", [])
    assert examples, f"No examples in {path}"
    for ex in examples:
        assert match_example(patt, ex), f"Example does not match pattern in {path}: {ex}"


