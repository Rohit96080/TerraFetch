# Sentinel Loader: User Guide

## 1. Quick start

Click the **?** button in the dialog header to open this guide, the limitations and the changelog.

1. Zoom the QGIS map canvas to your area of interest. The **current canvas extent is the search area**.
2. Open *Plugins > Sentinel Loader* (or the toolbar icon).
3. Choose **Satellite**, **Collection** (one collection, or *All collections* to search them all and list the results together), **Product**, **From / To** dates and (optical only) **Max cloud cover**.
4. Click **Search scenes**. Up to 100 of the newest scenes are listed.
5. Select a scene, optionally click **Preview** for a quick look, then click **Load in QGIS** (streams it) or **Export GeoTIFF…** (saves a local clipped file).

## 2. Sensors and products

| Sensor | Collection | Products (bands) |
|---|---|---|
| Sentinel-2 L2A (optical) | `sentinel-2-l2a` | True colour (visual); False colour NIR-R-G (B08,B04,B03); Agriculture SWIR-NIR-B (B11,B08,B02); SWIR B12-NIR-R (B12,B08,B04) |
| Sentinel-1 RTC (radar) | `sentinel-1-rtc` | VV; VH; VV + VH (2 bands) |
| Landsat 4-9 C2 L2 (optical) | `landsat-c2-l2` | True colour (red,green,blue); False colour (nir08,red,green); Agriculture (swir16,nir08,blue); SWIR (swir22,nir08,red) |

Radar has no cloud cover, so the cloud filter is hidden for Sentinel-1.

Sentinel-2 also offers **Forest fire (QuickFire)**: hotspots tinted over a natural-colour base. Extra controls appear: *Fire sensitivity* (higher shows more hotspots), *Hotspot style*, and *Show burn scars*. AOI is limited to 0.5°. Indicative only, see [LIMITATIONS.md](LIMITATIONS.md).

## 3. Scene list

Each row reads: `date · cloud % (or orbit direction for radar) · platform · scene ID`.
Cloud filtering is applied after the search, on the scene's `eo:cloud_cover` value.

## 4. Load vs Export

| | Load in QGIS | Export GeoTIFF |
|---|---|---|
| Data | Streamed on demand from Azure blob storage | Downloaded, clipped to AOI, written locally |
| Speed | Fast to appear, pans slower | Slower once, fast afterwards |
| Offline use | No | Yes |
| Size limit | None | AOI must be no more than 1.5° in width and height |
| Lifetime | Signed token lasts about 1 hour | Permanent |

After a successful export the file is added to the project automatically. Compression is DEFLATE, with tiling.

## 5. Limits and behaviour to know

- Search returns at most **100 scenes**, newest first. Narrow the dates to see older ones.
- The AOI is the canvas extent reprojected to EPSG:4326 and clamped to ±180°/±90°. The scene may cover more or less than the AOI.
- Streamed layers stop rendering after about an hour. Remove the layer and click **Load in QGIS** again.
- Export refuses an AOI larger than 1.5°. Zoom in, search again, then export. The AOI is fixed at search time, so re-search after you move the map.
- Internet access is required for search, load and export.

## 6. Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| "'From' date is after 'To' date." | Date range reversed | Swap the dates |
| "Network request failed: …" | No internet, proxy or firewall | Check QGIS *Settings > Options > Network*; make sure planetarycomputer.microsoft.com is reachable |
| "No scenes found…" | Range too narrow, cloud limit too low, or the map is over open ocean | Widen dates, raise cloud limit, move the map |
| "Scene … has no <asset> asset." | Chosen product is not available for that scene (older Landsat missions, for example) | Pick another scene or product |
| "Could not open the imagery: …" | GDAL could not open the remote files | Retry; check the network |
| "QGIS could not read the imagery (network down or token expired?)." | Token expired or connection lost | Click **Load in QGIS** again |
| "AOI is larger than 1.5° …" | Export area too big | Zoom in, search again, export |
| "Export failed: AOI may be outside the scene." | The AOI does not intersect the scene footprint | Select a scene covering the AOI |

## 7. Layer names

Loaded layers are named `<scene id>_<product>`, with spaces as underscores. Sentinel-2 uses the Copernicus prefix, e.g. `S2C_MSIL2A_20261017T003701_True_colour_(RGB)`. Sentinel-1 and Landsat use the full scene ID.

## 8. Tips

- For crisp results, zoom to the area before searching, not after.
- Sentinel-2 true colour uses the pre-rendered `visual` asset (8-bit). Composites use raw reflectance bands, so adjust the min/max stretch in *Layer Styling*.
- Radar backscatter is linear power. Use a stretch such as 0.0 to 0.5 for VV, or convert to dB with the raster calculator.
