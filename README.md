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

  - **STAC utilities**:
    Query STAC APIs to list collections or sample asset filenames, search and download assets,
    and scrape metadata from static STAC catalogs using lightweight helpers.

---

## Supported Products

Currently included schemas cover:

- **Sentinel missions**: S1, S2, S3, S4, S5P, S6  
- **Landsat**: LT04, LT05, LE07, LC08, LC09  
- **NASA MODIS**: Terra/Aqua MODIS products
- **EUMETSAT missions**: MTG, Metop
- **Copernicus Land Monitoring Service (CLMS)**:
  - Corine Land Cover (CLC)
  - High Resolution Water & Snow / Ice (HR-WSI)
  - High Resolution Vegetation Phenology & Productivity (HR-VPP)
  - High Resolution Layers: Grasslands
  - High Resolution Layers: Non-Vegetated Land Cover Change (HRL NVLCC)
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

Assemble with known schema (eventually faster):

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
---

## Run as a web API

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

Start the server:
```bash
uvicorn main:app --reload
```
and open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to access Swagger UI.

The interactive page lets you call `/parse` and `/assemble` directly from the
browser to verify your API.

---

## STAC helpers and catalog scraping

Filenames often reflect associated metadata or directory structures, so `parsEO` aligns with STAC naming conventions whenever possible. The package ships with lightweight utilities to interact with STAC APIs and catalogs, including helpers to list collections, sample asset filenames, search for downloadable assets, and traverse static catalogs stored on disk.

`list-stac-collections` and `stac-sample` rely on [`pystac-client`](https://github.com/stac-utils/pystac-client) for STAC API access. Install it alongside `parsEO` to use these commands.

The legacy `stac_dataspace` helper has been removed. Its functionality is covered by the new `scrape_catalog` function described below, which walks STAC catalogs or collections served over HTTP or stored locally. It does not traverse STAC API endpoints.

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

The command is backed by ``parseo.stac_scraper.sample_collection_filenames``,
which queries the STAC API for a handful of items and extracts representative
asset filenames.

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
for cid in stac_scraper.list_collections(stac_url):
    print(cid)
    stac_scraper.search_stac_and_download(
        stac_url=stac_url,
        collections=[cid],
        bbox=[13.0, 52.0, 13.5, 52.5],
        datetime="2024-01-01T00:00:00Z/2024-01-02T00:00:00Z",
        dest_dir="downloads",
    )
```

This functionality depends on the ``pystac-client`` and ``requests``
packages being available at runtime.

All temporal constraints should be expressed as timezone-aware ISO 8601
strings (e.g., ``2024-01-01T00:00:00Z``).

### Scrape a STAC catalog

``parseo.scrape_catalog`` is a lightweight helper that walks a static STAC
catalog or collection and extracts basic metadata for each data asset using only
the Python standard library. STAC API roots should be accessed via the
``list-stac-collections`` or ``stac-sample`` helpers instead.

```python
from parseo import scrape_catalog

# Walk a small STAC example catalog hosted online
catalog = "https://raw.githubusercontent.com/radiantearth/stac-spec/v1.0.0/examples/catalog.json"
for entry in scrape_catalog(catalog, limit=2):
    print(entry)
```

Which yields entries like:

```
{'filename': 'LC08_L1TP_038028_20180201_20180215_01_T1_B1.TIF'}
{'filename': 'LC08_L1TP_038028_20180201_20180215_01_T1_B2.TIF'}
```

When adjacent JSON or XML sidecar files are present, ``scrape_catalog`` also
adds any of the fields ``id``, ``product_type``, ``datetime``, ``tile`` and
``orbit`` found in those files to each entry.

From the command line, the same helpers are available through parseo's
``list-stac-collections`` and ``stac-sample`` subcommands, both powered by
``parseo.stac_scraper``.

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

# Example: CLMS HRL NVLCC product (first field: prefix)
parseo assemble \
  prefix=CLMS_HRL product=NVLCC resolution=010m tile_id=T32TNS \
  start_date=20210101 end_date=20211231 version=V100 file_id=NVLCC extension=tif
# -> CLMS_HRL_NVLCC_010m_T32TNS_20210101_20211231_V100_NVLCC.tif
```

---

## Creating a New Filename Schema

Adding support for a new product requires only a JSON schema placed under
`src/parseo/schemas/`. All field definitions live inside the schema file.

1. **Create the product directory**
   - Path: `src/parseo/schemas/<family>/<mission>/<product>/`
   - Add an `index.json` pointing to the active schema file. The `version`
     key in `index.json` is optional; `status` and `file` are required.

2. **Write the versioned schema file**
   - Filename: `<product>_filename_vX_Y_Z.json`
   - Include top-level metadata such as `schema_id`, `schema_version`,
     `stac_version`, optional `stac_extensions`, and a short `description`.

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
   - Placeholder order in the template defines `fields_order` for
     filename assembly.

5. **Provide examples**
   - Include an `"examples"` array showing valid filenames with and without
     optional components.

6. **Maintain versions**
   - When the schema evolves, create a new file with an incremented version
     and update `index.json` to mark it as `current`.

7. **Test the schema**
   - Use `parseo parse <filename>` to check parsing and `parseo assemble`
     with field dictionaries to ensure round-trip consistency.

---

## Contributing

- Add new schemas under `src/parseo/schemas/<product_family>/`
- Include at least one positive example in the schema file
- Run tests with `pytest`

---

## License

This project is licensed under the [European Union Public Licence v1.2](LICENSE.txt).
