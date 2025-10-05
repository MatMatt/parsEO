<div align="center">

# parsEO

**parsEO** is a Python toolkit that parses existing Earth Observation filenames into structured metadata and assembles new filenames from validated fields. Filename rules live in JSON schemas, turning the repository into a single source of truth for product nomenclature.

</div>

## Why parsEO?

- **Bidirectional workflows** – convert filenames to Python dictionaries and rebuild filenames from the same fields.
- **Schema-driven** – JSON schemas define every product token, validation rule, and STAC link. Drop in a new schema file and it is discovered automatically.
- **Extensible** – contributions focus on data, not glue code. Adding support for a new mission only requires a schema.

## Supported product families

- **Sentinel missions** – S1, S2, S3, S4, S5P, S6
- **Landsat** – LT04, LT05, LE07, LC08, LC09
- **NASA MODIS** – Terra and Aqua MODIS products
- **EUMETSAT missions** – MTG, Metop
- **Copernicus Land Monitoring Service (CLMS)**
  - Corine Land Cover (CLC) and CLC+ Raster
  - European Ground Motion Service (EGMS) Level 2 basic/calibrated products, Level 3 velocity grid, and GNSS model
  - Urban Atlas Land Cover / Land Use
  - High Resolution Vegetation Phenology & Productivity (HR-VPP): Seasonal Trajectories (PPI) and Vegetation Indices (FAPAR, LAI, NDVI, PPI, FCOVER, DMP)
  - High Resolution Water & Snow / Ice (HR-WSI): CC, FSC, GFSC, ICD, SWS, WDS, WIC, WIC-COMB, SP_S2, SP_COMB
  - High Resolution Layers (HRL): Forest Type, Grassland, Imperviousness, Non-Vegetated Land Cover Characteristics, Tree Cover Density, Water & Wetness, Small Woody Features

## Installation

```bash
pip install parseo
```

For development installs:

```bash
git clone https://github.com/MatMatt/parsEO.git
cd parsEO
pip install -e .
```

Confirm the CLI is available:

```bash
parseo --version
```

## Quick start

### Parse a filename

```python
from parseo import parse_auto

name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
result = parse_auto(name)

print(result.valid)   # True
print(result.fields)  # structured dict of extracted fields
```

Another example using a MODIS filename:

```python
from parseo import parse_auto

name = "MOD09GA.A2021123.h18v04.006.2021132234506.hdf"
result = parse_auto(name)

print(result.fields["platform"])  # MOD
print(result.fields["product"])   # 09
print(result.fields["variant"])   # GA
```

The MODIS schema advertises the Processing, Sat, Raster, and Electro-Optical STAC extensions, enabling automated STAC metadata generation (`processing`, `sat`, `raster`, `eo`).

### Assemble a filename

```python
from parseo import assemble, assemble_auto

fields = {
    "platform": "S2B",
    "instrument": "MSI",
    "processing_level": "L2A",
    "sensing_datetime": "20241123T224759",
    "processing_baseline": "N0511",
    "relative_orbit": "R101",
    "mgrs_tile": "T03VUL",  # MGRS tile (TxxYYY, e.g. T32TNS)
    "generation_datetime": "20241123T230829",
    "extension": "SAFE",
}

assemble_auto(fields)
# 'S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE'

assemble(fields, family="S2")
# Uses the default (current) Sentinel-2 schema for quicker resolution.

assemble(fields, family="S2", version="1.0.0")
# Lock both family and schema version explicitly.
```

To force a specific schema file:

```python
from pathlib import Path
from parseo import assemble

schema_path = Path("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")
filename = assemble(fields, schema_path=schema_path)
```

`parse_auto` reports the schema version and lifecycle status that were used:

```python
from parseo import parse_auto

result = parse_auto("S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE")
print(result.version)  # '1.0.0'
print(result.status)   # 'current'
```

### Command-line interface

The same functionality is exposed through the CLI.

```bash
# Parse a filename
parseo parse S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE

# Assemble using a JSON document with the required fields
parseo assemble --family S2 fields.json
```

### Working with specific schema versions

When multiple schema versions are present, parsEO chooses the one whose `status` is `"current"`. If none are marked current, the highest `schema_version` wins. You can always pin a schema by passing `schema_path` to `assemble` or `parse`.

## Authoring new schemas

Adding a schema requires only a JSON document under `src/parseo/schemas/`. Start from an existing product schema or the skeleton in `template/`.

1. **Create the product directory** – `src/parseo/schemas/<family>/<mission>/<product>/` (only the family level is mandatory).
2. **Write the versioned schema file** – `<product>_filename_vX_Y_Z.json` with required metadata (`schema_id`, `schema_version`, `status`, optional `stac_version`, `stac_extensions`, and `description`).
3. **Describe fields inline** – each entry inside `"fields"` combines JSON Schema keywords (`type`, `pattern`, `enum`, …) and optional documentation.
4. **List required fields** – populate the top-level `"required"` array; everything else is optional.
5. **Link to STAC metadata** – set `stac_map` to connect filename tokens to STAC properties. For patterns, capture groups (`$1`, `$2`, …) can be reused in the mapping.
6. **Define the template** – provide a `"template"` string that arranges `{field}` placeholders. Optional components can be wrapped with square brackets, e.g. `[.{extension}]`.
7. **Add examples** – populate `"examples"` with valid filenames covering typical combinations of optional tokens.
8. **Maintain versions** – mark the latest schema as `"current"` and move older ones to `"deprecated"` (or similar). parsEO uses these flags to pick defaults.
9. **Test round-trips** – run `parseo parse <filename>` and `parseo assemble --schema <schema_path>` to confirm the schema behaves as expected.

### Choosing `enum` vs. `pattern`

- Use `enum` for short, controlled vocabularies such as file extensions or processing modes. It keeps validation strict and self-documenting.
- Use `pattern` for structured tokens like timestamps (`^\d{8}T\d{6}$`), version identifiers (`^V\d{3}$`), or grid identifiers (`^h\d{2}v\d{2}$`).

Example excerpt:

```jsonc
"prefix": {
  "type": "string",
  "pattern": "^(MOD|MYD|MCD)$",
  "stac_map": {
    "MOD": {"platform": "Terra", "instrument": "MODIS"},
    "MYD": {"platform": "Aqua", "instrument": "MODIS"},
    "MCD": {"platform": "Combined", "instrument": "MODIS"}
  }
},
"tile": {
  "type": "string",
  "pattern": "^(h\d{2})(v\d{2})$",
  "stac_map": {
    "tile": "$0",
    "horizontal_grid": "$1",
    "vertical_grid": "$2"
  }
}
```

## Contributing

- Place new schemas under `src/parseo/schemas/<product_family>/`.
- Include at least one positive example in each schema file.
- Run the test-suite with `pytest` (and `ruff check .` for linting) before opening a pull request.
- Submit a pull request describing the new products or fixes.

## License

This project is licensed under the [European Union Public Licence v1.2](LICENSE.txt).
