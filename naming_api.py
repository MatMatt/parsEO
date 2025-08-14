from datetime import datetime
from pathlib import Path
import json
from typing import Optional, Any
from fastapi import FastAPI, HTTPException

# Directory containing satellite lookup JSON files
LOOKUPS_DIR = Path(__file__).resolve().parent / "library"


def _load_lookup(name: str) -> dict[str, Any]:
    """Load a lookup JSON file from the library directory."""
    with open(LOOKUPS_DIR / f"{name}.json", "r", encoding="utf-8") as f:
        return json.load(f)


# Load individual lookups
_s1 = _load_lookup("s1")
S1_MODES = _s1["modes"]
S1_PRODUCTS = _s1["products"]
S1_RESOLUTIONS = _s1["resolutions"]

_s2 = _load_lookup("s2")
S2_INSTRUMENTS = _s2["instruments"]
S2_LEVELS = _s2["levels"]

_s3 = _load_lookup("s3")
S3_INSTRUMENTS = _s3["instruments"]
S3_LEVELS = _s3["levels"]
S3_PRODUCTS = _s3["products"]

_s5p = _load_lookup("s5p")
S5P_PRODUCTS = _s5p["products"]

app = FastAPI()


def generate_sentinel_filename(
    satellite: str,
    mode: Optional[str] = None,
    product_type: str = '',
    resolution: Optional[str] = None,
    level: Optional[str] = None,
    sensing_start: str = '',
    sensing_end: Optional[str] = None,
    orbit_number: int = 0,
    tile_id: Optional[str] = None,
    data_take_id: Optional[str] = None,
    cycle_number: Optional[int] = None,
    processing_center: Optional[str] = None,
    processing_baseline: str = '',
    product_discriminator: str = '',
    instrument: Optional[str] = None,
) -> str:
    """Generate Sentinel-like filenames."""
    satellite = satellite.upper()
    product_type = product_type.upper()
    level = level.upper() if level else None
    mode = mode.upper() if mode else None
    resolution = resolution.upper() if resolution else None
    instrument = instrument.upper() if instrument else None
    orbit_number_str = f"R{int(orbit_number):03d}"
    cycle_number_str = f"C{int(cycle_number):03d}" if cycle_number is not None else None
    processing_baseline = processing_baseline.upper()
    processing_center = processing_center.upper() if processing_center else None
    tile_id = tile_id.upper() if tile_id else None
    data_take_id = data_take_id.upper() if data_take_id else None

    sensing_start_fmt = datetime.strptime(
        sensing_start, "%Y-%m-%d %H:%M:%S"
    ).strftime("%Y%m%dT%H%M%S")
    if sensing_end:
        sensing_end_fmt = datetime.strptime(
            sensing_end, "%Y-%m-%d %H:%M:%S"
        ).strftime("%Y%m%dT%H%M%S")
    else:
        sensing_end_fmt = None

    if satellite in ("S1A", "S1B"):
        return (
            f"{satellite}_{mode}_{product_type}_{resolution}_"
            f"{sensing_start_fmt}_{orbit_number_str}_{data_take_id}_{product_discriminator}"
        )
    if satellite in ("S2A", "S2B"):
        combined = f"{product_type}{level}" if level else product_type
        return (
            f"{satellite}_{combined}_{sensing_start_fmt}_"
            f"{processing_baseline}_{orbit_number_str}_{tile_id}_{product_discriminator}.SAFE"
        )
    if satellite in ("S3A", "S3B"):
        return (
            f"{satellite}_{instrument}_{level}_{product_type}_{sensing_start_fmt}_"
            f"{orbit_number_str}_{cycle_number_str}_{processing_center}_"
            f"{processing_baseline}_{product_discriminator}"
        )
    if satellite == "S5P":
        return (
            f"{satellite}_{level}_{product_type}_{orbit_number_str}_"
            f"{sensing_start_fmt}_{sensing_end_fmt}_{processing_baseline}_"
            f"{product_discriminator}"
        )
    raise ValueError("Unsupported satellite!")


