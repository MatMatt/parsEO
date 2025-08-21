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
    "mission": "S2B",
    "instrument_processing": "MSIL2A",
    "sensing_datetime": "20241123T224759",
    "processing_baseline": "N0511",
    "relative_orbit": "R101",
    "tile_id": "T03VUL",
    "generation_datetime": "20241123T230829",
    "extension": ".SAFE"
}

filename = assemble("sentinel/s2/s2_filename_v1_0_0.json", fields)
print(filename)
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE
```

---

## Command Line Interface

```bash
# Parse a filename
parseo parse S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE

# List available schemas
parseo list-schemas

## Command Line Interface

```bash
# Parse a filename
parseo parse S1A_IW_SLC__1SDV_20250105T053021_20250105T053048_A054321_D068F2E_ABC123.SAFE

# List available schemas
parseo list-schemas

# Assemble a filename from fields
# The CLI auto-selects a schema based on the FIRST compulsory field declared by that schema.

# Example for a Sentinel-2 SAFE schema where the first field is 'mission'
parseo assemble \
  mission=S2B instrument_processing=MSIL2A sensing_datetime=20241123T224759 \
  processing_baseline=N0511 relative_orbit=R101 tile_id=T03VUL \
  generation_datetime=20241123T230829 extension=.SAFE
# -> S2B_MSIL2A_20241123T224759_N0511_R101_T03VUL_20241123T230829.SAFE

# Example for a CLMS HR-WSI product where the first field is 'prefix'
# (first compulsory field name depends on the schema's fields_order[0])
parseo assemble \
  prefix=CLMS_WSI product=WIC spatial_res=020m tile_id=T33WXP \
  datetime=20201024T112121 platform=S2B version=V100 layer_code=WIC extension=.tif
# -> CLMS_WSI_WIC_020m_T33WXP_20201024T112121_S2B_V100_WIC.tif
```

---

## Contributing

- Add new schemas under `src/parseo/schemas/<product_family>/`  
- Include at least one positive example in the schema file  
- Run tests with `pytest`

---

## License

EUPL-1.2 (see LICENSE file)
