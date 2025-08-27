# parsEO

**parsEO** is a Python package for **parsing and assembling filenames** of satellite data and derived products.  
It also serves as an **authoritative definition of filename structures** through machine-readable JSON schemas.

---

## Features

- **Bidirectional support**:  
  Parse existing product filenames into structured fields, and assemble new filenames from fields.

- **Schema-driven**:  
  Filename rules are defined in JSON schema files under `src/parseo/schemas/`.  
  Adding support for a new product = adding a schema, no Python code changes required.

- **Flexible folder structure**:  
  parsEO does not assume a fixed folder depth. Products can live in arbitrary directory structures,  
  and the schema only describes the filename itself.

- **Extensible**:  
  New Copernicus or Landsat product families can be added by dropping schema definitions into the repo.

---

## Currently Supported Products

- **Sentinel missions**: S1, S2, S3, S4, S5P, S6  
- **Landsat**: LT04, LT05, LE07, LC08, LC09  
- **NASA MODIS**: Terra/Aqua MODIS products
- **EUMETSAT missions**: MTG, Metop
- **Copernicus Land Monitoring Service (CLMS)**:
  - Corine Land Cover (CLC)
  - High Resolution Vegetation Phenology & Productivity (HR-VPP)
  - High Resolution Water & Snow / Ice (HR-WSI)
  - High Resolution Layers (HRL)
---

## Installation

```bash
pip install parseo
```

For development:

```bash
git clone https://github.com/MatMatt/parsEO.git
cd parsEO
pip install -e .
```

---

## Usage

### Parse a filename

```python
from parseo import parse_auto

name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
res = parse_auto(name)

print(res.valid)   # True
print(res.fields)  # structured dict of extracted fields
```

Example for a MODIS product:

```python
name = "MOD09GA.A2021123.h18v04.006.2021132234506.hdf"
res = parse_auto(name)
print(res.fields["platform"])  # MOD
print(res.fields["product"])   # 09
print(res.fields["variant"])   # GA
```

### Assemble a filename

```python
from pathlib import Path
from parseo import assemble

schema_path = Path("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")

fields = {
    "platform": "S2B",
    "sensor": "MSI",
    "processing_level": "L2A",
    "sensing_datetime": "20241123T224759",
    "processing_baseline": "N0511",
    "relative_orbit": "R101",
    "mgrs_tile": "T03VUL",  # MGRS tile (TxxYYY, e.g., T32TNS)
    "generation_datetime": "20241123T230829",
    "extension": "SAFE",
}

filename = assemble(schema_path, fields)
print(filename)
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

Automatic schema selection:

```python
from parseo import assemble_auto

fields = {
    "platform": "S2B",
    "sensor": "MSI",
    "processing_level": "L2A",
    "sensing_datetime": "20241123T224759",
    "processing_baseline": "N0511",
    "relative_orbit": "R101",
    "mgrs_tile": "T03VUL",
    "generation_datetime": "20241123T230829",
    "extension": "SAFE",
}

filename = assemble_auto(fields)
print(filename)
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

### Validate schema examples

When adding a new schema, use `validate_schema_examples` to ensure that the
filenames listed under its `examples` section still parse and reassemble
correctly.

```python
from parseo.parser import validate_schema_examples

validate_schema_examples("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")
```

The project's tests call this helper so that schema examples stay in sync with
the parser over time.

### Run as a web API

