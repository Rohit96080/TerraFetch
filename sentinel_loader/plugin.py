import json
import os
import tempfile
from contextlib import contextmanager
from urllib.parse import urlencode

from osgeo import gdal
from qgis.core import (Qgis, QgsBlockingNetworkRequest, QgsCoordinateReferenceSystem,
                       QgsCoordinateTransform, QgsProject, QgsRasterLayer)
from qgis.PyQt.QtCore import QDate, Qt, QUrl
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.PyQt.QtWidgets import (QAction, QApplication, QComboBox, QDateEdit, QDialog,
                                 QFileDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
                                 QListWidget, QListWidgetItem, QProgressBar, QPushButton,
                                 QSpinBox, QVBoxLayout)

# Microsoft Planetary Computer: free STAC + anonymous signing tokens, covers both sensors.
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
SAS = "https://planetarycomputer.microsoft.com/api/sas/v1/token/"
MAX_EXPORT_DEG = 1.5  # refuse exports of a bigger AOI: it would pull gigabytes

# sensor label -> (collection, {product label: [asset keys]})
SENSORS = {
    "Sentinel-2 L2A (optical)": ("sentinel-2-l2a", {
        "True colour (RGB)": ["visual"],
        "False colour (NIR-R-G)": ["B08", "B04", "B03"],
        "Agriculture (SWIR-NIR-B)": ["B11", "B08", "B02"],
        "SWIR (B12-NIR-R)": ["B12", "B08", "B04"]}),
    "Sentinel-1 RTC (radar)": ("sentinel-1-rtc", {
        "VV": ["vv"], "VH": ["vh"], "VV + VH (2 bands)": ["vv", "vh"]}),
    "Landsat 4-9 Collection 2 L2 (optical)": ("landsat-c2-l2", {
        "True colour (RGB)": ["red", "green", "blue"],
        "False colour (NIR-R-G)": ["nir08", "red", "green"],
        "Agriculture (SWIR-NIR-B)": ["swir16", "nir08", "blue"],
        "SWIR (SWIR2-NIR-R)": ["swir22", "nir08", "red"]}),
}
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
QComboBox, QDateEdit, QSpinBox, QListWidget { color: white; background: rgba(255,255,255,16);
        border: 1px solid rgba(255,255,255,45); border-radius: 10px; padding: 6px 10px; }
QComboBox:focus, QDateEdit:focus, QSpinBox:focus { border: 1px solid rgba(125,185,255,230); }
QComboBox QAbstractItemView { color: white; background: rgb(30,40,66); border: 0;
        selection-background-color: rgb(59,100,200); }
