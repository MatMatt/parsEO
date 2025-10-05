# Determining a Landsat EPSG Code from Path/Row

Landsat Collection 1/2 Level-1 products use the UTM zone containing the scene center
as their native cartographic projection. Because each Worldwide Reference System 2
(WRS-2) path/row polygon is geographically fixed, you can infer the correct EPSG code
as long as you can locate that polygon and compute its centroid.

## Workflow

1. Download the WRS-2 descending path/row polygons from the USGS archive
   (e.g., `https://prd-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/atoms/files/WRS2_descending.zip`).
2. Use a spatial library such as `geopandas` to load the polygons.
3. Filter the dataset for the path/row of interest.
4. Compute the centroid latitude/longitude of the polygon.
5. Determine the UTM zone and hemisphere from that centroid.
6. Build the EPSG code: `EPSG:326##` for northern hemisphere zones, or `EPSG:327##` for southern hemisphere zones.

The repository now ships with a pre-computed lookup table (`parseo.data.load_landsat_epsg_lookup`) that
exposes this mapping directly, so most applications can avoid loading the shapefile at runtime.

The centroid-based approach matches what the Landsat Level-1 processing system uses to
select the UTM zone; therefore it returns the same EPSG code you will find in the
`*_MTL.txt` metadata file delivered with the scene.

## Example

```python
from parseo.data import LandsatSceneKey, load_landsat_epsg_lookup

lookup = load_landsat_epsg_lookup()
key = LandsatSceneKey(path=198, row=32).as_id()
print(lookup[key])
```

This returns the EPSG code for the UTM zone used by the requested path/row. For scenes
that cross multiple UTM zones, Landsat Level-1 processing still assigns the UTM zone
containing the centroid, so the pre-computed lookup remains valid.

To rebuild the lookup table from the authoritative WRS-2 polygons, run:

```bash
python scripts/build_landsat_epsg_lookup.py \
    /path/to/WRS2_descending.shp \
    src/parseo/data/landsat_epsg_lookup.json
```

Commit the regenerated JSON file to make the new mapping available to consumers.

> **Tip:** If you need only a quick lookup, you can query the WRS-2 API endpoint at
> `https://landsat.usgs.gov/wrs-api/v1/path/row` to retrieve the polygon metadata and
> compute the centroid without downloading the full shapefile.
