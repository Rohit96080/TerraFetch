import json
import os
import tempfile
from contextlib import contextmanager
from urllib.parse import urlencode

import numpy as np
from osgeo import gdal
from qgis.core import (Qgis, QgsBlockingNetworkRequest, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsProject, QgsRasterLayer)
from qgis.PyQt.QtCore import QDate, Qt, QUrl
from qgis.PyQt.QtGui import QCursor, QPixmap
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import (QAction, QApplication, QComboBox, QDateEdit, QDialog,
                                 QCheckBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                                 QListWidget, QListWidgetItem, QProgressBar, QPushButton,
                                 QSpinBox, QTextBrowser, QVBoxLayout, QWidget)

# Microsoft Planetary Computer: free STAC + anonymous signing tokens, covers both sensors.
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/"
MAX_EXPORT_DEG = 1.5  # refuse exports of a bigger AOI: it would pull gigabytes
MAX_FIRE_DEG = 0.5  # the fire product is computed locally, so its AOI cap is tighter
FIRE = "Forest fire (QuickFire)"
FIRE_KEYS = ["B02", "B03", "B04", "B08", "B8A", "B11", "B12", "SCL"]  # SCL = cloud mask
FIRE_STYLES = {"Glow (heat tint)": 1, "Red": 2, "Yellow": 3, "Subtle red shift": 4}

# sensor label -> (collection, {product label: [asset keys]})
SENSORS = {
    "Sentinel-2 L2A (optical)": ("sentinel-2-l2a", {
        "True colour (RGB)": ["visual"],
        "False colour (NIR-R-G)": ["B08", "B04", "B03"],
        "Agriculture (SWIR-NIR-B)": ["B11", "B08", "B02"],
        "SWIR (B12-NIR-R)": ["B12", "B08", "B04"],
        FIRE: FIRE_KEYS}),
    "Sentinel-1 RTC (radar)": ("sentinel-1-rtc", {
        "VV": ["vv"], "VH": ["vh"], "VV + VH (2 bands)": ["vv", "vh"]}),
    "Landsat 4-9 Collection 2 L2 (optical)": ("landsat-c2-l2", {
        "True colour (RGB)": ["red", "green", "blue"],
        "False colour (NIR-R-G)": ["nir08", "red", "green"],
        "Agriculture (SWIR-NIR-B)": ["swir16", "nir08", "blue"],
        "SWIR (SWIR2-NIR-R)": ["swir22", "nir08", "red"]}),
    # ponytail: MSS asset keys are from memory of the PC catalogue; build_vrt reports any that are missing
    "Landsat 1-5 MSS C2 L1 (optical)": ("landsat-c2-l1", {
        "False colour (NIR-R-G)": ["nir08", "red", "green"]}),
}
# satellite -> its collections (the "sub menu"); all of them are what Planetary Computer hosts
FAMILIES = {
    "Sentinel-2": ["Sentinel-2 L2A (optical)"],
    "Sentinel-1": ["Sentinel-1 RTC (radar)"],
    "Landsat": ["Landsat 4-9 Collection 2 L2 (optical)", "Landsat 1-5 MSS C2 L1 (optical)"],
}
ALL = "All collections"
RADAR = "sentinel-1-rtc"  # the only collection without cloud cover

