# Sentinel Loader: Technical Documentation

## 1. Overview

Single-module QGIS plugin ([plugin.py](../plugin.py), about 330 lines). `__init__.classFactory` returns `SentinelLoader`, which owns a toolbar/menu action that shows a frameless, translucent `Dialog`.

## 2. Components

| Symbol | Role |
|---|---|
| `STAC`, `SAS` | Planetary Computer STAC root and SAS-token endpoint |
| `MAX_EXPORT_DEG` | Max AOI width/height for export (1.5°) |
| `SENSORS` | Table: sensor label → (collection, {product label → asset keys}). Add a sensor or product by adding an entry |
| `RADAR` | Collection with no cloud metadata (cloud UI hidden, filter skipped) |
| `QSS` | Glass-style stylesheet for the dialog |
| `busy()` | Context manager for the wait cursor |
| `get_json(url)` | GET via `QgsBlockingNetworkRequest`, so QGIS proxy and auth settings apply; returns parsed JSON |
| `stac_search(...)` | `GET /search` with collection, bbox, datetime, limit 100, `sortby=-datetime` |
| `build_vrt(item, coll, keys)` | Fetches a SAS token and builds a VRT over `/vsicurl/<href>?<token>` for each asset, with `separate=True` for multi-file composites and `resolution="highest"`. Written to a temp dir |
| `Dialog` | UI, search, load, export |
| `SentinelLoader` | Plugin lifecycle: `initGui`, `unload`, `run` |

Added in 0.2: `layer_name()` (layer naming), `fire_tif()` (QuickFire port; numpy, 512-row strips, RGBA Byte GeoTIFF; SCL cloud mask; scale/offset read from the item's `raster:bands`), `Dialog.preview()` and `Dialog.fire()`.

## 3. Data flow

```
canvas extent ──transform──▶ EPSG:4326 bbox ──STAC /search──▶ features
                                                              │ (cloud filter client-side)
                                                              ▼
                                                        QListWidget (feature stored in UserRole)
selected scene ──SAS token──▶ /vsicurl/ URLs ──gdal.BuildVRT──▶ temp .vrt
        ├─ Load:   QgsRasterLayer(vrt) ▶ QgsProject
        └─ Export: gdal.Translate(vrt, projWin=AOI, DEFLATE+TILED) ▶ .tif ▶ addRasterLayer
```

## 4. Key design decisions

- **Planetary Computer**: one free anonymous source covering all three sensors, with SAS tokens issued without credentials.
- **VRT streaming**: no download for *Load*; only visible blocks are fetched via HTTP range reads.
- **QGIS network stack for JSON calls**: honours user proxy and auth. GDAL's own HTTP (`/vsicurl`) does not use QGIS proxy settings. This is a known gap.
- **`GDAL_DISABLE_READDIR_ON_OPEN=EMPTY_DIR`**: avoids directory listing requests on blob URLs. It is set process-wide in `Dialog.__init__`.
- **Client-side cloud filter**: simpler than a STAC `query` extension filter. The cost is that the 100-scene cap applies before filtering.
- **Export AOI cap**: prevents accidental multi-GB downloads.

## 5. Known limitations and technical debt

| Area | Limitation | Upgrade path |
|---|---|---|
| Token lifetime | Streamed layers break after about 1 h (marked `ponytail:` in code) | Re-sign on expiry, or auto-reload |
| Pagination | Max 100 results, no next-page | Follow the STAC `next` link |
| Cloud filter | Applied after the 100-result cap | Use the STAC `query` / CQL2 filter server-side |
| Temp VRTs | Created with `mkdtemp`, never cleaned | Delete on `unload` or QGIS exit |
| GDAL proxy | `/vsicurl` ignores QGIS proxy settings | Set `GDAL_HTTP_PROXY` from QGIS settings |
| Footprint | AOI is not intersected with scene geometry before load | Client-side check; warn if disjoint |
| Mosaicking | One scene at a time, with no multi-tile mosaic | Build a VRT across scenes |
| Sentinel-2 composites | Raw reflectance, with no automatic stretch or scale | Apply a default contrast enhancement |
| Radar | Linear power, no dB conversion | Optional dB conversion |
| Dialog | `mouse*Event` drag applies anywhere on the dialog; no `closeEvent` cleanup | Restrict drag to the header |
| i18n / icon | No translations, and the action has no icon | Add resources |
| Fire product | See [LIMITATIONS.md](LIMITATIONS.md) | |
| Tests | No automated tests | See [TESTING.md](TESTING.md) |
| Metadata | `about` omits Landsat; no `tracker`, `repository`, `tags` or `license` | Update before publishing |

## 6. External services

- STAC: `https://planetarycomputer.microsoft.com/api/stac/v1/search`
- SAS tokens: `https://planetarycomputer.microsoft.com/api/sas/v1/token/<collection>` (anonymous, about 1 h validity)
- Data: Azure Blob storage URLs in each item's `assets[*].href`

## 7. Extending

- **New product**: add `"Label": [asset keys]` under the sensor in `SENSORS`. Asset keys must exist in the collection's STAC items.
- **New sensor**: add a `SENSORS` entry. If the collection has no `eo:cloud_cover`, handle it like `RADAR`.
- **Dependencies**: only QGIS-bundled `qgis.*`, `osgeo.gdal` and the standard library. Do not add pip dependencies.

## 8. Packaging for the QGIS plugin repository

1. Complete `metadata.txt`: `tracker`, `repository`, `homepage`, `tags`, `changelog`, `license`, `icon`, and correct `about`.
2. Add `LICENSE` (GPL-compatible).
3. Zip the `sentinel_loader/` folder (the folder name at zip root must match the plugin name, with no `.git` or `__pycache__`).
4. Upload at plugins.qgis.org.
