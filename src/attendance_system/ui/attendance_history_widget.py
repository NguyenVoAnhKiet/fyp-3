from __future__ import annotations

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
from attendance_system.ui.constants import FONT_TITLE
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

        # Header
        self.header_label = QLabel("Attendance History")
        self.header_label.setFont(FONT_TITLE)
        self.layout.addWidget(self.header_label)

        # Filters
        self.filters_layout = QHBoxLayout()

        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDate(QDate.currentDate().addMonths(-1))
        self.filters_layout.addWidget(QLabel("From:"))
        self.filters_layout.addWidget(self.from_date)

        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDate(QDate.currentDate())
        self.filters_layout.addWidget(QLabel("To:"))
        self.filters_layout.addWidget(self.to_date)

        self.class_filter = QComboBox()
        self.class_filter.addItem("All Classes", "")
        self.filters_layout.addWidget(QLabel("Class:"))
        self.filters_layout.addWidget(self.class_filter)

        self.subject_filter = QComboBox()
        self.subject_filter.addItem("All Subjects", "")
        self.filters_layout.addWidget(QLabel("Subject:"))
        self.filters_layout.addWidget(self.subject_filter)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_sessions)
        self.filters_layout.addWidget(self.search_button)

        self.filters_layout.addStretch()
        self.layout.addLayout(self.filters_layout)

        # Splitter for Split View
        self.splitter = QSplitter(Qt.Horizontal)

        # Left Pane: Session List
        self.left_pane = QFrame()
        self.left_pane.setFrameStyle(QFrame.StyledPanel)
        self.left_layout = QVBoxLayout(self.left_pane)
        self.left_layout.addWidget(QLabel("Sessions"))
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
        self.right_pane.setFrameStyle(QFrame.StyledPanel)
        self.right_layout = QVBoxLayout(self.right_pane)
        self.right_layout.addWidget(QLabel("Attendance Records"))

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(4)
        self.records_table.setHorizontalHeaderLabels(["Student ID", "Name", "Status", "Time"])
        self.records_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.records_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.right_layout.addWidget(self.records_table)

        # Export Actions
        self.export_layout = QHBoxLayout()
        self.export_excel_button = QPushButton("Export to Excel")
        self.export_excel_button.clicked.connect(self.export_excel)
        self.export_excel_button.setEnabled(False)

        self.export_csv_button = QPushButton("Export to CSV")
        self.export_csv_button.clicked.connect(self.export_csv)
        self.export_csv_button.setEnabled(False)

        self.export_layout.addStretch()
        self.export_layout.addWidget(self.export_excel_button)
        self.export_layout.addWidget(self.export_csv_button)
        self.right_layout.addLayout(self.export_layout)

        self.splitter.addWidget(self.left_pane)
        self.splitter.addWidget(self.right_pane)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)

        self.layout.addWidget(self.splitter)

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
        self.export_excel_button.setEnabled(False)
        self.export_csv_button.setEnabled(False)

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

        self.export_excel_button.setEnabled(True)
        self.export_csv_button.setEnabled(True)

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
