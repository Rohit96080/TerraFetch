# Sentinel Loader: Test Plan

No automated tests exist yet. This is the manual plan. Run it on QGIS 3.30 (minimum) and the latest LTR.

## Test cases

| # | Scenario | Steps | Expected |
|---|---|---|---|
| 1 | Plugin loads | Enable the plugin | Toolbar icon and menu entry appear; no errors in the Python console |
| 2 | Dialog opens | Click the action twice | Same dialog is reused and raised |
| 3 | Sentinel-2 search | Zoom to a city, search the last month | Scenes listed with a cloud % |
| 4 | Cloud filter | Set 5%, search | All shown scenes are 5% or below |
| 5 | Radar search | Pick Sentinel-1 | Cloud control hidden; rows show orbit direction |
| 6 | Landsat search | Pick Landsat | Scenes listed |
| 7 | Date validation | From later than To | "'From' date is after 'To' date." |
| 8 | No results | Mid-ocean AOI | "No scenes found…" message |
| 9 | Load each product | For each sensor and product, Load | Layer added, renders, named `date product` |
| 10 | Export | Small AOI (under 1.5°), Export | Progress bar, `.tif` written, layer added, georeferenced correctly |
| 11 | Export too large | Zoom out, search, Export | AOI-too-large message, no file |
| 12 | Export cancel | Cancel the file dialog | Nothing happens |
| 13 | Disjoint AOI | Pick a scene not covering the AOI, Export | "Export failed… AOI may be outside the scene." |
| 14 | Offline | Disconnect network, Search | "Network request failed" shown, no crash |
| 15 | Token expiry | Load, wait 70 min, pan | Layer stops rendering; reload fixes it |
| 16 | Non-4326 canvas | Set project CRS to UTM or EPSG:3857, search | AOI shown in lon/lat, correct results |
| 17 | Antimeridian / poles | Extent beyond ±180°/±90° | Clamped, no crash |
| 18 | Unload / reload | Disable then enable plugin | Menu and toolbar entries removed, then restored; no duplicates |
| 19 | Product missing | Old Landsat scene lacking an asset | "Scene … has no … asset." |
| 21 | Preview | Select scene, Preview for each product | Image popup, clipped to AOI |
| 22 | Fire product | Sentinel-2 over a known fire, Search, Preview, Load, Export | Hotspots tinted; controls change the result; AOI over 0.5° refused |
| 23 | Layer name | Load any product | `S2C_MSIL2A_<datetime>_<product>` |
| 20 | Proxy | Configure a QGIS proxy | Search works through the proxy |

## Release checklist

- [ ] All test cases pass on the minimum and the latest QGIS
- [ ] `metadata.txt` complete (version, about, tracker, repository, tags, license)
- [ ] `LICENSE` and `CHANGELOG.md` updated
- [ ] Package contains no `__pycache__` or `.git`
- [ ] README install steps verified on a clean profile
