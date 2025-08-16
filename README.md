# parsEO

[![CI](https://github.com/MatMatt/parseo/actions/workflows/python-package.yml/badge.svg)](https://github.com/MatMatt/parseo/actions/workflows/python-package.yml) ![License: EUPL 1.2](https://img.shields.io/badge/License-EUPL%201.2-green.svg) ![Python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)

A lightweight, schema-driven filename parser currently supporting:

-   **Copernicus Sentinel** and

-   **USGS Landsat** products.

The parser uses JSON schema definitions to match and extract fields from product filenames, ensuring consistent and maintainable parsing logic.\
Schemas are bundled with the package and include field descriptions, code lists, and regular expressions.

------------------------------------------------------------------------

## ✨ Features

-   **Schema-based parsing** for Sentinel-1 to Sentinel-6, Sentinel-5P, Landsat 4–9
-   **Named capture groups** for clean, descriptive field extraction
-   **Unified Sentinel-1 schema** covering L0/L1/L2 product families
-   **Both Python API and CLI support**
-   **Bundled JSON schemas** (offline-friendly)
-   **Extensible** — add your own schemas for new missions

------------------------------------------------------------------------

## 📦 Installation

### From source (editable for development)

``` bash
git clone https://github.com/MatMatt/parseo.git
cd parseo
python -m pip install -e .
```

## 🤨 Usage

``` python
from parseo.parser import parse_auto

# Sentinel-2 example
name = "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
result = parse_auto(name)

if result:
    print("Matched schema:", result.schema_name)
    print("Fields:", result.fields)
else:
    print("No schema matched ❌")
```

``` text
Matched schema: sentinel/sentinel2_filename_structure.json
Fields: {
  'mission': 'S2B',
  'instrument_processing': 'MSIL2A',
  'sensing_datetime': '20241123T224759',
  'processing_baseline': 'N0511',
  'relative_orbit': 'R101',
  'tile_id': 'T03VUL',
  'generation_datetime': '20241123T230829',
  'extension': '.SAFE'
}
```

``` bash
# Module form (works everywhere)
python -m parseo.cli S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE

# Console script (if your Scripts/ is on PATH)
filenaming-parse S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

# 💪 Currently supported

| Family | Missions | Typical products (examples) | Schema file (bundled) | Notes |
|---------------|---------------|---------------|---------------|---------------|
| Sentinel-1 | S1A, S1B | `SLC__`, `GRD[F/M/H]_`, `OCN__` | `sentinel1_filename_structure.json` | S1 schema; supports polarisation tokens like `1SDV`, `2SDV` |
| Sentinel-2 | S2A, S2B | `MSIL1C`, `MSIL2A` | `sentinel2_filename_structure.json` | MGRS tile IDs (`TxxYYY`) parsed |
| Sentinel-3 | S3A, S3B | OLCI/SLSTR/SRAL product names | `sentinel3_filename_structure.json` | Key metadata fields captured |
| Sentinel-4 | S4 (MTG-S) | Atmospheric composition products | `sentinel4_filename_structure.json` | Pre-operational formats supported |
| Sentinel-5 | S5 (MetOp-SG A/B) | Atmospheric composition products | `sentinel5_filename_structure.json` | Distinct from S5P |
| Sentinel-5P | S5P (TROPOMI) | L1B/L2 TROPOMI products | `sentinel5p_filename_structure.json` | TROPOMI-specific patterns |
| Sentinel-6 | S6A, S6B | Poseidon altimetry products | `sentinel6_filename_structure.json` | Core filename fields parsed |
| Landsat | 4 | L1/L2 scene IDs | `landsat4_filename_structure.json` |  |
| Landsat | 5 | L1/L2 scene IDs | `landsat5_filename_structure.json` |  |
| Landsat | 7 | L1/L2 scene IDs | `landsat7_filename_structure.json` |  |
| Landsat | 8 | `L1TP`, `L1GT`, `L1GS`, `L2SP`, `L2SR` | `landsat8_filename_structure.json` | Processing-level switches included |
| Landsat | 9 | `L1TP`, `L1GT`, `L1GS`, `L2SP`, `L2SR` | `landsat9_filename_structure.json` | Processing-level switches included |

The parser tries all bundled schemas in order and returns the first match with named capture groups.

## 🏗️ Project structure

``` bash
parseo/
├── src/parseo/
│   ├── __init__.py
│   ├── parser.py           # Core parser logic
│   ├── cli.py              # CLI entry point
│   └── schemas/
│       ├── sentinel/
│       │   ├── sentinel1_filename_structure.json
│       │   ├── sentinel2_filename_structure.json
│       │   └── ...
│       └── landsat/
│           ├── landsat4_filename_structure.json
│           ├── landsat5_filename_structure.json
│           └── ...
├── tests/
│   ├── data/
│   └── test_parser.py
├── pyproject.toml (or setup.cfg)
└── README.md
```

## 📄 Add a new schema

Follow these steps to add support for another mission or product family.

### Create the schema file  
   Place a JSON file in `src/parseo/schemas/<family>/`.  
   Example: src/parseo/schemas/sentinel/sentinel2_filename_structure.json

### Define the pattern and fields 
Use **named capture groups** in `filename_pattern` (e.g., `(?P<tile_id>T\d{2}[A-Z]{3})`) and document each field.  
Example (Sentinel-2):

```json
{
  "mission": {
    "codes": [
      "S2A",
      "S2B",
      "S2C"
    ],
    "description": "Satellite & mission number (Sentinel-2A, Sentinel-2B, or Sentinel-2C)"
  },
  "instrument_processing": {
    "codes": [
      "MSIL1C",
      "MSIL2A"
    ],
    "description": "Instrument + Processing Level",
    "details": {
      "MSIL1C": "MultiSpectral Instrument, Level-1C (Top-Of-Atmosphere reflectance)",
      "MSIL2A": "MultiSpectral Instrument, Level-2A (Bottom-Of-Atmosphere reflectance, atmospherically corrected)"
    }
  },
  "sensing_datetime": {
    "format": "YYYYMMDDThhmmss",
    "description": "UTC date and time when acquisition started"
  },
  "processing_baseline": {
    "format": "Nxxxx",
    "description": "Processing baseline version (e.g., N0511)"
  },
  "relative_orbit": {
    "format": "Rxxx",
    "range": "R001\u2013R143",
    "description": "Relative orbit number (repeats every 10 days for Sentinel-2)"
  },
  "tile_id": {
    "format": "T<zone><lat_band><grid_square>",
    "description": "MGRS tile ID (e.g., T32TMT) covering 100\u00d7100 km area",
    "notes": "Zone = 2 digits, Latitude band = 1 letter, Grid square = 2 letters"
  },
  "generation_datetime": {
    "format": "YYYYMMDDThhmmss",
    "description": "UTC date and time when the product was generated"
  },
  "extension": {
    "codes": [
      ".SAFE"
    ],
    "description": "Sentinel SAFE format container"
  },
  "valid_examples": [
    "S2A_MSIL1C_20250105T103021_N0511_R080_T32TMT_20250105T120021.SAFE",
    "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
  ],
  "filename_pattern": "^(?P<mission>S2A|S2B)_(?P<instrument_processing>MSIL1C|MSIL2A)_(?P<sensing_datetime>(?:19|20)\\d\\d(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])T(?:[01]\\d|2[0-3])(?:[0-5]\\d){2})_(?P<processing_baseline>N\\d{4})_(?P<relative_orbit>R\\d{3})_(?P<tile_id>T\\d{2}[C-HJ-NP-X][A-Z]{2})_(?P<generation_datetime>(?:19|20)\\d\\d(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])T(?:[01]\\d|2[0-3])(?:[0-5]\\d){2})(?P<extension>\\.SAFE)$",
  "fields_order": [
    "mission",
    "instrument_processing",
    "sensing_datetime",
    "processing_baseline",
    "relative_orbit",
    "tile_id",
    "generation_datetime",
    "extension"
  ]
}
```
### Install in editable mode (for development)
``` bash
python -m pip install -e .
```
### Test your schema
``` bash
# Module form
python -m parseo.cli S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```
``` bash
# Or console script if on PATH
parseo S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

## 📜 License

This project is licensed under the **European Union Public Licence (EUPL)**, Version 1.2 or later.  
You can read the full text in the [LICENSE.txt](LICENSE.txt) file or in the [European Commission website](https://joinup.ec.europa.eu/collection/eupl/eupl-text-11-12).
