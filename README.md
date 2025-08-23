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

## Supported Products

Currently included schemas cover:

- **Sentinel missions**: S1, S2, S3, S4, S5P, S6
- **Landsat**: LT04, LT05, LE07, LC08, LC09
- **Copernicus Land Monitoring Service (CLMS)**:
  - Corine Land Cover (CLC)
  - High Resolution Water & Snow / Ice (HR-WSI)
  - High Resolution Layers: Grasslands
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

### Assemble a filename

```python
from parseo import assemble

fields = {
    "platform": "S2B",
    "processing_level": "MSIL2A",
    "datetime": "20241123T224759",
    "version": "N0511",
    "sat_relative_orbit": "R101",
    "mgrs_tile": "T03VUL",
    "generation_datetime": "20241123T230829",
    "extension": ".SAFE"
}

filename = assemble("sentinel/s2/s2_filename_v1_0_0.json", fields)
print(filename)
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

### Run as a web API

You can expose parsEO over HTTP using [FastAPI](https://fastapi.tiangolo.com).
The steps below show a minimal, working example from scratch.

1. **Install the required packages**:

   ```bash
   pip install parseo fastapi uvicorn
   ```

2. **Save the following as `main.py`**:

   ```python
   from dataclasses import asdict

   from fastapi import FastAPI
   from pydantic import BaseModel

   from parseo import assemble, parse_auto


   app = FastAPI()


   @app.get("/parse")
   def parse_endpoint(name: str):
       res = parse_auto(name)
       # ParseResult is a dataclass; convert to dict for JSON response
       return asdict(res)


   class AssemblePayload(BaseModel):
       schema: str
       fields: dict


   @app.post("/assemble")
   def assemble_endpoint(payload: AssemblePayload):
       filename = assemble(payload.schema, payload.fields)
       return {"filename": filename}
   ```

3. **Start the server**:

   ```bash
   uvicorn main:app --reload
   ```

4. **Open the Swagger UI** at <http://127.0.0.1:8000/docs> and try the endpoints:

   - `GET /parse` → click **Try it out**, enter a filename such as
     `S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE`, and
     press **Execute** to see the parsed fields.
   - `POST /assemble` → click **Try it out** and paste the JSON body below, then
     press **Execute** to receive the assembled filename.

     ```json
     {
       "schema": "sentinel/s2/s2_filename_v1_0_0.json",
       "fields": {
         "platform": "S2B",
         "processing_level": "MSIL2A",
         "datetime": "20241123T224759",
         "version": "N0511",
         "sat_relative_orbit": "R101",
         "mgrs_tile": "T03VUL",
         "generation_datetime": "20241123T230829",
         "extension": ".SAFE"
       }
     }
     ```

   The response will look like:

   ```json
   {
     "filename": "S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE"
   }
   ```

   These endpoints can also be called from the command line:

   ```bash
   curl 'http://127.0.0.1:8000/parse?name=S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE'
   curl -X POST 'http://127.0.0.1:8000/assemble'\
     -H 'Content-Type: application/json'\
     -d '{
       "schema": "sentinel/s2/s2_filename_v1_0_0.json",
       "fields": {
         "platform": "S2B",
         "processing_level": "MSIL2A",
         "datetime": "20241123T224759",
         "version": "N0511",
         "sat_relative_orbit": "R101",
         "mgrs_tile": "T03VUL",
         "generation_datetime": "20241123T230829",
         "extension": ".SAFE"
       }
     }'
   ```

The interactive Swagger page or the `curl` commands both let you verify that the
API works as expected.

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

# Assemble a filename from fields.
# The CLI auto-selects a schema based on the first compulsory field.

# Example: Sentinel-2 SAFE (first field: platform)
parseo assemble\
  platform=S2B processing_level=MSIL2A datetime=20241123T224759\
  version=N0511 sat_relative_orbit=R101 mgrs_tile=T03VUL\
  generation_datetime=20241123T230829 extension=.SAFE
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE

# Example: CLMS HR-WSI product (first field: prefix)
parseo assemble\
  prefix=CLMS_WSI product=WIC pixel_spacing=020m tile_id=T33WXP\
  sensing_datetime=20201024T103021 platform=S2B version=V100 file_id=WIC extension=.tif
# -> CLMS_WSI_WIC_020m_T33WXP_20201024T103021_S2B_V100_WIC.tif
```

---

## Contributing

- Add new schemas under `src/parseo/schemas/<product_family>/`
- Include at least one positive example in the schema file
- Run tests with `pytest`

---

## License

This project is licensed under the [European Union Public Licence v1.2](LICENSE.txt).
