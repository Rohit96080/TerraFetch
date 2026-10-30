# TerraFetch

**TerraFetch** is a QGIS plugin that finds satellite imagery for the area on your map, lets you preview it, and loads it into QGIS or saves it as a GeoTIFF, without leaving QGIS and without creating any account.

Imagery comes from the free [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/) (Copernicus Sentinel data and USGS Landsat data).

- Version: 0.2
- Requires: QGIS 3.30 or newer and an internet connection
- Licence: GPL-3.0-or-later
- Author: Rohit Kumar (rohit.kumar@azistaindustries.com)

## What it does

| Satellite | Collection | Products |
|---|---|---|
| Sentinel-2 | L2A (optical, surface reflectance) | True colour, False colour (NIR-R-G), Agriculture (SWIR-NIR-B), SWIR (B12-NIR-R), Forest fire (QuickFire) |
| Sentinel-1 | RTC (radar, terrain-corrected) | VV, VH, VV + VH |
| Landsat | Collection 2 Level-2 (Landsat 4-9) | True colour, False colour, Agriculture, SWIR |
| Landsat | Landsat 1-5 MSS, Collection 2 Level-1 | False colour |

- Search by satellite, collection (or *All collections*), date range, cloud cover and the current map extent
- **Preview** a scene and product in a small window before using it
- **Load in QGIS**: adds the scene as a layer, streamed on demand (nothing is downloaded up front)
- **Export GeoTIFF**: clips to your area and saves a compressed, tiled GeoTIFF
- **Forest fire (QuickFire)**: Sentinel-2 hotspot visualisation with sensitivity, style and burn-scar options
- Built-in **Help** (the **?** button) with the manual and limitations
- Layers are named `<scene id>_<product>`, for example `S2C_MSIL2A_20261017T003701_True_colour_(RGB)`

## Install in QGIS

### Option A: from the ZIP file (recommended)

1. Download `TerraFetch.zip` from the [Releases page](https://github.com/Rohit96080/TerraFetch/releases), or download this repository as a ZIP and zip the `terrafetch` folder so that the ZIP contains a single top-level `terrafetch/` folder.
2. In QGIS open **Plugins > Manage and Install Plugins > Install from ZIP**.
3. Choose the ZIP file and click **Install Plugin**.
4. Make sure **TerraFetch** is ticked under **Installed**.
5. Open it from the toolbar icon or **Plugins > TerraFetch**.

### Option B: copy the folder

1. Copy the `terrafetch` folder into the QGIS plugins directory:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Restart QGIS.
3. Enable **TerraFetch** under **Plugins > Manage and Install Plugins > Installed**.

If you update the plugin, restart QGIS so the new version loads.

## How to use

1. Zoom the QGIS map to your area. **The visible map extent is the search area.**
2. Open TerraFetch and choose **Satellite**, **Collection** and **Product**.
3. Set the **From / To** dates and, for optical imagery, the **maximum cloud cover**.
4. Click **Search scenes**. Up to 100 of the newest scenes appear.
5. Select a scene, then **Preview**, **Load in QGIS** or **Export GeoTIFF**.

For the forest fire product, three extra controls appear: *Fire sensitivity* (higher shows more hotspots), *Hotspot style* and *Show burn scars*.

## Area of interest (AOI) limits

| Action | Maximum area |
|---|---|
| Search, Preview, Load (streamed products) | No limit |
| Export GeoTIFF | 1.5° wide and high (about 165 km) |
| Forest fire product (Load and Export) | 0.5° wide and high (about 55 km) |

The AOI is fixed when you click Search. If you move the map afterwards, search again.

## Limitations

- **Data source:** only collections hosted by Microsoft Planetary Computer are offered. Not available: Sentinel-2 L1C, Sentinel-1 GRD/SLC, Sentinel-3, Sentinel-5P, and Landsat Level-1 for Landsat 4-9. These would need Copernicus Data Space or USGS accounts and large downloads.
- **Search:** at most 100 scenes per collection, with no paging. The cloud filter is applied after that cap. Narrow the dates to reach older scenes.
- **One scene at a time:** no mosaicking of neighbouring tiles.
- **Streaming:** loaded layers use a signed link that expires after about 1 hour. If a layer stops drawing, remove it and load the scene again. Remote reads do not use the QGIS proxy settings.
- **Preview:** auto-stretched, so colours differ from the QGIS rendering. For the fire product it runs the full calculation at low resolution.
- **Composites and radar:** composite bands are raw reflectance, so adjust the stretch in Layer Styling. Radar is linear backscatter power, with no dB conversion.
- **Forest fire product:** indicative only, and not for operational fire detection. It is a visual aid based on the QuickFire script, not an official Copernicus product. 20 m bands are resampled to 10 m, so hotspots look blocky. Bright soil, sun glint or hot industrial sites can cause false alarms, and small or cool fires can be missed. Sentinel-2 revisits about every 5 days, so it is not real time. Cloud masking uses the scene classification band, which can differ from other tools. For fire information you rely on, use EFFIS or NASA FIRMS.
- **Landsat MSS:** band names are not yet tested.
- **Housekeeping:** temporary files are not deleted automatically. There are no automated tests yet, and the plugin has not been fully tested across QGIS versions.
- **Availability:** the service is provided by Microsoft Planetary Computer, which may change or be unavailable.

## Troubleshooting

| Message | What to do |
|---|---|
| "No scenes found" | Widen the dates, raise the cloud limit, or move the map |
| "Network request failed" | Check your internet, proxy or firewall |
| "Scene … has no … asset" | The product is not available for that scene; pick another |
| "AOI is larger than …" | Zoom in, search again, then retry |
| Layer stops drawing after about an hour | Remove it and click Load in QGIS again |

## Credits and licence

- The forest fire product is based on **QuickFire V1.0.0 by Pierre Markuse**, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
- Imagery: contains modified Copernicus Sentinel data and USGS Landsat data, served by Microsoft Planetary Computer. Follow their terms of use.
- TerraFetch is free software released under the **GNU General Public License v3.0 or later**. See [LICENSE](LICENSE).

## Support

Report problems at https://github.com/Rohit96080/TerraFetch/issues
