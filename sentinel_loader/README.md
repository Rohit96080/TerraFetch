# Sentinel Loader

QGIS plugin that searches **Sentinel-2 L2A**, **Sentinel-1 RTC** and **Landsat 4-9 Collection 2 L2** imagery for the current map extent, streams it into QGIS, and exports it as GeoTIFF. Data comes from the free [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) STAC API. No account or API key is needed.

- Version: 0.2
- Author: Rohit Kumar (rohit.kumar@azistaindustries.com)
- Requires: QGIS 3.30 or newer (QGIS 3 and 4 Qt bindings via `qgis.PyQt`), internet access

## Features

- Search by sensor, date range, cloud cover and the current canvas extent
- Band composites: true colour, false colour, agriculture and SWIR (optical); VV, VH, VV+VH (radar)
- **Preview** any scene and product before loading
- **Forest fire (QuickFire)** hotspot product for Sentinel-2
- Layers are named `S2C_MSIL2A_20261017T003701_True_colour_(RGB)`
- **Load in QGIS**: streams a signed VRT, with nothing downloaded up front
- **Export GeoTIFF**: clips to the AOI and writes a DEFLATE-compressed, tiled GeoTIFF
- Uses the QGIS network stack, so QGIS proxy and auth settings apply

## Install

1. Copy the `sentinel_loader` folder into the QGIS plugins directory:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS, then enable **Sentinel Loader** under *Plugins > Manage and Install Plugins > Installed*.
3. Open it from the toolbar icon or *Plugins > Sentinel Loader*.

## Documentation

| Document | Purpose |
|---|---|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Step-by-step usage, products, limits, troubleshooting |
| [docs/TECHNICAL.md](docs/TECHNICAL.md) | Architecture, data flow, code map, design decisions, known limitations |
| [docs/LIMITATIONS.md](docs/LIMITATIONS.md) | All known limits and caveats |
| [docs/TESTING.md](docs/TESTING.md) | Manual test plan and release checklist |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

## Project layout

```
sentinel_loader/
├── __init__.py     classFactory entry point
├── plugin.py       all plugin code (STAC client, VRT builder, dialog, plugin class)
├── metadata.txt    QGIS plugin metadata
└── docs/           guides
```

## Licence and data terms

Licence for this plugin: **to be decided** (add a LICENSE file before publishing; QGIS plugin repository requires one).
Imagery licences: Sentinel data is free and open (Copernicus); Landsat is public domain (USGS). Planetary Computer terms of use apply to the API.