parsEO functions can be exposed through a web service. The example below uses
[FastAPI](https://fastapi.tiangolo.com), which provides an automatic Swagger UI
for trying out the endpoints.

```python
# file: main.py
from fastapi import FastAPI
from parseo import assemble, parse_auto

app = FastAPI()


@app.get("/parse")
def parse_endpoint(name: str):
    res = parse_auto(name)
    return res.model_dump()


@app.post("/assemble")
def assemble_endpoint(schema: str, fields: dict):
    filename = assemble(schema, fields)
    return {"filename": filename}
```

Start the server and open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
to access Swagger UI:

```bash
uvicorn main:app --reload
```

The interactive page lets you call `/parse` and `/assemble` directly from the
browser to verify your API.

### List STAC collections

Use the ``list-stac-collections`` subcommand to list collection IDs exposed by a
STAC API. The STAC root URL must be supplied via ``--stac-url``:

```bash
parseo list-stac-collections --stac-url https://catalogue.dataspace.copernicus.eu/stac
```
```
AQUA
CCM
CLMS
COP-DEM
ENVISAT
GLOBAL-MOSAICS
LANDSAT-5
LANDSAT-7
...

```

Each collection ID is printed on its own line.

### Sample filenames from a STAC collection

The ``stac-sample`` subcommand prints a few asset filenames from a STAC
collection. The STAC API root must always be provided via ``--stac-url``
(with or without a trailing slash):

```bash
parseo stac-sample SENTINEL-2 --samples 3 --stac-url https://catalogue.dataspace.copernicus.eu/stac

```
Which might output:

```
SENTINEL-2:
  S2A_MSIL1C_20210101T101031_N0209_R122_T33UUU_20210101T121023.SAFE
  S2B_MSIL1C_20210101T101031_N0209_R122_T33UUU_20210101T121023.SAFE
  S2A_MSIL1C_20210102T101031_N0209_R122_T33UUU_20210102T121023.SAFE
```

Asset filenames are taken from each asset's ``title`` when available; if not,
the filename is parsed from the ``href``.  OData-style links such as
``Products('NAME')/$value`` are handled automatically.

Known collection aliases are automatically mapped to their official STAC IDs:

| Alias | STAC ID |
|-------|---------|
| `SENTINEL2_L2A` | `sentinel-2` |

A different STAC service can be targeted by supplying its URL:

```bash
parseo stac-sample my-collection --samples 2 --stac-url https://stac.example.com
```

### Search STAC and download assets

The ``parseo.stac_scraper`` module provides helpers for programmatic
interaction with a STAC API.  The snippet below lists available collections
and downloads the first asset matching a simple search:

```python
from parseo import stac_scraper

stac_url = "https://catalogue.dataspace.copernicus.eu/stac"

# List available collections and download the first matching asset for each
for cid in stac_scraper.list_collections_client(stac_url):
    print(cid)
    stac_scraper.search_stac_and_download(
        stac_url=stac_url,
        collections=[cid],
        bbox=[13.0, 52.0, 13.5, 52.5],
        datetime="2024-01-01/2024-01-02",
        dest_dir="downloads",
    )
```

This functionality depends on the ``pystac-client`` and ``requests``
packages being available at runtime.  If either is missing an
``ImportError`` is raised.

---

## Command Line Interface

Use the CLI to parse filenames, list available schemas, and assemble filenames from fields.
The `assemble` subcommand relies on the `parseo.assembler` module, which ships with the
standard parseo installation. If you run `parseo assemble` in an environment where this
module was intentionally omitted, the CLI will exit with:

```
The 'assemble' command requires parseo.assembler, which is part of the standard parseo installation.
```

Reinstall parseo with assembler support or provide your own `parseo/assembler.py`
implementing `assemble(schema_path, fields)` to enable this command.

The `list-clms-products` subcommand queries the public Copernicus Land Monitoring Service (CLMS)
dataset catalog and prints the available product names. Use this to discover valid identifiers
when working with CLMS filename schemas.

```bash
# Parse a filename
parseo parse S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE

# List available schemas
parseo list-schemas
# -> CLC
#    LANDSAT
#    S1
#    S2
#    S3
#    S4
#    S5P
#    S6

# List CLMS products from the dataset catalog
parseo list-clms-products
# -> Corine Land Cover (CLC)
#    High Resolution Water & Snow / Ice (HR-WSI)
#    High Resolution Vegetation Phenology & Productivity (HR-VPP)
#    ...

# Inspect a specific schema
parseo schema-info S2
# -> {
#      "schema_id": "copernicus:sentinel:s2",
#      "description": "Sentinel-2 product filename (MSI sensor, processing levels L1C/L2A; extension optional).",
#      "template": "{platform}_{sensor}{processing_level}_{sensing_datetime}_..._[.{extension}]",
#      "examples": [
#        "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE",
#        "..."
#      ],
#      "fields": {
#        "platform": {"type": "string", "enum": ["S2A", "S2B", "S2C"], "description": "Spacecraft unit"},
#        "sensor": {"type": "string", "enum": ["MSI"], "description": "Sensor"},
#        ...
#      }
#    }

# Assemble a filename from fields.
# The CLI auto-selects a schema based on the first compulsory field.

# Example: Sentinel-2 SAFE (first field: platform)
parseo assemble \
  platform=S2B sensor=MSI processing_level=L2A sensing_datetime=20241123T224759 \
  processing_baseline=N0511 relative_orbit=R101 mgrs_tile=T03VUL \
  generation_datetime=20241123T230829 extension=SAFE
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE

# Example: CLMS HR-WSI product (first field: prefix)
parseo assemble \
  prefix=CLMS_WSI product=WIC pixel_spacing=020m tile_id=T33WXP \
  sensing_datetime=20201024T103021 platform=S2B processing_baseline=V100 file_id=WIC extension=tif
# -> CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC.tif

# Example: CLMS HR-VPP product (first field: prefix)
parseo assemble \
  prefix=CLMS_VPP product=FAPAR resolution=100m tile_id=T32TNS \
  start_date=20210101 end_date=20210110 version=V100 file_id=FAPAR extension=tif
# -> CLMS_VPP_FAPAR_100m_T32TNS_20210101_20210110_V100_FAPAR.tif
```

## Schema discovery and versioning

Each JSON schema is self contained. For `parseo` to discover it, the file must
include `"schema_id"` and `"schema_version"` at the top level. Multiple
versions of the same product can live side by side; add a `"status"` field to
each file to mark its lifecycle (`current`, `deprecated`, ...).

When several versions are present, `parseo` selects the one whose `status` is
`"current"`. If none are marked current, the highest `schema_version`
is used automatically.

### Default behaviour

```python
from parseo import parse_auto

res = parse_auto("S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE")
print(res.version)  # -> '1.0.0'
print(res.status)   # -> 'current'
```

### Requesting a specific version

Pass an explicit schema file to work with a particular version.

```python
from pathlib import Path
from parseo import assemble
from parseo.parser import _load_json_from_path, _extract_fields, _try_validate

schema_v100 = Path("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")

# assemble with that exact schema version
filename = assemble(schema_v100, fields)

# parse with that schema version
schema = _load_json_from_path(schema_v100)
if _try_validate(name, schema):
    fields = _extract_fields(name, schema)
```

---

## Creating a New Filename Schema

Adding support for a new product requires only a JSON schema placed under
`src/parseo/schemas/`. All field definitions live inside the schema file.
For a starting you can either use one of the used ones or you can use the 
one in `examples/schema_skeleton/`.

1. **Create the product directory**
   - Path: `src/parseo/schemas/<family>/<mission>/<product>/`. `family` 
   folder is required, the rest is up to you.  

2. **Write the versioned schema file**
   - Filename: `<product>_filename_vX_Y_Z.json`
   - Include top-level metadata such as **required** `schema_id` and
     `schema_version` (needed for discovery), `status` (`current`,
     `deprecated`, etc.), `stac_version`, optional `stac_extensions`, and a
     short `description`. ParsEO will use the version flagged as current
     as a default when assembling a filename.

3. **Define fields inline**
   - Add a top-level `"fields"` object. Each field uses JSON Schema
     keywords like `type`, `pattern` or `enum`, plus an optional
     `description`.
   - Mark required fields in a top-level `"required"` array. Any field not
     listed there is optional.

4. **Describe the filename structure**
   - Provide a `"template"` string that arranges fields using `{field}`
     placeholders. Optional parts can be wrapped in square brackets, e.g.,
     `[.{extension}]`.
   - At runtime the template is compiled into a regex by replacing each
     placeholder with the field's pattern or enum values.

5. **Provide examples**
   - Include an `"examples"` array showing valid filenames with and without
     optional components.

6. **Maintain versions**
   - Add a `"status"` field to every schema file. Mark the active schema as
     `"current"` and older ones as `"deprecated"` (or similar).
   - `parseo` selects the schema marked `"current"`; if none is marked,
     the highest `schema_version` is chosen automatically.

7. **Test the schema**
   - Use `parseo parse <filename>` to check parsing and `parseo assemble`
     with field dictionaries to ensure round-trip consistency.

---

## Contributing

- Add new schemas under `src/parseo/schemas/<product_family>/`
- Include at least one positive example in the schema file
- Run tests with `pytest`
- submit a pull request
---

## License

This project is licensed under the [European Union Public Licence v1.2](LICENSE.txt).
