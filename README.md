# parsEO

**parsEO** is a Python package for **parsing and assembling filenames** of satellite data and derived products. It also serves as an **authoritative definition of filename structures** through machine-readable JSON schemas.

## Features

-   **Bidirectional support**:\
    Parse existing product filenames into structured fields, and assemble new filenames from fields.

-   **Schema-driven**: Filename rules are defined in JSON schema files under `src/parseo/schemas/`. Dropping a new schema file into this tree is enough — parsEO discovers it automatically.

-   **Extensible**: New product families can be added by dropping schema definitions into the repo (see below).

## Currently Supported Products

-   **Sentinel missions**: S1, S2, S3, S4, S5P, S6
-   **Landsat**: LT04, LT05, LE07, LC08, LC09
-   **NASA MODIS**: Terra/Aqua MODIS products
-   **EUMETSAT missions**: MTG, Metop
-   **Copernicus Land Monitoring Service (CLMS)**:
    -   Corine Land Cover (CLC) and CLC+ Raster
    -   European Ground Motion Service (EGMS) Level 3 velocity grid
    -   Urban Atlas Land Cover / Land Use
    -   High Resolution Vegetation Phenology & Productivity (HR-VPP): Seasonal Trajectories (PPI) and Vegetation Indices (FAPAR, LAI, NDVI, PPI, FCOVER, DMP)
    -   High Resolution Water & Snow / Ice (HR-WSI): CC, FSC, GFSC, ICD, SWS, WDS, WIC, WIC-COMB, SP_S2, SP_COMB
    -   High Resolution Layers (HRL): Forest Type, Grassland, Imperviousness, Non-Vegetated Land Cover Characteristics, Tree Cover Density, Water & Wetness, Small Woody Features

## Installation

``` bash
pip install parseo
```

For development:

``` bash
git clone https://github.com/MatMatt/parsEO.git
cd parsEO
pip install -e .
```

``` bash
parseo --version
```

## Usage

### Parse a filename

``` python
from parseo import parse_auto

name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
res = parse_auto(name)

print(res.valid)   # True
print(res.fields)  # structured dict of extracted fields
```

Example for a MODIS product:

``` python
name = "MOD09GA.A2021123.h18v04.006.2021132234506.hdf"
res = parse_auto(name)
print(res.fields["platform"])  # MOD
print(res.fields["product"])   # 09
print(res.fields["variant"])   # GA
```

This schema advertises the Processing, Sat, Raster, and Electro-Optical STAC
extensions so MODIS filenames can be associated with the corresponding STAC
metadata (`processing`, `sat`, `raster`, `eo`).

### Assembling a filename

``` python
from pathlib import Path
from parseo import assemble, assemble_auto

fields = {
    "platform": "S2B",
    "instrument": "MSI",
    "processing_level": "L2A",
    "sensing_datetime": "20241123T224759",
    "processing_baseline": "N0511",
    "relative_orbit": "R101",
    "mgrs_tile": "T03VUL",  # MGRS tile (TxxYYY, e.g., T32TNS)
    "generation_datetime": "20241123T230829",
    "extension": "SAFE",
}
```

#### Asseble Auto (autodetection of schema)

``` python
filename = assemble_auto(fields)
print(filename)
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

#### Assemble using default (current) family schema. This should speed up the conversion, if family is known and stable.

``` python
filename = assemble(fields, family="S2")
print(filename)
```

#### Assemble specifying product family and and filneme version. This should speed up the conversion, if family is known and stable.

``` python
filename = assemble(fields, family="S2", version="1.0.0")
print(filename)
```

#### Assembing with an explicit schema file

``` python
schema_path = Path("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")
filename = assemble(fields, schema_path=schema_path)
print(filename)
```

#### Perfomeance tests:

| Function | Conversion time (seconds per file) |
|----|----|
| assemble_auto(fields) | 0.0074 |
| assemble(fields, family='S2') | 0.000017 |
| assemble(fields, family='S2', version='1.0.0') | 0.0000178 |

### Validate schema examples

When adding a new schema, use `validate_schema` to ensure that the filenames listed under its `examples` section still parse and reassemble correctly. Pass `verbose=True` to get feedback as each example is checked.

``` python
from parseo import validate_schema

validate_schema("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")

# Enable verbose output to see progress
validate_schema(
    "src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json",
    verbose=True
)
```

The paresos internal tests call this `validate_schema` so that schema examples stay in sync with the parser over time.

### Map combined tokens to STAC fields (`stac_map`)

Some schemas contain filename tokens that encode multiple STAC metadata fields (for example, a platform identifier that also implies the satellite name and instrument). You can declare a `stac_map` block inside the token definition to expand those combined values into richer STAC metadata when parsing, and to translate STAC fields back into tokens when assembling filenames.

Below is an excerpt from the Landsat schema (`src/parseo/schemas/usgs/landsat/landsat_filename_v1_0_0.json`) that maps the combined `platform` token to STAC fields:

``` json
{
  "fields": {
    "platform": {
      "description": "Landsat platform identifier",
      "stac_map": {
        "preserve_original_as": "platform_code",
        "LC08": {
          "platform": "landsat-8",
          "instrument": "OLI_TIRS"
        },
        "LE07": {
          "platform": "landsat-7",
          "instrument": "ETM+"
        }
      }
    }
  }
}
```

When you parse a Landsat filename, `parse_auto` uses this mapping to enrich the result:

``` python
from parseo import parse_auto

