import logging
import re

from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox, QListWidget, QListWidgetItem, QInputDialog, QFileDialog
from gui.dialogs.ui_crud import Ui_Dialog_Manage

from controller.recipient_controller import RecipientController
from controller.recipient_group_controller import RecipientGroupController

from models.recipient_group_model import RecipientGroupModel

logger = logging.getLogger(__name__)
logger.info("[EMAIL] Iniciando configuracao de destinatarios...")

class ManageGroupsDialog(QDialog):
    """
    Dialog for managing recipient groups.
    
    Args:
        recipient_controller (RecipientController): Controller for recipient operations.
        group_controller (RecipientGroupController): Controller for recipient group operations.
        parent (QDialog, optional): Parent dialog for modal behavior.
    """
    
    def __init__(self, recipient_controller: RecipientController, group_controller: RecipientGroupController, parent=None):
        super().__init__(parent)
        self.recipient_controller = recipient_controller
        self.group_controller = group_controller

        self.ui = Ui_Dialog_Manage()
        self.ui.setupUi(self, titleText="Gerenciar Grupos de Destinatários")
        
        self._connect()
        self.reload()

        self.selected_group = None

    def _connect(self):
        """
        Connect UI signals to their respective slots.
        """
        try:
            self.ui.btn_add.clicked.connect(self.on_add_group)
            self.ui.btn_remove.clicked.connect(self.on_delete_group)
            self.ui.btn_select.clicked.connect(self.on_select_group)
        except Exception as e:
            logger.error(f"[ERRO] Falha ao conectar sinais do UI: {e}")

    def reload(self):
        """
        Reload the list of senders in the UI.
        """
        try:
            lst = self.ui.list_widget
            lst.clear()

            groups = self.group_controller.list_groups()

            for g in groups:
                # try to get member ids from membership DAO for debugging
                try:
                    member_ids = []
                    if hasattr(self.group_controller, 'membership_dao'):
                        try:
                            member_ids = self.group_controller.membership_dao.list_group_members(g.group_id)
                        except Exception:
                            member_ids = []
                    # fallback to deriving from recipients if membership table empty
                    members = self.group_controller.list_group_recipients(g.group_id)
                    count = len(members)
                    logger.debug(f"[GROUP] {g.name} (id={g.group_id}) membership_ids={member_ids} resolved_count={count}")
                except Exception as e:
                    logger.error(f"[ERRO] Falha ao obter membros para grupo {g.name}: {e}")
                    count = 0

                item = QListWidgetItem(f"{g.name} - {count} destinatários")
                lst.addItem(item)
        except Exception as e:
            logger.error(f"[ERRO] Falha ao recarregar lista de grupos: {e}")
            QMessageBox.critical(self, "Erro", "Falha ao recarregar lista de grupos.")
    def on_add_group(self):
        """
        Add a new recipient group and import recipients from a file.
        """

        try:
            name, ok = QInputDialog.getText(self, "Adicionar Grupo", "Nome do grupo:")

            if ok and name:
                group = self.group_controller.add_group(name)
                
                path, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo", filter="Arquivos suportados (*.csv *.xlsx *.xls)")
                if path:
                    addresses = self.recipient_controller.process_recipient_file(path)

                    added = 0
                    failed = 0
                    for a in addresses:
                        try:
                            # add_recipient already associates the recipient with the group when group_id is passed,
                            # so avoid duplicating the association call which can cause conflicts.
                            rec = self.recipient_controller.add_recipient(a, group_id=group.group_id)
                            if rec:
                                added += 1
                        except Exception as ex:
                            failed += 1
                            logger.warning(f"[WARN] Falha ao adicionar email {a}: {ex}")

                    logger.info(f"[IMPORT] Import finished: {added} added, {failed} failed, {len(addresses)} total")
                
                self.reload()
        except Exception as e:
            logger.error(f"[ERRO] Falha ao adicionar grupo: {e}")
            QMessageBox.critical(self, "Erro", "Falha ao adicionar grupo.")

    def get_item_list_widget(self) -> QListWidget:
        """
        Get the QListWidget containing the senders.

        Returns:
            QListWidget: The list widget with senders.
        """

        try:
            lst = getattr(self.ui, 'list_widget', None)

            if not lst:
                return
            
            row = lst.currentRow()
            if row < 0:
                return

            return lst.item(row).text()
        except Exception as e:
            logger.error(f"[ERRO] Falha ao obter item selecionado: {e}")
            return None
    
    def get_group_by_selected_item(self) -> Optional[RecipientGroupModel]:
        """
        Get the recipient group corresponding to the selected item in the list widget.
        """

        try:
            regex = r"^(.*) - \d+ destinatários$"

            group_name = self.get_item_list_widget()
            match = re.match(regex, group_name) if group_name else None

            if match:
                group_name = match.group(1)
            else:
                group_name = None

            grp = next((g for g in self.group_controller.list_groups() if g.name == group_name), None)
            
            return grp
        except Exception as e:
            logger.error(f"[ERRO] Falha ao obter grupo selecionado: {e}")
            return None

    def on_delete_group(self):
        """
        Delete the selected recipient group.
        """
        
        try:
            group = self.get_group_by_selected_item()

            if group:
                self.group_controller.delete_group(group.group_id)
                self.reload()
        except Exception as e:
            logger.error(f"[ERRO] Falha ao deletar grupo: {e}")
            QMessageBox.critical(self, "Erro", "Falha ao deletar grupo.")

    def on_select_group(self):
        """
        Select the recipient group and store its members' emails.
        """

        try:
            group = self.get_group_by_selected_item()
            
            if group:
                members = self.group_controller.list_group_recipients(group.group_id)
                emails = [m.address for m in members]
                logger.debug(f"[SELECT_GROUP] Selected group {group.name} (id={group.group_id}) members_count={len(members)} emails_sample={emails[:5]}")
                self.selected_group_emails = emails
                self.selected_group = group.name
                self.accept()
        except Exception as e:
            logger.error(f"[ERRO] Falha ao selecionar grupo: {e}")
            QMessageBox.critical(self, "Erro", "Falha ao selecionar grupo.")
