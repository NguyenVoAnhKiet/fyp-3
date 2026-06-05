from __future__ import annotations

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QLabel, QDialog, QFormLayout, 
    QLineEdit, QMessageBox, QAbstractItemView
)
from attendance_system.ui.constants import FONT_TITLE
from attendance_system.repositories.user_repository import UserRepository
from attendance_system.repositories.face_reference_repository import FaceReferenceRepository
from attendance_system.repositories.caching_face_reference_repository import (
    CachingFaceReferenceRepository,
)
from attendance_system.core.db import Database


class UserDialog(QDialog):
    def __init__(self, parent=None, user_data=None):
        super().__init__(parent)
        self.user_data = user_data
        self.is_edit_mode = user_data is not None
        self.setWindowTitle("Edit User" if user_data else "Add User")
        self.setMinimumWidth(400)
        
        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        
        self.student_id_input = QLineEdit()
        self.full_name_input = QLineEdit()
        
        if user_data:
            # Edit mode: show student_id as read-only
            self.student_id_input.setText(user_data["student_id"])
            self.student_id_input.setEnabled(False)
            self.full_name_input.setText(user_data["full_name"])
            self.form_layout.addRow("Student ID:", self.student_id_input)
        
        # Full name is always shown and editable
        self.form_layout.addRow("Full Name:", self.full_name_input)
        
        self.layout.addLayout(self.form_layout)
        
        self.buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.save_button)
        self.buttons_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.buttons_layout)

    def get_data(self):
        return {
            "student_id": self.student_id_input.text().strip() if self.is_edit_mode else None,
            "full_name": self.full_name_input.text().strip(),
        }


class UserManagementWidget(QWidget):
    def __init__(
        self,
        database: Database,
        parent=None,
        face_repo: FaceReferenceRepository | CachingFaceReferenceRepository | None = None,
    ):
        super().__init__(parent)
        self.database = database
        self.user_repo = UserRepository(database)
        # If caller didn't supply a face_repo, default to a bare repo (legacy
        # callers, tests). Production wires CachingFaceReferenceRepository in
        # main.py so user-delete invalidates the recognizer's cache.
        if face_repo is None:
            face_repo = FaceReferenceRepository(database)
        self.face_repo = face_repo
        
        self._build_ui()
        self.load_users()

    def _build_ui(self):
        self.layout = QVBoxLayout(self)
        
        # Header
        self.header_label = QLabel("User Management")
        self.header_label.setFont(FONT_TITLE)
        self.layout.addWidget(self.header_label)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("\U0001f50d Tìm kiếm theo tên hoặc mã SV...")
        self.search_bar.setClearButtonEnabled(True)
        self.search_bar.textChanged.connect(self._filter_users)
        self.layout.addWidget(self.search_bar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Student ID", "Full Name"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.layout.addWidget(self.table)
        
        # Actions
        self.actions_layout = QHBoxLayout()
        self.add_button = QPushButton("Add User")
        self.add_button.clicked.connect(self.add_user)
        self.edit_button = QPushButton("Edit User")
        self.edit_button.clicked.connect(self.edit_user)
        self.delete_button = QPushButton("Delete User")
        self.delete_button.clicked.connect(self.delete_user)
        
        self.actions_layout.addWidget(self.add_button)
        self.actions_layout.addWidget(self.edit_button)
        self.actions_layout.addWidget(self.delete_button)
        self.actions_layout.addStretch()
        self.layout.addLayout(self.actions_layout)

    def load_users(self):
        users = self.user_repo.list_active()
        self.table.setRowCount(len(users))
        for i, user in enumerate(users):
            self.table.setItem(i, 0, QTableWidgetItem(str(user["id"])))
            self.table.setItem(i, 1, QTableWidgetItem(user["student_id"]))
            self.table.setItem(i, 2, QTableWidgetItem(user["full_name"]))

    def _filter_users(self, text: str) -> None:
        for row in range(self.table.rowCount()):
            match = False
            for col in [1, 2]:  # student_id and full_name columns
                item = self.table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def _generate_student_id(self) -> str:
        """Generate next student_id as STU + (MAX(id) + 1)."""
        with self.database.session() as conn:
            result = conn.execute(
                "SELECT MAX(id) as max_id FROM users"
            ).fetchone()
            max_id = result["max_id"] if result["max_id"] is not None else 0
            next_id = max_id + 1
            return f"STU{next_id}"

    def add_user(self):
        dialog = UserDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["full_name"]:
                QMessageBox.warning(self, "Validation Error", "Full name is required.")
                return
            try:
                # Auto-generate student_id: STU + (MAX(id) + 1)
                student_id = self._generate_student_id()
                self.user_repo.create(student_id, data["full_name"])
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"User created successfully!\n\nStudent ID: {student_id}\nName: {data['full_name']}"
                )
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add user: {str(e)}")

    def edit_user(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a user to edit.")
            return
            
        user_id = int(self.table.item(selected_row, 0).text())
        user_data = self.user_repo.get_by_id(user_id)
        
        dialog = UserDialog(self, user_data)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["full_name"]:
                QMessageBox.warning(self, "Validation Error", "Full name is required.")
                return
            try:
                self.user_repo.update(user_id, full_name=data["full_name"])
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update user: {str(e)}")

    def delete_user(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a user to delete.")
            return
            
        user_id = int(self.table.item(selected_row, 0).text())
        student_id = self.table.item(selected_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete user {student_id}?\n\n"
            "This will delete their face data but preserve historical attendance records.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Soft delete user and remove face references
                self.user_repo.deactivate(user_id)
                self.face_repo.delete_by_user_id(user_id)
                self.load_users()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete user: {str(e)}")