result = parse_auto("LC08_L1TP_190026_20200101_20200114_02_T1.tar")

result.fields["platform_code"]  # "LC08" (preserved token value)
result.fields["platform"]        # "landsat-8" (STAC platform name)
result.fields["instrument"]      # "OLI_TIRS"
```

The same mapping is applied in reverse when assembling filenames. If you provide the STAC values along with `platform_code`, `assemble_auto` (or `assemble`) picks the correct token for the output filename. This keeps your schemas declarative while ensuring that parse results remain STAC-friendly.

### Run as API

parsEO functions can be exposed through a web service. The example below uses [FastAPI](https://fastapi.tiangolo.com), which provides an automatic Swagger UI for trying out the endpoints.

``` python
# Safe to file: main.py
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

from the console inside the same directiory start the app:

``` bash
uvicorn main:app --reload
```

Open <http://127.0.0.1:8000/docs> to access Swagger UI:

The interactive page lets you call `/parse` and `/assemble` directly from the browser to verify the API.

### List STAC collections (not functional yet!)

Use the `list-stac-collections` subcommand to list collection IDs exposed by a STAC API. The STAC root URL must be supplied via `--stac-url`:

``` bash
parseo list-stac-collections --stac-url https://catalogue.dataspace.copernicus.eu/stac
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

The `stac-sample` subcommand prints a few asset filenames from a STAC collection. The STAC API root must always be provided via `--stac-url` (with or without a trailing slash):

``` bash
# not working yet!
parseo stac-sample SENTINEL-2 --samples 3 --stac-url https://catalogue.dataspace.copernicus.eu/stac
```

### Search STAC and download assets (does not work yet)

The `parseo.stac_scraper` module provides helpers for programmatic interaction with a STAC API. The snippet below lists available collections and downloads the first asset matching a simple search:

``` python
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

This functionality depends on the `pystac-client` and `requests` packages being available at runtime. If either is missing an `ImportError` is raised.

## Command Line Interface

Use the CLI to parse filenames, list available schemas, and assemble filenames from fields.

``` bash
# Parse a filename
parseo parse S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE

# List available schemas
parseo list-schemas
FAMILY               VERSION STATUS  FILE
CC                   0.0.0   current ...\src\parseo\schemas\copernicus\clms\hr-wsi\cc\cc_filename_v0_0_0.json
CLC                  1.1.0   current ...\src\parseo\schemas\copernicus\clms\clc\clc_filename_v1_1_0.json
CLC                  1.0.0   deprecated ...\src\parseo\schemas\copernicus\clms\clc\clc_filename_v1_0_0.json
FOREST-TYPE          0.0.0   current ...\src\parseo\schemas\copernicus\clms\hrl\forest-type\forest-type_filename_v0_0_0.json
FSC                  0.0.0   current ...\src\parseo\schemas\copernicus\clms\hr-wsi\fsc\fsc_filename_v0_0_0.json
GFSC                 0.0.0   current ...\src\parseo\schemas\copernicus\clms\hr-wsi\gfsc\gfsc_filename_v0_0_0.json

# Inspect a specific schema
parseo schema-info S2
# -> {
#      "schema_id": "copernicus:sentinel:s2",
#      "description": "Sentinel-2 product filename (MSI instrument, processing levels L1C/L2A; extension optional).",
#      "template": "{platform}_{instrument}{processing_level}_{sensing_datetime}_..._[.{extension}]",
#      "examples": [
#        "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE",
#        "..."
#      ],
#      "fields": {
#        "platform": {"type": "string", "enum": ["S2A", "S2B", "S2C"], "description": "Spacecraft unit"},
#        "instrument": {"type": "string", "enum": ["MSI"], "description": "Instrument"},
#        ...
#      }
#    }
```

Use the CLI to assemble filenames.

``` bash
# The CLI auto-selects a schema based on the first compulsory field.

# Example: Sentinel-2 SAFE (first field: platform)
parseo assemble platform=S2B instrument=MSI processing_level=L2A sensing_datetime=20241123T224759 processing_baseline=N0511 relative_orbit=R101 mgrs_tile=T03VUL generation_datetime=20241123T230829 extension=SAFE
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE

# Example: CLMS HR-WSI product (first field: programme)
parseo assemble programme=CLMS project=WSI product=WIC pixel_spacing=020m mgrs_tile=T33WXP sensing_datetime=20201024T103021 platform=S2B version=V100 variable=WIC extension=tif
# -> CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC.tif

# Example: CLMS HR-VPP product (first field: prefix)
parseo assemble prefix=CLMS_VPP product=FAPAR resolution=100m mgrs_tile=T32TNS start_date=20210101 end_date=20210110 version=V100 file_id=FAPAR extension=tif
# -> CLMS_VPP_FAPAR_100m_T32TNS_20210101_20210110_V100_FAPAR.tif
```