QComboBox::drop-down, QDateEdit::drop-down { border: 0; width: 22px; }
QListWidget { padding: 4px; outline: 0; }
QListWidget::item { padding: 7px 8px; border-radius: 7px; }
QListWidget::item:hover { background: rgba(255,255,255,20); }
QListWidget::item:selected { background: rgba(59,130,246,170); color: white; }
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
        self.resize(480, 660)

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
        titles.addWidget(QLabel("Sentinel Loader", objectName="title"))
        titles.addWidget(QLabel("Sentinel-1/2 & Landsat imagery for the current map extent", objectName="sub"))
        head.addLayout(titles, 1)
        close = QPushButton("✕", objectName="x")
        close.clicked.connect(self.close)
        head.addWidget(close, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(head)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        self.sensor = QComboBox()
        self.sensor.addItems(SENSORS)
        self.sensor.currentTextChanged.connect(self.sensor_changed)
        self.product = QComboBox()
        today = QDate.currentDate()
        self.d0 = QDateEdit(today.addMonths(-1), calendarPopup=True)
        self.d1 = QDateEdit(today, calendarPopup=True)
        self.cloud = QSpinBox(minimum=0, maximum=100, value=20, suffix=" %")
        self.cloud_cap = QLabel("MAX CLOUD COVER", objectName="cap")
        for i, (cap, w) in enumerate((("SENSOR", self.sensor), ("PRODUCT", self.product),
                                      ("FROM", self.d0), ("TO", self.d1))):
            grid.addWidget(QLabel(cap, objectName="cap"), (i // 2) * 2, i % 2)
            grid.addWidget(w, (i // 2) * 2 + 1, i % 2)
        grid.addWidget(self.cloud_cap, 4, 0)
        grid.addWidget(self.cloud, 5, 0)
        lay.addLayout(grid)

        self.aoi_label = QLabel("AOI: current map canvas extent", objectName="cap")
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
        self.export_btn = QPushButton("Export GeoTIFF…")
        self.export_btn.clicked.connect(self.export)
        row.addWidget(self.load_btn)
        row.addWidget(self.export_btn)
        lay.addLayout(row)
        self.sensor_changed(self.sensor.currentText())
        self.sel_changed()

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
            "Sentinel Loader", msg, Qgis.MessageLevel.Success if ok else Qgis.MessageLevel.Critical, 6)

    def sensor_changed(self, name):
        self.product.clear()
        self.product.addItems(SENSORS[name][1])
        optical = SENSORS[name][0] != RADAR
        self.cloud.setVisible(optical)
        self.cloud_cap.setVisible(optical)
        self.scenes.clear()

    def sel_changed(self):
        on = bool(self.scenes.selectedItems())
        self.load_btn.setEnabled(on)
        self.export_btn.setEnabled(on)

    def aoi(self):
        canvas = self.iface.mapCanvas()
        xf = QgsCoordinateTransform(canvas.mapSettings().destinationCrs(),
                                    QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
        r = xf.transformBoundingBox(canvas.extent())
        return (max(r.xMinimum(), -180), max(r.yMinimum(), -90),
                min(r.xMaximum(), 180), min(r.yMaximum(), 90))

    def search(self):
        coll = SENSORS[self.sensor.currentText()][0]
        try:
            if self.d0.date() > self.d1.date():
                raise RuntimeError("'From' date is after 'To' date.")
            self.bbox = self.aoi()
            self.aoi_label.setText("AOI (lon/lat): %.4f, %.4f  →  %.4f, %.4f" % self.bbox)
            with busy():
                feats = stac_search(coll, self.bbox, self.d0.date().toString("yyyy-MM-dd"),
                                    self.d1.date().toString("yyyy-MM-dd"))
        except Exception as e:
            return self.report(str(e))
        if coll != RADAR:
            feats = [f for f in feats if f["properties"].get("eo:cloud_cover", 0) <= self.cloud.value()]
        self.scenes.clear()
        for f in feats:
            p = f["properties"]
            extra = (f"{p['eo:cloud_cover']:.0f}% cloud" if "eo:cloud_cover" in p
                     else f"{p.get('sat:orbit_state', '')} orbit")
            it = QListWidgetItem(f"{p['datetime'][:10]}   ·   {extra}   ·   {p.get('platform', '')}   ·   {f['id'][:28]}")
            it.setData(Qt.ItemDataRole.UserRole, f)
            self.scenes.addItem(it)
        if feats:
            self.report(f"{len(feats)} scenes found. Select one.", ok=True)
        else:
            self.report("No scenes found. Widen the dates, raise the cloud limit or move the map.")

    def current(self):
        """(scene, collection, product name, asset keys) for the selected scene."""
        coll, products = SENSORS[self.sensor.currentText()]
        name = self.product.currentText()
        return self.scenes.selectedItems()[0].data(Qt.ItemDataRole.UserRole), coll, name, products[name]

    def load(self):
        try:
            item, coll, name, keys = self.current()
            with busy():
                path = build_vrt(item, coll, keys)
                layer = QgsRasterLayer(path, f"{item['properties']['datetime'][:10]} {name}")
            if not layer.isValid():
                raise RuntimeError("QGIS could not read the imagery (network down or token expired?).")
            QgsProject.instance().addMapLayer(layer)
        except Exception as e:
            return self.report(str(e))
        # ponytail: streamed layers use a ~1h signed token; re-load the scene after that
        self.report(f"Loaded '{layer.name()}' (streamed; export it to keep a local copy).", ok=True)

    def export(self):
        w, s, e, n = self.bbox
        if max(e - w, n - s) > MAX_EXPORT_DEG:
            return self.report(f"AOI is larger than {MAX_EXPORT_DEG}° - zoom in, search again, then export.")
        item, coll, name, keys = self.current()
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
        self.iface.addRasterLayer(out, os.path.splitext(os.path.basename(out))[0])
        self.report(f"Exported to {out} and added to the project.", ok=True)


class SentinelLoader:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dlg = None

    def initGui(self):
        self.action = QAction("Sentinel Loader", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu("&Sentinel Loader", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        self.iface.removePluginMenu("&Sentinel Loader", self.action)
        self.iface.removeToolBarIcon(self.action)

    def run(self):
        self.dlg = self.dlg or Dialog(self.iface)
        self.dlg.show()
        self.dlg.raise_()