QSS = """
* { font-family: 'Segoe UI'; font-size: 13px; }
#glass { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
            stop:0 rgba(40,56,92,235), stop:1 rgba(18,24,43,235));
         border: 1px solid rgba(255,255,255,60); border-radius: 18px; }
QLabel { color: rgba(255,255,255,235); background: transparent; }
#title { font-size: 19px; font-weight: 600; }
#sub, #cap { color: rgba(255,255,255,150); font-size: 12px; }
#status { border-radius: 10px; padding: 9px 12px; background: rgba(255,255,255,18);
          border: 1px solid rgba(255,255,255,30); }
QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QListWidget { color: white; background: rgba(255,255,255,16);
        border: 1px solid rgba(255,255,255,45); border-radius: 10px; padding: 6px 10px; }
QComboBox:focus, QDateEdit:focus, QSpinBox:focus { border: 1px solid rgba(125,185,255,230); }
QComboBox QAbstractItemView { color: white; background: rgb(30,40,66); border: 0;
        selection-background-color: rgb(59,100,200); }
QComboBox::drop-down, QDateEdit::drop-down { border: 0; width: 22px; }
QListWidget { padding: 4px; outline: 0; }
QListWidget::item { padding: 7px 8px; border-radius: 7px; }
QListWidget::item:hover { background: rgba(255,255,255,20); }
QListWidget::item:selected { background: rgba(59,130,246,170); color: white; }
QCheckBox { color: rgba(255,255,255,235); }
QTextBrowser { color: white; background: rgba(255,255,255,16); border: 0; padding: 8px; }
QProgressBar { background: rgba(255,255,255,18); border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar::chunk { background: rgb(99,140,246); border-radius: 3px; }
QPushButton { color: white; background: rgba(255,255,255,22); border-radius: 10px;
              border: 1px solid rgba(255,255,255,55); padding: 9px 16px; }
QPushButton:hover { background: rgba(255,255,255,45); }
QPushButton:disabled { color: rgba(255,255,255,90); background: rgba(255,255,255,10); }
#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
              stop:0 rgba(59,130,246,255), stop:1 rgba(99,102,241,255));
           border: 1px solid rgba(255,255,255,70); font-weight: 600; }
#primary:hover { background: rgb(96,165,250); }
#x { padding: 2px 9px; border-radius: 12px; font-size: 14px; }
"""


@contextmanager
def busy():
    QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def get_json(url):
    # QGIS network stack so the user's QGIS proxy / auth settings apply
    req = QgsBlockingNetworkRequest()
    if req.get(QNetworkRequest(QUrl(url))) != req.NoError:
        raise RuntimeError(f"Network request failed: {req.errorMessage()}")
    return json.loads(bytes(req.reply().content()))


def stac_search(collection, bbox, d0, d1):
    q = urlencode({"collections": collection, "bbox": ",".join(f"{v:.6f}" for v in bbox),
                   "datetime": f"{d0}/{d1}", "limit": 100, "sortby": "-datetime"})
    return get_json(f"{STAC}/search?{q}")["features"]


def build_vrt(item, collection, keys):
    """Signed, streamed VRT of the chosen assets (nothing downloaded yet)."""
    token = get_json(SAS + collection)["token"]
    missing = [k for k in keys if k not in item["assets"]]
    if missing:
        raise RuntimeError(f"Scene {item['id']} has no {', '.join(missing)} asset.")
    urls = [f"/vsicurl/{item['assets'][k]['href']}?{token}" for k in keys]
    path = os.path.join(tempfile.mkdtemp(prefix="sentinel_"), f"{item['id']}.vrt")
    # separate=True takes band 1 of each file, so only for multi-file composites
    ds = gdal.BuildVRT(path, urls, separate=len(urls) > 1, resolution="highest")
    if ds is None:
        raise RuntimeError(f"Could not open the imagery: {gdal.GetLastErrorMsg() or 'unknown GDAL error'}")
    ds = None  # flush to disk
    return path


def layer_name(item, product):
    # Sentinel-2 ids look like S2C_MSIL2A_20261017T003701_R002_T..., keep the Copernicus-style prefix
    base = "_".join(item["id"].split("_")[:3]) if item["id"].startswith("S2") else item["id"]
    return f"{base}_{product}".replace(" ", "_")