def parse_sentinel_filename_verbose(filename: str) -> Any:
    """Verbose function to parse a Sentinel-like filename."""
    filename = filename.upper()

    # Sentinel-1
    if filename.startswith("S1A_") or filename.startswith("S1B_"):
        parts = filename.split("_")
        if len(parts) == 8:
            mode_desc = S1_MODES.get(parts[1], "Unknown mode")
            prod_desc = S1_PRODUCTS.get(parts[2], "Unknown product type")
            res_desc = S1_RESOLUTIONS.get(parts[3], "Unknown resolution")
            return {
                "Satellite": f"Satellite: {parts[0]} (Sentinel-1)",
                "Mode": f"Mode: {parts[1]} ({mode_desc})",
                "Product_Type": f"Product Type: {parts[2]} ({prod_desc})",
                "Resolution": f"Resolution: {parts[3]} ({res_desc})",
                "Sensing_Start": (
                    "Sensing Start Time: "
                    f"{parts[4]} (Start time of the sensing operation)"
                ),
                "Orbit_Number": (
                    "Orbit Number: "
                    f"{parts[5]} (Relative orbit number, e.g., {parts[5]})"
                ),
                "Data_Take_ID": (
                    "Data Take ID: "
                    f"{parts[6]} (Unique identifier for the data take)"
                ),
                "Product_Discriminator": (
                    "Product Discriminator: "
                    f"{parts[7]} (Further identifies the product, e.g., processing details)"
                ),
            }
        return "The filename does not have the correct number of parts for Sentinel-1."

    # Sentinel-2
    if filename.startswith("S2A_") or filename.startswith("S2B_"):
        clean = filename[:-5] if filename.endswith(".SAFE") else filename
        parts = clean.split("_")
        if len(parts) == 7:
            instrument_code = parts[1][:3]
            level_code = parts[1][3:]
            instr_desc = S2_INSTRUMENTS.get(instrument_code, "Unknown instrument")
            level_desc = S2_LEVELS.get(level_code, "Unknown processing level")
            return {
                "Satellite": f"Satellite: {parts[0]} (Sentinel-2)",
                "Instrument": f"Instrument: {instrument_code} ({instr_desc})",
                "Level": f"Product Level: {level_code} ({level_desc})",
                "Sensing_Start": (
                    "Sensing Start Time: "
                    f"{parts[2]} (Start time of the sensing operation)"
                ),
                "Processing_Baseline": (
                    "Processing Baseline: "
                    f"{parts[3]} (Baseline number of the processing software)"
                ),
                "Orbit_Number": (
                    "Orbit Number: "
                    f"{parts[4]} (Relative orbit number, e.g., {parts[4]})"
                ),
                "Tile_ID": (
                    "Tile Identifier: "
                    f"{parts[5]} (Geographical tile ID, e.g., T31TCJ)"
                ),
                "Product_Discriminator": (
                    "Product Discriminator: "
                    f"{parts[6]} (Further identifies the product, e.g., processing details)"
                ),
            }
        return "The filename does not have the correct number of parts for Sentinel-2."

    # Sentinel-3
    if filename.startswith("S3A_") or filename.startswith("S3B_"):
        parts = filename.split("_")
        if len(parts) == 10:
            instrument_desc = S3_INSTRUMENTS.get(parts[1], "Unknown instrument")
            level_desc = S3_LEVELS.get(parts[2], "Unknown processing level")
            prod_desc = S3_PRODUCTS.get(parts[3], "Unknown product type")
            return {
                "Satellite": f"Satellite: {parts[0]} (Sentinel-3)",
                "Instrument": f"Instrument: {parts[1]} ({instrument_desc})",
                "Level": f"Product Level: {parts[2]} ({level_desc})",
                "Product_Type": f"Product Type: {parts[3]} ({prod_desc})",
                "Sensing_Start": (
                    "Sensing Start Time: "
                    f"{parts[4]} (Start time of the sensing operation)"
                ),
                "Orbit_Number": (
                    "Orbit Number: "
                    f"{parts[5]} (Relative orbit number, e.g., {parts[5]})"
                ),
                "Cycle_Number": (
                    "Cycle Number: "
                    f"{parts[6]} (Orbit cycle number, e.g., {parts[6]})"
                ),
                "Processing_Center": (
                    "Processing Center: "
                    f"{parts[7]} (Center where the product was processed, e.g., ESA)"
                ),
                "Processing_Baseline": (
                    "Processing Baseline: "
                    f"{parts[8]} (Baseline number of the processing software)"
                ),
                "Product_Discriminator": (
                    "Product Discriminator: "
                    f"{parts[9]} (Further identifies the product, e.g., processing details)"
                ),
            }
        return "The filename does not have the correct number of parts for Sentinel-3."

    # Sentinel-5P
    if filename.startswith("S5P_"):
        parts = filename.split("_")
        if len(parts) == 8:
            prod_desc = S5P_PRODUCTS.get(parts[2], "Unknown product type")
            return {
                "Satellite": f"Satellite: {parts[0]} (Sentinel-5P)",
                "Level": (
                    "Product Level: "
                    f"{parts[1]} (e.g., L2 for Level 2)"
                ),
                "Product_Type": f"Product Type: {parts[2]} ({prod_desc})",
                "Orbit_Number": (
                    "Orbit Number: "
                    f"{parts[3]} (Relative orbit number, e.g., {parts[3]})"
                ),
                "Sensing_Start": (
                    "Sensing Start Time: "
                    f"{parts[4]} (Start time of the sensing operation)"
                ),
                "Sensing_End": (
                    "Sensing End Time: "
                    f"{parts[5]} (End time of the sensing operation)"
                ),
                "Processing_Baseline": (
                    "Processing Baseline: "
                    f"{parts[6]} (Baseline number of the processing software)"
                ),
                "Product_Discriminator": (
                    "Product Discriminator: "
                    f"{parts[7]} (Further identifies the product, e.g., processing details)"
                ),
            }
        return "The filename does not have the correct number of parts for Sentinel-5P."

    return "Invalid or unsupported filename format."


@app.get("/generate")
def generate_endpoint(
    satellite: str,
    mode: Optional[str] = None,
    product_type: str = '',
    resolution: Optional[str] = None,
    level: Optional[str] = None,
    sensing_start: str = '',
    sensing_end: Optional[str] = None,
    orbit_number: int = 0,
    tile_id: Optional[str] = None,
    data_take_id: Optional[str] = None,
    cycle_number: Optional[int] = None,
    processing_center: Optional[str] = None,
    processing_baseline: str = '',
    product_discriminator: str = '',
    instrument: Optional[str] = None,
):
    try:
        filename = generate_sentinel_filename(
            satellite,
            mode,
            product_type,
            resolution,
            level,
            sensing_start,
            sensing_end,
            orbit_number,
            tile_id,
            data_take_id,
            cycle_number,
            processing_center,
            processing_baseline,
            product_discriminator,
            instrument,
        )
        return {"filename": filename}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/parse")
def parse_endpoint(filename: str):
    return parse_sentinel_filename_verbose(filename)