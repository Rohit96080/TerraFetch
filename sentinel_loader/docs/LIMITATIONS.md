# Sentinel Loader: Limitations

## Data and search
- Only collections hosted by Microsoft Planetary Computer are offered: Sentinel-2 L2A, Sentinel-1 RTC, Landsat C2 L2 and Landsat 1-5 MSS C2 L1. Not available: Sentinel-2 L1C, Sentinel-1 SLC/GRD, Sentinel-3, Sentinel-5P, Landsat Level-1 for TM/ETM+/OLI. Those need Copernicus Data Space or USGS accounts and downloads (not implemented).
- In "All collections" mode a product is only usable for scenes of collections that support it (e.g. MSS has only false colour).
- Landsat MSS band names were set from memory and are untested.
- Search returns at most **100 scenes**, newest first, with no paging. Narrow the dates to see older scenes.
- The cloud filter is applied **after** the 100-scene cap, so with a low limit fewer than 100 may remain.
- The AOI is always the **map canvas extent** at search time. Move the map, then search again.
- One scene at a time. There is no mosaicking of neighbouring tiles.
- Landsat products need all the listed bands. Some older missions lack them ("Scene … has no … asset").
- Internet access is required for everything. Source: Microsoft Planetary Computer, with no uptime guarantee.

## Load (streamed products)
- Streamed layers use a signed token valid for about **1 hour**. After that they stop rendering, so remove the layer and load it again.
- GDAL's remote reads (`/vsicurl`) do **not** use the QGIS proxy settings. JSON searches do.
- Composite bands (false colour, SWIR and so on) are raw reflectance. Adjust the stretch in Layer Styling.
- Radar is linear backscatter power, with no dB conversion.

## Preview
- Auto-stretched per band, so colours differ from the QGIS rendering.
- Black or no-data areas flatten the contrast.
- It takes a few seconds, because it streams the data at reduced size. For the fire product it runs the full calculation at low resolution.

## Forest fire (QuickFire)
- **Sentinel-2 only**. It needs the SWIR bands B11 and B12.
- Computed locally and saved to a temporary GeoTIFF (not streamed). Maximum AOI is **0.5°**, and it is slower than the other products.
- B11, B12, B8A and SCL are 20 m bands resampled to 10 m with nearest-neighbour, so hotspots look blocky.
- Cloud masking uses the scene's SCL band (classes 8, 9, 10) in place of Sentinel Hub's CLP. Results can differ from EO Browser.
- Hotspots are **indicative only**. Bright bare soil, sun glint, hot industrial sites or thin cloud can trigger false positives, and small or cool fires can be missed. Do not use it for operational fire detection. Use dedicated products such as NASA FIRMS.
- A Sentinel-2 revisit is about 5 days, so it is not a real-time tool.
- Based on QuickFire v1.0.0 by Pierre Markuse (CC BY 4.0). Keep the attribution.

## Export
- AOI up to **1.5°** (0.5° for the fire product).
- The AOI is fixed at search time, so re-search after moving the map.
- Export fails if the AOI does not intersect the scene.

## Plugin
- Temporary VRT/GeoTIFF files in the system temp folder are not cleaned up automatically.
- No automated tests, no translations, and no toolbar icon yet.
- Tested only by reading the code so far. Run [TESTING.md](TESTING.md) before relying on it.
