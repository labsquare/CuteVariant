"""Plugin to show all characteristics of a selected variant

VariantInfoWidget is showed on the GUI, it uses VariantPopupMenu to display a
contextual menu about the variant which is selected.
VariantPopupMenu is also used in viewquerywidget for the same purpose.
"""
# Qt imports
from PySide2.QtCore import Qt, Slot, QSize
from PySide2.QtWidgets import *
from PySide2.QtGui import QFont

# Custom imports
from cutevariant.gui.ficon import FIcon
from cutevariant.core import sql, get_sql_connexion
from cutevariant.gui.plugin import PluginWidget
from cutevariant import commons as cm

LOGGER = cm.logger()


class VariantInfoWidget(PluginWidget):
    """Plugin to show all annotations of a selected variant"""

    GENOTYPES = {
        "-1": FIcon(0xF10D3),
        "0": FIcon(0xF0766),
        "1": FIcon(0xF0AA1),
        "2": FIcon(0xF0AA5),
    }

    ENABLE = True

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Info variants"))

        # Current variant => set by on_refresh and on_open_project
        self.current_variant = None

        self.view = QTabWidget()

        # Editor
        # TODO: edit comment on variant is disabled
        self.comment_input = QTextBrowser()
        self.comment_input.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.comment_input.setOpenExternalLinks(True)

        self.editor = QWidget()
        self.editor_layout = QVBoxLayout()

        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))

        # sub_edit_layout = QFormLayout()
        # editor_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        # sub_edit_layout.addWidget(self.comment_input)
        # sub_edit_layout.addWidget(self.save_button)

        self.editor_layout.addWidget(self.comment_input)
        # self.editor_layout.addWidget(self.save_button)

        self.editor.setLayout(self.editor_layout)
        # self.save_button.clicked.connect(self.on_save_clicked)

        # Build variant tab
        self.variant_view = QTreeWidget()
        self.variant_view.setColumnCount(2)
        self.variant_view.setAlternatingRowColors(True)
        self.variant_view.setHeaderLabels(["Field", "Value"])
        self.view.addTab(self.variant_view, "Variants")

        # build transcript tab
        self.transcript_combo = QComboBox()
        self.transcript_view = QTreeWidget()
        self.transcript_view.setColumnCount(2)
        self.transcript_view.setAlternatingRowColors(True)

        self.transcript_view.setHeaderLabels(["Field", "Value"])
        tx_layout = QVBoxLayout()
        tx_layout.addWidget(self.transcript_combo)
        tx_layout.addWidget(self.transcript_view)
        tx_widget = QWidget()
        tx_widget.setLayout(tx_layout)
        self.view.addTab(tx_widget, "Transcripts")
        self.transcript_combo.currentIndexChanged.connect(self.on_transcript_changed)

        # build Samples tab
        self.sample_combo = QComboBox()
        self.sample_view = QTreeWidget()
        self.sample_view.setAlternatingRowColors(True)

        self.sample_view.setColumnCount(2)
        self.sample_view.setHeaderLabels(["Field", "Value"])
        tx_layout = QVBoxLayout()
        tx_layout.addWidget(self.sample_combo)
        tx_layout.addWidget(self.sample_view)
        tx_widget = QWidget()
        tx_widget.setLayout(tx_layout)
        self.view.addTab(tx_widget, "Samples")
        self.sample_combo.currentIndexChanged.connect(self.on_sample_changed)

        # Build genotype tabs
        self.genotype_view = QListWidget()
        self.genotype_view.setIconSize(QSize(20, 20))
        self.view.addTab(self.genotype_view, "Genotypes")

        self.view.addTab(self.editor, self.tr("Comments"))

        # self.view.setColumnCount(2)
        # Set title of columns
        # self.view.setHeaderLabels([self.tr("Attributes"), self.tr("Values")])

        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.addWidget(self.view)
        self.setLayout(v_layout)

        # # Create menu
        # TODO: restore this
        # self.context_menu = VariantPopupMenu()
        # # Ability to trigger the menu
        # self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        # self.view.customContextMenuRequested.connect(self.show_menu)
        # self.add_tab("variants")

        # Cache all database fields and their descriptions for tooltips
        # Field names as keys, descriptions as values
        self.fields_descriptions = None

    def on_open_project(self, conn):
        self.conn = conn
        self.on_refresh()
        # Cache DB fields descriptions
        self.fields_descriptions = {
            field["name"]: field["description"]
            for field in sql.get_fields(self.conn)
        }

    def on_refresh(self):
        """Set the current variant by the variant displayed in the GUI"""
        self.current_variant = self.mainwindow.state.current_variant
        self.populate()

    def populate(self):
        """Show the current variant attributes on the TreeWidget

        .. note:: RichText in Markdown is supported starting PySide 5.14
        """
        if not self.current_variant or "id" not in self.current_variant:
            return

        variant_id = self.current_variant["id"]

        font = QFont()
        font.setBold(True)

        # Populate variant
        self.variant_view.clear()
        for field_name, value in sql.get_one_variant(self.conn, variant_id).items():
            item = QTreeWidgetItem()
            item.setText(0, field_name)
            item.setFont(0, font)
            item.setText(1, str(value))
            # Tooltips on header AND field => easier for user
            tooltip = self.fields_descriptions.get(field_name, "")
            item.setToolTip(0, tooltip)
            item.setToolTip(1, tooltip)

            if field_name == "comment":
                try:
                    self.comment_input.setMarkdown(str(value))
                except AttributeError:
                    # Fallback Qt 5.14-
                    self.comment_input.setPlainText(str(value))

            self.variant_view.addTopLevelItem(item)

        # Populate annotations
        self.transcript_combo.blockSignals(True)
        self.transcript_combo.clear()
        for annotation in sql.get_annotations(self.conn, variant_id):
            if "transcript" in annotation:
                self.transcript_combo.addItem(annotation["transcript"], annotation)
        self.on_transcript_changed()
        self.transcript_combo.blockSignals(False)

        # Populate samples
        self.sample_combo.blockSignals(True)
        self.sample_combo.clear()
        for sample in sql.get_samples(self.conn):
            self.sample_combo.addItem(sample["name"], sample["id"])
        self.on_sample_changed()
        self.sample_combo.blockSignals(False)

        # Populate genotype
        self.genotype_view.clear()
        q = f"SELECT samples.name, sv.gt FROM samples LEFT JOIN sample_has_variant sv ON samples.id = sv.sample_id AND sv.variant_id = {variant_id}"

        for row in self.conn.execute(q):
            item = QListWidgetItem()
            genotype = str(row[1])
            icon = self.GENOTYPES.get(genotype, self.GENOTYPES["-1"])

            item.setText(str(row[0]))
            item.setIcon(icon)

            self.genotype_view.addItem(item)

    @Slot()
    def on_transcript_changed(self):
        """This method is triggered when transcript change from combobox"""
        annotations = self.transcript_combo.currentData()
        font = QFont()
        font.setBold(True)
        self.transcript_view.clear()
        if annotations:
            for key, val in annotations.items():
                item = QTreeWidgetItem()
                item.setFont(0, font)
                item.setText(0, key)
                item.setText(1, str(val))

                self.transcript_view.addTopLevelItem(item)

    @Slot()
    def on_sample_changed(self):
        """This method is triggered when sample change from combobox"""
        sample_id = self.sample_combo.currentData()
        variant_id = self.current_variant["id"]
        font = QFont()
        font.setBold(True)
        self.sample_view.clear()
        ann = sql.get_sample_annotations(self.conn, variant_id, sample_id)
        if ann:
            for key, value in ann.items():
                item = QTreeWidgetItem()
                item.setText(0, key)
                item.setFont(0, font)
                item.setText(1, str(value))
                self.sample_view.addTopLevelItem(item)

    # @Slot()
    # def on_save_clicked(self):
    #     """Save button
    #     """
    #     classification = self.classification_box.currentIndex()
    #     favorite = self.favorite_checkbox.isChecked()
    #     comment = self.comment_input.toPlainText()

    #     updated = {
    #         "classification": classification,
    #         "favorite": favorite,
    #         "comment": comment,
    #     }

    #     if "variant_view" in self.mainwindow.plugins:
    #         main_view = self.mainwindow.plugins["variant_view"]
    #         print(main_view)

    # sql.update_variant(self.conn, updated)

    # def show_menu(self, pos: QPoint):
    #     """Show context menu associated to the current variant"""
    #     if not self.current_variant:
    #         return
    #     self.context_menu.popup(self.current_variant, self.view.mapToGlobal(pos))


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    conn = get_sql_connexion("/home/schutz/Dev/cutevariant/examples/test.db")

    w = VariantInfoWidget()
    w.conn = conn

    variant = sql.get_one_variant(conn, 1)

    w.current_variant = variant

    w.show()

    app.exec_()
