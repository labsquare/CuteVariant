# Qt imports
from PySide2.QtCore import qApp, Qt, QRect, QPoint, QBuffer, QByteArray
from PySide2.QtGui import (
    QIconEngine,
    QColor,
    QPainter,
    QIcon,
    QFontDatabase,
    QFont,
    QPalette,
    QPixmap,
    QPen,
)

# Custom imports
from cutevariant.commons import logger

LOGGER = logger()


class FIconEngine(QIconEngine):
    """Base class for FIcon; used to load custom font"""

    # Class attribute
    font = None

    def __init__(self):
        super().__init__()
        self.setColor(qApp.palette().color(QPalette.Normal, QPalette.Text))

    def setCharacter(self, hex_character: int):
        self.hex_character = hex_character

    def setColor(self, color: QColor):
        self.color = color

    def paint(
        self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State
    ):
        """override"""
        font = FIconEngine.font if hasattr(FIconEngine, "font") else painter.font()
        painter.save()

        if mode == QIcon.Disabled:
            painter.setPen(QPen(qApp.palette().color(QPalette.Disabled, QPalette.Text)))

        else:
            painter.setPen(QPen(self.color))

        
        #font.setPixelSize(rect.size().width())

        painter.setFont(font)
        # painter.setRenderHint(QPainter.HighQualityAntialiasing, True)
        painter.drawText(
            rect, Qt.AlignCenter | Qt.AlignVCenter, str(chr(self.hex_character))
        )
        painter.restore()

    def pixmap(self, size, mode, state):
        pix = QPixmap(size)
        pix.fill(Qt.transparent)
        painter = QPainter(pix)
        self.paint(painter, QRect(QPoint(0, 0), size), mode, state)
        return pix

    @classmethod
    def setFontPath(cls, filename):
        """Set font from a font file and return it

        :return: QFont or False if the file is not loaded
        """
        db = QFontDatabase()
        font_id = db.addApplicationFont(filename)
        if font_id == -1:
            LOGGER.error("FIconEngine:setFontPath:: cannot load font icon.")
            return False

        cls.font = QFont(db.applicationFontFamilies(font_id)[0])
        return cls.font


class FIcon(QIcon):
    """Handy public class to load and use custom font in QIcons"""

    def __init__(self, hex_character: int, color=None):
        """Build an icon with the given character and color from the current font"""
        self.engine = FIconEngine()
        self.engine.setCharacter(hex_character)
        if color:
            self.engine.setColor(color)
        else:
            self.engine.setColor(qApp.palette().text().color())
        super().__init__(self.engine)

    def to_base64(self, w=32, h=32):
        """Return icon as base64 to make it work with html"""
        pix = self.pixmap(w, h)
        data = QByteArray()
        buff = QBuffer(data)
        pix.save(buff, "PNG")
        return data.toBase64().data().decode()


def setFontPath(filename):
    """Handy function to load font file

    .. note:: Fonts are supposed to be in cm.DIR_FONTS
    .. note:: This function is called only 1 time at the start of the program
    """
    return FIconEngine.setFontPath(filename)
