import json

import parseo.schema_registry as schema_registry


def test_new_schema_discovery(tmp_path, monkeypatch):
    pkg_name = "tmp_pkg"
    pkg_dir = tmp_path / pkg_name
    (pkg_dir / "schemas").mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("")

    monkeypatch.syspath_prepend(tmp_path)

    schema_registry.clear_cache()
    assert schema_registry.list_schema_families(pkg=pkg_name) == []

    schema_v1 = {
        "schema_id": "x:y:abc",
        "schema_version": "1.0.0",
        "status": "current",
        "template": "ABC_{id}.txt",
        "fields": {"id": {"pattern": "[A-Z]+"}},
    }
    (pkg_dir / "schemas" / "abc_filename_v1_0_0.json").write_text(json.dumps(schema_v1))

    schema_registry.clear_cache()
    fams = schema_registry.list_schema_families(pkg=pkg_name)
    assert "ABC" in fams
    path1 = schema_registry.get_schema_path("abc", pkg=pkg_name)
    assert path1.name == "abc_filename_v1_0_0.json"

    schema_v2 = schema_v1 | {"schema_version": "2.0.0"}
    schema_v2["status"] = "current"
    schema_v1["status"] = "deprecated"
    (pkg_dir / "schemas" / "abc_filename_v1_0_0.json").write_text(json.dumps(schema_v1))
    (pkg_dir / "schemas" / "abc_filename_v2_0_0.json").write_text(json.dumps(schema_v2))

    schema_registry.clear_cache()
    path2 = schema_registry.get_schema_path("abc", pkg=pkg_name)
    assert path2.name == "abc_filename_v2_0_0.json"