## Schema discovery and versioning

Each JSON schema is self contained. For `parseo` to discover it, the file must include `"schema_id"` and `"schema_version"` at the top level. Multiple versions of the same product can live side by side; add a `"status"` field to each file to mark its lifecycle (`current`, `deprecated`, ...).

When several versions are present, `parseo` selects the one whose `status` is `"current"`. If none are marked current, the highest `schema_version` is used automatically.

### Default behaviour

``` python
from parseo import parse_auto

res = parse_auto("S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE")
print(res.version)  # -> '1.0.0'
print(res.status)   # -> 'current'
```

### Requesting a specific version

Pass an explicit schema file to work with a particular version.

``` python
from pathlib import Path
from parseo import assemble
from parseo.parser import _load_json_from_path, _extract_fields, _try_validate

schema_v100 = Path("src/parseo/schemas/copernicus/sentinel/s2/s2_filename_v1_0_0.json")

# assemble with that exact schema version
filename = assemble(fields, schema_path=schema_v100)
print(filename)

# parse with that schema version
schema = _load_json_from_path(schema_v100)
if _try_validate(name, schema):
    fields = _extract_fields(name, schema)
print(fields)
```

## Creating a New Filename Schema

Adding support for a new product requires only a JSON schema placed under `src/parseo/schemas/`. All field definitions live inside the schema file. Start from an existing product schema or copy the skeleton in `template/`.

1.  **Create the product directory**
    -   Path: `src/parseo/schemas/<family>/<mission>/<product>/`. `family` folder is required, the rest is up to you.
2.  **Write the versioned schema file**
    -   Filename: `<product>_filename_vX_Y_Z.json`
    -   Include top-level metadata such as **required** `schema_id` and `schema_version` (needed for discovery), `status` (`current`, `deprecated`, etc.), `stac_version`, optional `stac_extensions`, and a short `description`. ParsEO will use the version flagged as current as a default when assembling a filename.
    -   When populating `stac_extensions`, always list the canonical schema URIs published at [stac-extensions.github.io](https://stac-extensions.github.io) (for example, `https://stac-extensions.github.io/eo/v1.0.0/schema.json`).
3.  **Define fields inline**
    -   Add a top-level `"fields"` object. Each field uses JSON Schema keywords like `type`, `pattern` or `enum`, plus an optional `description`.
    -   Mark required fields in a top-level `"required"` array. Any field not listed there is optional.

    **Picking `enum` vs. `pattern`**

    -   Use an `enum` when the field value must be selected from a finite vocabulary (e.g., `extension`, `collection`, or `processing_mode`). Enums keep the schema readable and help surface invalid tokens early.
    -   Use a `pattern` when the field must match a structured value such as timestamps (`^\d{8}T\d{6}$`), version identifiers (`^V\d{3}$`), or grid/tile IDs (`^h\d{2}v\d{2}$`). Patterns work best when the allowed set is large but follows a consistent structure.

    **Linking fields to STAC metadata**

    -   Populate a field-level `stac_map` when the filename token should be expanded into richer STAC properties. Map enum entries to dictionaries and use `pattern` capture groups (`$1`, `$2`, …) to fill values derived from the match.
    -   Keep the STAC mappings near the relevant field definitions so downstream tooling can translate filenames into STAC items without extra lookups.
    -   Example:

        ``` jsonc
        "prefix": {
          "type": "string",
          "pattern": "^(MOD|MYD|MCD)$",
          "stac_map": {
            "MOD": {
              "platform": "Terra",
              "instrument": "MODIS"
            },
            "MYD": {
              "platform": "Aqua",
              "instrument": "MODIS"
            },
            "MCD": {
              "platform": "Combined",
              "instrument": "MODIS"
            }
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
4.  **Describe the filename structure**
    -   Provide a `"template"` string that arranges fields using `{field}` placeholders. Optional parts can be wrapped in square brackets, e.g., `[.{extension}]`.
    -   At runtime the template is compiled into a regex by replacing each placeholder with the field's pattern or enum values.
5.  **Provide examples**
    -   Include an `"examples"` array showing valid filenames with and without optional components.
6.  **Maintain versions**
    -   Add a `"status"` field to every schema file. Mark the active schema as `"current"` and older ones as `"deprecated"` (or similar).
    -   `parseo` selects the schema marked `"current"`; if none is marked, the highest `schema_version` is chosen automatically.
7.  **Test the schema**
    -   Use `parseo parse <filename>` to check parsing and `parseo assemble` with field dictionaries to ensure round-trip consistency.

## Contributing

-   Add new schemas under `src/parseo/schemas/<product_family>/`
-   Include at least one positive example in the schema file
-   Run tests with `pytest`
-   submit a pull request

## License

This project is licensed under the [European Union Public Licence v1.2](LICENSE.txt).