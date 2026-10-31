# Changelog

## 0.2

- Preview button: quick look of the selected scene and product, clipped to the AOI
- New product: Forest fire (QuickFire), Sentinel-2 only, with sensitivity, hotspot style and burn-scar options (AOI up to 0.5°)
- Layer names are now `<scene id>_<product>` with underscores (Sentinel-2: `S2C_MSIL2A_20261017T003701_True_colour_(RGB)`)
- Fix: loading failed on some Windows/QGIS setups with "HTTP response code 0" (now uses the OS certificate store)
- Declared QGIS 4 (Qt6) support in metadata
- Added a plugin icon
- Added docs/LIMITATIONS.md
- Renamed the plugin to TerraFetch (GPL-3.0-or-later licence, README with install steps and limitations)
- Renamed the plugin to TerraFetch (GPL-3.0-or-later licence, README with install steps and limitations)
- Help (?) button in the dialog: user guide, limitations and changelog
- New Satellite > Collection menu, with an "All collections" option that merges results into one list; added Landsat 1-5 MSS C2 L1

## 0.1 (initial)

- Search Sentinel-2 L2A, Sentinel-1 RTC and Landsat 4-9 C2 L2 via Microsoft Planetary Computer STAC
- Filter by canvas extent, date range and cloud cover
- Band composites: true colour, false colour, agriculture, SWIR; VV/VH radar
- Load streamed VRT into QGIS
- Export clipped, compressed GeoTIFF (AOI up to 1.5°)