def fire_tif(item, bbox, out, sens, style, burn, width=None, cb=None):
    """Port of QuickFire v1.0.0 by Pierre Markuse (CC BY 4.0): RGBA Byte GeoTIFF, hotspots tinted.
    Processed in row strips so memory stays flat. SCL replaces Sentinel Hub's CLP cloud mask."""
    w, s, e, n = bbox
    vrt = build_vrt(item, "sentinel-2-l2a", FIRE_KEYS)
    src = gdal.Translate(vrt[:-4] + "_aoi.vrt", vrt, format="VRT", projWin=[w, n, e, s],
                         projWinSRS="EPSG:4326", width=width or 0)
    if src is None:
        raise RuntimeError(f"Fire product failed: {gdal.GetLastErrorMsg() or 'AOI may be outside the scene.'}")
    sc = []  # DN -> reflectance (scale/offset differ between processing baselines)
    for k in FIRE_KEYS[:-1]:
        rb = item["assets"][k].get("raster:bands", [{}])[0]
        sc.append((rb.get("scale", 1e-4), rb.get("offset", 0)))
    W, H = src.RasterXSize, src.RasterYSize
    dst = gdal.GetDriverByName("GTiff").Create(out, W, H, 4, gdal.GDT_Byte, ["COMPRESS=DEFLATE", "TILED=YES"])
    dst.SetGeoTransform(src.GetGeoTransform())
    dst.SetProjection(src.GetProjection())
    dst.GetRasterBand(4).SetColorInterpretation(gdal.GCI_AlphaBand)
    th = [2.0, 1.5, 1.25, 1.0]
    for y in range(0, H, 512):
        h = min(512, H - y)
        a = src.ReadAsArray(0, y, W, h).astype("float32")
        B02, B03, B04, B08, B8A, B11, B12 = [np.clip(a[i] * sc[i][0] + sc[i][1], 0, None) for i in range(7)]
        scl = a[7]
        urban = [np.sqrt(1.2 * B12), np.sqrt(1.4 * B11), np.sqrt(B04)]
        nat = [2.5 * B04, 2.5 * B03, 2.5 * B02]
        cc = [np.sqrt(B04), np.sqrt(B03), np.sqrt(B02)]
        viz = np.stack([0.1 * u + 0.4 * c1 + 0.5 * c2 for u, c1, c2 in zip(urban, nat, cc)])
        viz = viz.mean(0) * (1 - 1.1) + viz * 1.1  # saturation 1.10
        viz = (viz - 0.01) / 0.98
        t = B11 + B12
        tier = sum((t > x / sens).astype(int) for x in th)  # 0 = none .. 4 = hottest
        hot = ((scl < 8) | (scl > 10)) & (B02 < 0.8) & (tier > 0)
        if style == 1:
            heat = [viz[0] + 0.5 * B12, viz[1] + np.array([0, 0, 0.1, 0.2, 0.5])[tier] * B11, viz[2]]
        elif style == 2:
            heat = [np.ones_like(t), np.zeros_like(t), np.zeros_like(t)]
        elif style == 3:
            heat = [np.ones_like(t), np.ones_like(t), np.zeros_like(t)]
        else:
            heat = [viz[0] + 0.2, viz[1] - 0.2, viz[2] - 0.2]
        if burn:
            scar = ~hot & ((B08 - B12) / (B08 + B12 + 1e-9) < -0.25)
            viz[0] += 0.3 * scar
            viz[1] += 0.3 * scar
        for i in range(3):
            res = (np.clip(np.where(hot, heat[i], viz[i]), 0, 1) * 255).astype("uint8")
            dst.GetRasterBand(i + 1).WriteArray(res, 0, y)
        dst.GetRasterBand(4).WriteArray(((a[2] > 0) * 255).astype("uint8"), 0, y)
        if cb:
            cb((y + h) / H)
    dst = src = None  # close/flush
    return out


class Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.bbox = None
        self._drag = None
        gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(QSS)
        self.resize(480, 720)

        glass = QFrame(objectName="glass")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(glass)
        lay = QVBoxLayout(glass)
        lay.setContentsMargins(22, 18, 22, 20)
        lay.setSpacing(4)

        head = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(0)
        titles.addWidget(QLabel("TerraFetch", objectName="title"))
        titles.addWidget(QLabel("Sentinel-1/2 & Landsat imagery for the current map extent", objectName="sub"))
        head.addLayout(titles, 1)
        helpb = QPushButton("?", objectName="x")
        helpb.setToolTip("User manual, features and limitations")
        helpb.clicked.connect(self.show_help)
        head.addWidget(helpb, 0, Qt.AlignmentFlag.AlignTop)
        close = QPushButton("✕", objectName="x")
        close.clicked.connect(self.close)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self.sensor = QComboBox()
        self.sensor.addItems(FAMILIES)
        self.sensor.currentTextChanged.connect(self.sensor_changed)
        self.collection = QComboBox()
        self.collection.currentTextChanged.connect(self.collection_changed)
        self.product = QComboBox()
        today = QDate.currentDate()
        self.d0 = QDateEdit(today.addMonths(-1), calendarPopup=True)
        self.d1 = QDateEdit(today, calendarPopup=True)
        self.cloud = QSpinBox(minimum=0, maximum=100, value=20, suffix=" %")
        self.cloud_cap = QLabel("MAX CLOUD COVER", objectName="cap")
        for i, (cap, w) in enumerate(((QLabel("SATELLITE", objectName="cap"), self.sensor),
                                      (QLabel("COLLECTION", objectName="cap"), self.collection),
                                      (QLabel("PRODUCT", objectName="cap"), self.product),
                                      (self.cloud_cap, self.cloud),
                                      (QLabel("FROM", objectName="cap"), self.d0),
                                      (QLabel("TO", objectName="cap"), self.d1))):
            grid.addWidget(cap, (i // 2) * 2, i % 2)
            grid.addWidget(w, (i // 2) * 2 + 1, i % 2)
        lay.addLayout(grid)

        self.fire_sens = QDoubleSpinBox(minimum=0.5, maximum=2.0, singleStep=0.1, value=1.0)
        self.fire_style = QComboBox()
        for k, v in FIRE_STYLES.items():
            self.fire_style.addItem(k, v)
        self.fire_burn = QCheckBox("Show burn scars")
        self.fire_box = QWidget()
        fg = QGridLayout(self.fire_box)
        fg.setContentsMargins(0, 4, 0, 0)
        fg.addWidget(QLabel("FIRE SENSITIVITY", objectName="cap"), 0, 0)
        fg.addWidget(QLabel("HOTSPOT STYLE", objectName="cap"), 0, 1)
        fg.addWidget(self.fire_sens, 1, 0)
        fg.addWidget(self.fire_style, 1, 1)
        fg.addWidget(self.fire_burn, 2, 0, 1, 2)
        lay.addWidget(self.fire_box)
        self.product.currentTextChanged.connect(lambda n: self.fire_box.setVisible(n == FIRE))

        self.aoi_label = QLabel("AOI: current map canvas extent (export up to 1.5°, fire product up to 0.5°)", objectName="cap")
        lay.addSpacing(4)
        lay.addWidget(self.aoi_label)
        self.search_btn = QPushButton("Search scenes", objectName="primary")
        self.search_btn.clicked.connect(self.search)
        lay.addWidget(self.search_btn)

        lay.addWidget(QLabel("SCENES", objectName="cap"))
        self.scenes = QListWidget()
        self.scenes.itemSelectionChanged.connect(self.sel_changed)
        lay.addWidget(self.scenes, 1)

        self.progress = QProgressBar(textVisible=False)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)
        self.status = QLabel("Zoom to your area, pick dates and search.", objectName="status")
        self.status.setWordWrap(True)
        lay.addWidget(self.status)

        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 0)
        self.load_btn = QPushButton("Load in QGIS", objectName="primary")
        self.load_btn.clicked.connect(self.load)
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.preview)
        self.export_btn = QPushButton("Export GeoTIFF…")
        self.export_btn.clicked.connect(self.export)
        row.addWidget(self.preview_btn)
        row.addWidget(self.load_btn)
        row.addWidget(self.export_btn)
        lay.addLayout(row)
        self.sensor_changed(self.sensor.currentText())
        self.sel_changed()

    def show_help(self):
        """Manual, AOI limits, limitations and history, from the bundled help.html."""
        try:
            with open(os.path.join(os.path.dirname(__file__), "help.html"), encoding="utf-8") as fh:
                html = fh.read()
        except OSError:
            html = "<p>help.html is missing from the plugin folder.</p>"
        dlg = QDialog(self)
        dlg.setWindowTitle("TerraFetch - Help")
        dlg.setStyleSheet("QDialog { background: rgb(28,38,64); }")
        dlg.resize(760, 760)
        view = QTextBrowser()
        view.document().setDefaultStyleSheet(
            "body { color: #e8ecf5; } h1 { color: #ffffff; } h2 { color: #8ab4ff; } "
            "a { color: #8ab4ff; } th { background-color: #2f4170; color: #ffffff; } "
            "td { color: #e8ecf5; } code { color: #ffd479; } .muted { color: #9aa6c4; }")
        view.setHtml(html)
        QVBoxLayout(dlg).addWidget(view)
        dlg.exec()

    def mousePressEvent(self, e):
        self._drag = QCursor.pos() - self.pos()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(QCursor.pos() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def report(self, msg, ok=False):
        self.status.setStyleSheet(f"background: {'rgba(34,197,94,70)' if ok else 'rgba(239,68,68,90)'};")
        self.status.setText(("✔  " if ok else "✖  ") + msg)
        self.iface.messageBar().pushMessage(
            "TerraFetch", msg, Qgis.MessageLevel.Success if ok else Qgis.MessageLevel.Critical, 6)

    def colls(self):
        """Collection labels to search: the chosen one, or every collection of the satellite."""
        c = self.collection.currentText()
        return FAMILIES[self.sensor.currentText()] if c == ALL else [c]

    def sensor_changed(self, name):
        self.collection.blockSignals(True)  # repopulate without half-built state reaching collection_changed
        self.collection.clear()
        if len(FAMILIES[name]) > 1:
            self.collection.addItem(ALL)
        self.collection.addItems(FAMILIES[name])
        self.collection.blockSignals(False)
        self.collection_changed()

    def collection_changed(self, _=None):
        labs = self.colls()
        self.product.clear()
        self.product.addItems(dict.fromkeys(p for l in labs for p in SENSORS[l][1]))  # union, ordered
        optical = any(SENSORS[l][0] != RADAR for l in labs)
        self.cloud.setVisible(optical)
        self.cloud_cap.setVisible(optical)
        self.scenes.clear()

    def sel_changed(self):
        on = bool(self.scenes.selectedItems())
        self.load_btn.setEnabled(on)
        self.preview_btn.setEnabled(on)
        self.export_btn.setEnabled(on)

    def aoi(self):
        canvas = self.iface.mapCanvas()
        xf = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(),
                                    QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
        r = xf.transformBoundingBox(canvas.extent())
        return (max(r.xMinimum(), -180), max(r.yMinimum(), -90),
                min(r.xMaximum(), 180), min(r.yMaximum(), 90))

    def search(self):
        labs = self.colls()
        try:
            if self.d0.date() > self.d1.date():
                raise RuntimeError("'From' date is after 'To' date.")
            self.bbox = self.aoi()
            self.aoi_label.setText("AOI (lon/lat): %.4f, %.4f  →  %.4f, %.4f" % self.bbox)
            with busy():
                feats = [f for l in labs for f in stac_search(
                    SENSORS[l][0], self.bbox, self.d0.date().toString("yyyy-MM-dd"),
                    self.d1.date().toString("yyyy-MM-dd"))]
        except Exception as e:
            return self.report(str(e))
        feats = [f for f in feats if f["collection"] == RADAR
                 or f["properties"].get("eo:cloud_cover", 0) <= self.cloud.value()]
        feats.sort(key=lambda f: f["properties"]["datetime"], reverse=True)
        self.scenes.clear()
        for f in feats:
            p = f["properties"]
            extra = (f"{p['eo:cloud_cover']:.0f}% cloud" if "eo:cloud_cover" in p
                     else f"{p.get('sat:orbit_state', '')} orbit")
            it = QListWidgetItem(f"{f['collection'] + '   ·   ' if len(labs) > 1 else ''}{p['datetime'][:10]}   ·   {extra}   ·   {p.get('platform', '')}   ·   {f['id'][:28]}")
            it.setData(Qt.ItemDataRole.UserRole, f)
            self.scenes.addItem(it)
        if feats:
            self.report(f"{len(feats)} scenes found. Select one.", ok=True)
        else:
            self.report("No scenes found. Widen the dates, raise the cloud limit or move the map.")

    def current(self):
        """(scene, collection, product name, asset keys) for the selected scene."""
        item = self.scenes.selectedItems()[0].data(Qt.ItemDataRole.UserRole)
        coll = item["collection"]  # in "All collections" mode scenes come from different collections
        products = next(v[1] for v in SENSORS.values() if v[0] == coll)
        name = self.product.currentText()
        if name not in products:
            raise RuntimeError(f"'{name}' is not available for {coll}. Pick another product or scene.")
        return item, coll, name, products[name]

    def fire(self, item, out, width=None):
        w, s, e, n = self.bbox
        if width is None and max(e - w, n - s) > MAX_FIRE_DEG:
            raise RuntimeError(f"AOI is larger than {MAX_FIRE_DEG}° for the fire product - zoom in and search again.")

        def cb(done):
            self.progress.setValue(int(done * 100))
            QApplication.processEvents()

        self.progress.setValue(0)
        self.progress.setVisible(True)
        try:
            return fire_tif(item, self.bbox, out, self.fire_sens.value(), self.fire_style.currentData(),
                            self.fire_burn.isChecked(), width, cb)
        finally:
            self.progress.setVisible(False)

    def preview(self):
        """Small auto-stretched PNG of the selected scene/product, clipped to the AOI."""
        try:
            item, coll, name, keys = self.current()
            w, s, e, n = self.bbox
            png = os.path.join(tempfile.mkdtemp(prefix="sentinel_"), "preview.png")
            with busy():
                if name == FIRE:
                    ds = gdal.Translate(png, self.fire(item, png[:-3] + "tif", width=480), format="PNG")
                else:
                    vrt = build_vrt(item, coll, keys)
                    bands = [1, 2, 3] if len(keys) >= 3 else [1, 2, 1] if len(keys) == 2 else [1]
                    ds = gdal.Translate(png, vrt, format="PNG", width=480, projWin=[w, n, e, s],
                                        projWinSRS="EPSG:4326", bandList=bands,
                                        outputType=gdal.GDT_Byte, scaleParams=[[]])
            if ds is None:
                raise RuntimeError(f"Preview failed: {gdal.GetLastErrorMsg() or 'AOI may be outside the scene.'}")
            ds = None  # close/flush
            pix = QPixmap(png)
        except Exception as ex:
            return self.report(str(ex))
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Preview - {layer_name(item, name)}")
        lab = QLabel()
        lab.setPixmap(pix)
        QVBoxLayout(dlg).addWidget(lab)
        dlg.exec()

    def load(self):
        try:
            item, coll, name, keys = self.current()
            with busy():
                path = (self.fire(item, os.path.join(tempfile.mkdtemp(prefix="sentinel_"), f"{item['id']}_fire.tif"))
                        if name == FIRE else build_vrt(item, coll, keys))
                layer = QgsRasterLayer(path, layer_name(item, name))
            if not layer.isValid():
                raise RuntimeError("QGIS could not read the imagery (network down or token expired?).")
            QgsProject.instance().addMapLayer(layer)
        except Exception as e:
            return self.report(str(e))
        # ponytail: streamed layers use a ~1h signed token; re-load the scene after that
        self.report(f"Loaded '{layer.name()}' ({'computed, saved in temp folder' if name == FIRE else 'streamed'}; "
                    "export it to keep a local copy).", ok=True)

    def export(self):
        w, s, e, n = self.bbox
        if max(e - w, n - s) > MAX_EXPORT_DEG:
            return self.report(f"AOI is larger than {MAX_EXPORT_DEG}° - zoom in, search again, then export.")
        try:
            item, coll, name, keys = self.current()
        except Exception as ex:
            return self.report(str(ex))
        out, _ = QFileDialog.getSaveFileName(
            self, "Export GeoTIFF", f"{item['id']}_{name.split()[0]}.tif", "GeoTIFF (*.tif)")
        if not out:
            return
        self.progress.setValue(0)
        self.progress.setVisible(True)

        def cb(done, msg, data):
            self.progress.setValue(int(done * 100))
            QApplication.processEvents()
            return 1

        try:
            with busy():
                if name == FIRE:
                    ds = self.fire(item, out)
                else:
                    vrt = build_vrt(item, coll, keys)
                    ds = gdal.Translate(out, vrt, projWin=[w, n, e, s], projWinSRS="EPSG:4326",
                                        creationOptions=["COMPRESS=DEFLATE", "TILED=YES"], callback=cb)
            if ds is None:
                raise RuntimeError(f"Export failed: {gdal.GetLastErrorMsg() or 'AOI may be outside the scene.'}")
            ds = None  # close/flush
        except Exception as ex:
            return self.report(str(ex))
        finally:
            self.progress.setVisible(False)
        self.iface.addRasterLayer(out, layer_name(item, name))
        self.report(f"Exported to {out} and added to the project.", ok=True)


class TerraFetch:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None

    def initGui(self):
        self.action = QAction("TerraFetch", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&TerraFetch", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&TerraFetch", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        self.dlg = self.dlg or Dialog(self.iface)
        self.dlg.show()
        self.dlg.raise_()
