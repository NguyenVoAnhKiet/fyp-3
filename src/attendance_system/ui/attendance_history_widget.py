from __future__ import annotations

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QAction,
    QComboBox,
    QDateEdit,
    QGraphicsDropShadowEffect,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from attendance_system.core.db import Database
from attendance_system.services.attendance_service import AttendanceService
from attendance_system.ui.styles import BG_CARD, BORDER, FONT_H1, FONT_H3, FONT_SMALL, TEXT_SECONDARY
from attendance_system.utils.time_utils import local_to_utc, utc_to_local


class AttendanceHistoryWidget(QWidget):
    def __init__(self, database: Database, parent=None):
        super().__init__(parent)
        self.attendance_service = AttendanceService(database)
        self._build_ui()
        self.load_filters()
        self.search_sessions()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(16)

        # Header
        self.header_label = QLabel("Lịch Sử Điểm Danh")
        self.header_label.setFont(FONT_H1)
        self.layout.addWidget(self.header_label)

        # Filters
        self.filters_layout = QHBoxLayout()
        self.filters_layout.setContentsMargins(0, 0, 0, 0)
        self.filters_layout.setSpacing(10)

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        from_label = QLabel("From:")
        from_label.setFont(FONT_SMALL)
        from_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.filters_layout.addWidget(from_label)
        self.filters_layout.addWidget(self.from_date)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        to_label = QLabel("To:")
        to_label.setFont(FONT_SMALL)
        to_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.filters_layout.addWidget(to_label)
        self.filters_layout.addWidget(self.to_date)

        self.class_filter = QComboBox()
        self.class_filter.addItem("All Classes", "")
        class_label = QLabel("Class:")
        class_label.setFont(FONT_SMALL)
        class_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.filters_layout.addWidget(class_label)
        self.filters_layout.addWidget(self.class_filter)

        self.subject_filter = QComboBox()
        self.subject_filter.addItem("All Subjects", "")
        subject_label = QLabel("Subject:")
        subject_label.setFont(FONT_SMALL)
        subject_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.filters_layout.addWidget(subject_label)
        self.filters_layout.addWidget(self.subject_filter)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_sessions)
        self.filters_layout.addWidget(self.search_button)

        self.filters_layout.addStretch()
        self.layout.addLayout(self.filters_layout)

        # Splitter for Split View
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(12)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStyleSheet(
            f"QSplitter::handle {{ background-color: {BORDER}; }}"
            f"QSplitter::handle:hover {{ background-color: {TEXT_SECONDARY}; }}"
        )

        # Left Pane: Session List
        self.left_pane = QFrame()
        self.left_pane.setFrameStyle(QFrame.NoFrame)
        self.left_pane.setObjectName("leftPane")
        self.left_pane.setStyleSheet(
            "#leftPane {"
            f"  background-color: {BG_CARD};"
            f"  border: 1px solid {BORDER};"
            "  border-radius: 8px;"
            "}"
        )
        self.left_pane.setGraphicsEffect(self._make_card_shadow())
        self.left_layout = QVBoxLayout(self.left_pane)
        self.left_layout.setContentsMargins(16, 16, 16, 16)
        self.left_layout.setSpacing(12)

        self.sessions_label = QLabel("Sessions")
        self.sessions_label.setFont(FONT_H3)
        self.left_layout.addWidget(self.sessions_label)
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(4)
        self.session_table.setHorizontalHeaderLabels(["ID", "Date", "Class", "Subject"])
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.session_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.session_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.session_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.session_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.session_table.itemSelectionChanged.connect(self.on_session_selected)
        self.left_layout.addWidget(self.session_table)

        # Right Pane: Session Details
        self.right_pane = QFrame()
        self.right_pane.setFrameStyle(QFrame.NoFrame)
        self.right_pane.setObjectName("rightPane")
        self.right_pane.setStyleSheet(
            "#rightPane {"
            f"  background-color: {BG_CARD};"
            f"  border: 1px solid {BORDER};"
            "  border-radius: 8px;"
            "}"
        )
        self.right_pane.setGraphicsEffect(self._make_card_shadow())
        self.right_layout = QVBoxLayout(self.right_pane)
        self.right_layout.setContentsMargins(16, 16, 16, 16)
        self.right_layout.setSpacing(12)

        self.records_label = QLabel("Attendance Records")
        self.records_label.setFont(FONT_H3)
        self.right_layout.addWidget(self.records_label)

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(4)
        self.records_table.setHorizontalHeaderLabels(["Student ID", "Name", "Status", "Time"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.right_layout.addWidget(self.records_table)

        # Export dropdown
        self.export_layout = QHBoxLayout()
        self.export_layout.addStretch()

        self.export_menu = QMenu()
        self.export_excel_action = QAction("📊 Excel (.xlsx)")
        self.export_excel_action.triggered.connect(self.export_excel)
        self.export_menu.addAction(self.export_excel_action)

        self.export_csv_action = QAction("📄 CSV (.csv)")
        self.export_csv_action.triggered.connect(self.export_csv)
        self.export_menu.addAction(self.export_csv_action)

        self.export_button = QPushButton("Xuất Báo Cáo")
        self.export_button.setMenu(self.export_menu)
        self.export_button.setStyleSheet("font-size: 15px;")
        self.export_button.setEnabled(False)

        self.export_layout.addWidget(self.export_button)
        self.right_layout.addLayout(self.export_layout)

        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.right_pane)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        self.layout.addWidget(self.splitter)

    def _make_card_shadow(self) -> QGraphicsDropShadowEffect:
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(15, 23, 42, 24))
        return shadow

    def load_filters(self):
        classes = self.attendance_service.get_unique_classes()
        for c in classes:
            self.class_filter.addItem(c, c)

        subjects = self.attendance_service.get_unique_subjects()
        for s in subjects:
            self.subject_filter.addItem(s, s)

    def search_sessions(self):
        # Convert UI date filter (local timezone) to UTC for DB query
        start_date = local_to_utc(self.from_date.date().toString(Qt.ISODate) + "T00:00:00")
        end_date = local_to_utc(self.to_date.date().toString(Qt.ISODate) + "T23:59:59")
        class_name = self.class_filter.currentData() or None
        subject_name = self.subject_filter.currentData() or None

        sessions = self.attendance_service.get_sessions(
            start_date=start_date, end_date=end_date, class_name=class_name, subject_name=subject_name
        )

        self.session_table.setRowCount(len(sessions))
        for i, session in enumerate(sessions):
            self.session_table.setItem(i, 0, QTableWidgetItem(str(session["id"])))
            self.session_table.setItem(i, 1, QTableWidgetItem(utc_to_local(session["start_time"])[:10]))
            self.session_table.setItem(i, 2, QTableWidgetItem(session["class_name"]))
            self.session_table.setItem(i, 3, QTableWidgetItem(session["subject_name"]))

        self.records_table.setRowCount(0)
        self.export_button.setEnabled(False)

    def on_session_selected(self):
        selected_rows = self.session_table.selectedItems()
        if not selected_rows:
            return

        session_id = int(self.session_table.item(selected_rows[0].row(), 0).text())
        records = self.attendance_service.get_session_records(session_id)

        self.records_table.setRowCount(len(records))
        for i, rec in enumerate(records):
            self.records_table.setItem(i, 0, QTableWidgetItem(rec["student_id"]))
            self.records_table.setItem(i, 1, QTableWidgetItem(rec["full_name"]))
            self.records_table.setItem(i, 2, QTableWidgetItem(rec["status"]))
            self.records_table.setItem(i, 3, QTableWidgetItem(utc_to_local(rec["recorded_at"]).split("T")[-1][:8]))

        self.export_button.setEnabled(True)

    def get_selected_session_id(self):
        selected_rows = self.session_table.selectedItems()
        if not selected_rows:
            return None
        return int(self.session_table.item(selected_rows[0].row(), 0).text())

    def export_excel(self):
        session_id = self.get_selected_session_id()
        if not session_id:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export to Excel", "", "Excel Files (*.xlsx)")
        if path:
            try:
                self.attendance_service.export_session_to_excel(session_id, path)
                QMessageBox.information(self, "Success", "Data exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")

    def export_csv(self):
        session_id = self.get_selected_session_id()
        if not session_id:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                self.attendance_service.export_session_to_csv(session_id, path)
                QMessageBox.information(self, "Success", "Data exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
