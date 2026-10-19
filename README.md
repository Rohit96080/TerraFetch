# Sentinel Loader – QGIS plugin

Search, preview and export **Sentinel-2**, **Sentinel-1** and **Landsat 4-9** imagery for the current QGIS map extent, without leaving QGIS and without creating any account.

Imagery comes from the free [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) STAC API. Scenes are streamed as virtual rasters (VRT), so nothing is downloaded until you export.

## Features

- **Three sensors**
  - Sentinel-2 L2A (optical)
  - Sentinel-1 RTC (radar)
  - Landsat 4-9 Collection 2 Level-2 (optical)
- **Band composites** per sensor:

  | Sensor | Products |
  |---|---|
  | Sentinel-2 L2A | True colour (RGB), False colour (NIR-R-G), Agriculture (SWIR-NIR-B), SWIR (B12-NIR-R) |
  | Sentinel-1 RTC | VV, VH, VV + VH (2 bands) |
  | Landsat C2 L2 | True colour (RGB), False colour (NIR-R-G), Agriculture (SWIR-NIR-B), SWIR (SWIR2-NIR-R) |

- **Search by map extent**: the AOI is the current canvas extent, reprojected to EPSG:4326.
- **Filters**: date range and maximum cloud cover (optical sensors only).
- **Scene list**: date, cloud cover (or orbit direction for radar), platform and scene ID, newest first (up to 100 results).
- **Load in QGIS**: adds the selected scene as a streamed layer.
- **Export GeoTIFF**: clips the scene to the AOI and saves a DEFLATE-compressed, tiled GeoTIFF, then adds it to the project.
- Uses the QGIS network stack, so your QGIS proxy and authentication settings apply.
- Frameless "glass" dialog that can be dragged by its body.

## Requirements

- QGIS **3.30 or newer** (GDAL and PyQt come with QGIS)
- Internet access

## Installation

1. Download or clone this repository.
2. Copy the inner `sentinel_loader` folder into your QGIS plugins directory:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. In QGIS: **Plugins → Manage and Install Plugins → Installed**, tick **Sentinel Loader**.

A **Sentinel Loader** button is added to the toolbar and to the **Plugins** menu.

## Usage

1. Zoom the map to your area of interest.
2. Open **Sentinel Loader**.
3. Choose the sensor, product, date range and (for optical) the maximum cloud cover.
4. Click **Search scenes** and select a scene from the list.
5. Click **Load in QGIS** to stream it, or **Export GeoTIFF…** to save a local copy.

## How it works

1. Queries the Planetary Computer STAC `/search` endpoint with the AOI bbox and date range.
2. Requests a short-lived anonymous SAS token for the collection.
3. Builds a GDAL VRT over `/vsicurl/` URLs of the chosen assets (one file per band, stacked for composites).
4. Loads the VRT, or runs `gdal.Translate` with the AOI as the window to export.

## Limitations

- Streamed layers use a signed token valid for about one hour. Reload the scene after that, or export it.
- Export is refused when the AOI is larger than **1.5°** on either side, to avoid pulling gigabytes of data. Zoom in, search again, then export.
- One scene at a time: mosaicking several scenes is not supported.

## Project layout

```
sentinel_loader/
├── __init__.py     # QGIS entry point (classFactory)
├── metadata.txt    # plugin metadata
└── plugin.py       # dialog, STAC search, VRT building, export
```

## Data

Imagery © ESA / Copernicus (Sentinel) and USGS / NASA (Landsat), served by Microsoft Planetary Computer. Check their terms of use before redistributing data.

## Author

Rohit Kumar
