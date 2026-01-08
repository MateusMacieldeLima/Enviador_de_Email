import logging
from typing import Optional

from PySide6.QtWidgets import QDialog, QMessageBox, QListWidget, QListWidgetItem
from gui.dialogs.ui_crud import Ui_Dialog_Manage

from controller.sender_controller import SenderController

from models.sender_model import SenderModel

logger = logging.getLogger(__name__)
logger.info("[EMAIL] Iniciando configuracao de remetente...")

class ManageSendersDialog(QDialog):
    """
    Dialog for managing email senders.

    Args:
        controller (SenderController): Controller for sender operations.
        parent (QDialog, optional): Parent dialog for modal behavior.
    """

    def __init__(self, controller: SenderController, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.controller = controller

        self.ui = Ui_Dialog_Manage()
        self.ui.setupUi(self, titleText="Gerenciar Remetentes")

        self._connect()
        self.reload()

        self.selected_sender = None

    def _connect(self):
        """
        Connect UI signals to their respective slots.
        """
        self.ui.btn_add.clicked.connect(self.on_add)
        self.ui.btn_remove.clicked.connect(self.on_delete)
        self.ui.btn_select.clicked.connect(self.on_select)

    def reload(self):
        """
        Reload the list of senders in the UI.
        """

        if not hasattr(self.ui, 'list_widget'):
            self.ui.list_widget = QListWidget(self)
            self.ui.verticalLayout.addWidget(self.ui.list_widget)

        lst = self.ui.list_widget
        lst.clear()

        senders = self.controller.list_senders()

        for s in senders:
            lst.addItem(QListWidgetItem(s.address))

    def on_add(self):
        """
        Add a new sender via a dialog.
        """

        from gui.dialogs.ui_adicionar_remetente import Ui_Dialog_Adicionar_Remetente

        dlg = QDialog(self)
        dlg.ui = Ui_Dialog_Adicionar_Remetente()
        dlg.ui.setupUi(dlg)

        while True:
            result = dlg.exec_()
            if result != QDialog.DialogCode.Accepted:
                logger.debug("[CANCEL] Configuracao de remetente cancelada pelo usuario")
                QMessageBox.information(self, "Remetente", "Configuração cancelada.")
                return

            address = dlg.ui.lineEdit.text().strip()
            password = dlg.ui.lineEdit_2.text().strip()

            # Checagens básicas
            if not address:
                logger.debug("[VALIDACAO] Email vazio")
                QMessageBox.warning(self, "Email Obrigatório", "Por favor, digite um email válido.")
                continue

            if not password:
                logger.debug("[VALIDACAO] Senha vazia")
                QMessageBox.warning(self, "Senha Obrigatória", "Por favor, digite a senha de aplicativo.")
                continue

            # Adiciona na database
            try:
                sender = self.controller.add_sender(address, password)
                
                logger.info(f"[OK] Remetente configurado e salvo: {sender.address} (id={sender.sender_id})")
                QMessageBox.information(self, "Remetente", f"Remetente '{address}' adicionado com sucesso.")
            except Exception as e:
                logger.error(f"[ERRO] Falha ao adicionar remetente: {e}")
                QMessageBox.critical(self, "Erro", f"Falha ao adicionar remetente: {e}")
            
            self.reload()

            break

    def get_item_list_widget(self) -> Optional[str]:
        """
        Get the text of the selected item in the QListWidget.

        Returns:
            Optional[str]: The text of the selected item, or None if nothing selected.
        """

        lst = getattr(self.ui, 'list_widget', None)

        if not lst:
            return None

        try:
            row = lst.currentRow()
        except Exception:
            return None

        if row is None or row < 0:
            return None

        item = lst.item(row)
        if not item:
            return None

        return item.text()
    
    def get_sender_by_selected_item(self) -> Optional[SenderModel]:
        """
        Get the sender model corresponding to the selected item in the list.
        
        Returns:
            Optional[SenderModel]: The selected sender model, or None if not found.
        """
        try:
            address = self.get_item_list_widget()
            if not address:
                return None

            senders = self.controller.list_senders()
            sender = next((s for s in senders if s.address == address), None)

            return sender
        except Exception as e:
            logger.error(f"[ERRO] Falha ao obter remetente selecionado: {e}")
            return None

    def on_delete(self):
        """
        Delete the selected sender.
        """

        sender = self.get_sender_by_selected_item()

        if sender:
            try:
                self.controller.delete_sender(sender.sender_id)
                
                logger.info(f"[OK] Remetente removido: {sender.address} (id={sender.sender_id})")
                QMessageBox.information(self, "Remetente", f"Remetente '{sender.address}' removido com sucesso.")

                self.reload()
            except Exception as e:
                logger.error(f"[ERRO] Falha ao remover remetente: {e}")
                QMessageBox.critical(self, "Erro", f"Falha ao remover remetente: {e}")

    def on_select(self):
        """
        Select the highlighted sender.
        """

        sender = self.get_sender_by_selected_item()

        if not sender:
            QMessageBox.warning(self, "Remetente", "Nenhum remetente selecionado.")
            return

        try:
            self.selected_sender = sender

            logger.info(f"[OK] Remetente selecionado: {sender.address} (id={sender.sender_id})")
            QMessageBox.information(self, "Remetente", f"Remetente '{sender.address}' selecionado com sucesso.")

            self.accept()
        except Exception as e:
            logger.error(f"[SELECT] Falha ao configurar remetente: {e}")
            QMessageBox.critical(self, "Erro", f"Falha ao configurar remetente: {e}")
