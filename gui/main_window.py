import sys
import logging
import io

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, QProgressDialog,  QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from typing import Optional

from gui.dialogs.manage_senders import ManageSendersDialog
from gui.dialogs.manage_groups import ManageGroupsDialog
from gui.ui_mainwindow import Ui_MainWindow
from gui.workers.email_worker import EmailWorker

from core.email_service import EmailService

from utils.exceptions import EmailServiceError
from utils.validators import validate_required_fields
from utils.files import get_base_path, add_to_sys_path, join_paths, file_exists
from utils.fernet_crypto import generate_and_store_master_key

# Configurar logging para debug
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('email_sender_debug.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Configurar encoding para Windows

def _safe_wrap_stream(stream: Optional[io.TextIOBase]) -> io.TextIOBase:
    """
    Return a UTF-8 text wrapper for the given stream or a harmless fallback.

    In frozen GUI apps (PyInstaller) sys.stdout/sys.stderr may be None, or
    may lack a .buffer attribute. This helper avoids AttributeError by
    falling back to an in-memory StringIO when necessary.

    Args:
        stream (Optional[io.TextIOBase]): The original text stream.
    Returns:
        io.TextIOBase: A UTF-8 wrapped text stream or a StringIO fallback.
    """
    try:
        if stream is None:
            return io.StringIO()
        buf = getattr(stream, 'buffer', None)
        if buf is not None:
            return io.TextIOWrapper(buf, encoding='utf-8')
    except Exception:
        # If anything goes wrong, quietly return the original stream
        pass
    return stream


# Replace stdout/stderr with safe wrappers (no-op when not needed)
sys.stdout = _safe_wrap_stream(sys.stdout)
sys.stderr = _safe_wrap_stream(sys.stderr)

# Adicionar o diretório raiz ao path para importações
add_to_sys_path(get_base_path())
logger.debug(f"Adicionado ao sys.path: {get_base_path()}")

# Caso você tenha colado a classe Ui_MainWindow no MESMO arquivo deste código,
# mantenha a importação acima comentada e garanta que a classe Ui_MainWindow
# está definida antes desta classe MainWindow.

# ----------------------------
# Exemplo assume que Ui_MainWindow já está definido/importado
# ----------------------------

class MainWindow(QMainWindow):
    """
    Main window class for the Email Sender application.

    Args:
        parent: Optional parent widget.
    """
    def __init__(self, parent=None):
        logger.info("[INIT] Inicializando MainWindow...")
        super().__init__(parent)

        # Instancia e configura a UI gerada pelo Qt Designer
        logger.debug("[UI] Configurando interface UI...")
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        logger.debug("[OK] Interface UI configurada")

        # Serviço de email
        logger.debug("[EMAIL] Criando EmailService...")
        self.email_service = EmailService()
        logger.debug("[OK] EmailService criado")
        
        # Estado do app
        self.sender = None
        self.recipients = []
        self.attachments = []
        self.email_worker = None
        logger.debug("[OK] Estado inicial configurado")

        # Configurar placeholders
        self.ui.lineEdit.setPlaceholderText("Digite o assunto do e-mail")
        self.ui.textEdit.setPlaceholderText("Digite a mensagem do e-mail...")
        logger.debug("[OK] Placeholders configurados")

        # Conectar sinais
        self._connect_signals()
        logger.debug("[OK] Sinais conectados")
        
        # Configurar interface inicial
        self._setup_initial_ui()
        logger.info("[OK] MainWindow inicializada com sucesso")


    def _connect_signals(self):
        """
        Connect UI elements to their respective slots.
        """
        # Botões
        self.ui.pushButton.clicked.connect(self.on_informacoes_clicked)        # "Informações"
        self.ui.pushButton_2.clicked.connect(self.on_anexo_clicked)            # "Anexo"
        self.ui.pushButton_3.clicked.connect(self.on_enviar_clicked)           # "Enviar"

        # Ações de menu
        self.ui.actionRemetente.triggered.connect(self.on_manage_senders_triggered)
        self.ui.actionDestinatario.triggered.connect(self.on_manage_recipients_triggered)
    
    def _setup_initial_ui(self):
        """
        Initial UI setup.
        """
        self.setWindowTitle("Email Sender - Rio Software")
        self.statusBar().showMessage("Pronto para enviar emails")
        
        # Desabilitar botão de envio até configurar sender
        self.ui.pushButton_3.setEnabled(False)

    # ----------------------------
    # Placeholders dos botões
    # ----------------------------
    def on_informacoes_clicked(self):
        """
        Show information about generating app passwords.
        """

        info = ( """Como gerar a Senha de Aplicativo no Gmail:

     1.  Acesse sua Conta Google, 
     2.  Vá em Segurança e ative a Verificação em Duas Etapas.
     2.  Na mesma tela de Segurança, vá em "Senhas de app".
     3.  Gere uma nova senha e copie o código gerado""")

        QMessageBox.information(self, "Senha App", info)

    def on_anexo_clicked(self):
        """
        Handle adding attachments.
        """
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar arquivos para anexar")

        if files:
            self.attachments.extend(files)

            msg = f"{len(files)} anexo(s) adicionado(s). Total: {len(self.attachments)}"

            self.statusBar().showMessage(msg, 4000)
            logger.info(f"[ANEXO] {msg}")

    def on_enviar_clicked(self):
        """
        Send emails using the email service.
        """
        # Validar dados
        subject = (self.ui.lineEdit.text() or "").strip()
        body = (self.ui.textEdit.toHtml() or "").strip()
        
        # Validar campos obrigatórios
        errors = validate_required_fields(self.sender, self.recipients, subject, body)
        if errors:
            QMessageBox.warning(self, "Dados Inválidos", "\n".join(errors))
            return
        
        # Confirmar envio
        reply = QMessageBox.question(
            self, 
            "Confirmar Envio", 
            f"Enviar email para {len(self.recipients)} destinatário(s)?\n\n"
            f"Assunto: {subject}\n"
            f"Destinatários: {', '.join(self.recipients[:3])}{'...' if len(self.recipients) > 3 else ''}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Configurar serviço se necessário
        if not self.email_service.email_controller:
            try:
                self.email_service.email_controller.sender = self.sender
            except EmailServiceError as e:
                QMessageBox.critical(self, "Erro de Configuração", str(e))
                return

        # Criar diálogo de progresso com contagem por destinatário (sempre criado quando iniciar envio)
        total = len(self.recipients)
        # garantir que existe um dialogo anterior fechado
        try:
            if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
                try:
                    self.progress_dialog.close()
                except Exception:
                    pass
        except Exception:
            pass

        self.progress_dialog = QProgressDialog("Enviando emails...", "Cancelar", 0, total, self)
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setValue(0)
        self.progress_dialog.setMinimumDuration(200)
        self.progress_dialog.show()

        self.email_worker = EmailWorker(
            self.email_service.email_controller, 
            self.recipients, 
            subject, 
            body, 
            self.attachments
        )

        try:
            self.email_worker.progress.connect(lambda v: self.progress_dialog.setValue(v))

            self.progress_dialog.canceled.connect(lambda: self.email_worker.request_cancel())
        except Exception:
            logger.exception("Falha ao conectar sinais de progresso/cancelamento")

        # Conectar finalizacao
        self.email_worker.finished.connect(self.on_email_sent)
        # Desabilitar botão durante envio
        self.ui.pushButton_3.setEnabled(False)
        self.statusBar().showMessage("Enviando emails...")
        # Iniciar o worker
        self.email_worker.start()

    def on_email_sent(self, success: bool, message: str):
        """
        Callback for when email sending is finished.

        Args:
            success (bool): True if emails were sent successfully, False otherwise.
            message (str): Additional message or error details.
        """
        # Fechar diálogo de progresso se existir
        try:
            if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
                try:
                    self.progress_dialog.close()
                except Exception:
                    pass
        except Exception:
            pass

        # Reabilitar botao de enviar
        try:
            self.ui.pushButton_3.setEnabled(True)
        except Exception:
            pass

        # Mostrar mensagem de resultado
        if success:
            QMessageBox.information(self, "Sucesso", f"Emails enviados com sucesso!")
            # Atualizar barra de status com confirmacao temporaria
            try:
                self.statusBar().showMessage(f"Enviados para {len(self.recipients)} destinatários", 5000)
            except Exception:
                pass
        else:
            QMessageBox.critical(self, "Erro no Envio", f"Falha ao enviar emails:\n{message}")
            try:
                self.statusBar().showMessage("Erro no envio de emails", 5000)
            except Exception:
                pass

        # limpar referencia ao worker
        try:
            self.email_worker = None
        except Exception:
            pass

    def on_manage_senders_triggered(self):
        """
        Open the Manage Senders dialog.
        """

        dlg = ManageSendersDialog(self.email_service.sender_controller, parent=self)

        if dlg.exec_() == QDialog.DialogCode.Accepted:
            sel = getattr(dlg, 'selected_sender', None)
            
            if sel:
                self.sender = sel

                try:
                    self.email_service.setup_email_controller(self.sender)
                except Exception as e:
                    QMessageBox.critical(self, "Erro na Configuração", f"Falha ao configurar remetente:\n{e}")
                    logger.error(f"[ERROR] Failed to set up email controller: {e}")
                    self.statusBar().showMessage("Erro ao configurar remetente", 5000)
                    
                    return

                # habilitar envio se houver recipients
                if self.recipients:
                    try:
                        self.ui.pushButton_3.setEnabled(True)
                    except Exception:
                        pass
                # mostrar sender na barra de status
                try:
                    self.statusBar().showMessage(f"Remetente: {self.sender.address}")
                except Exception:
                    pass

    def on_manage_recipients_triggered(self):
        dlg = ManageGroupsDialog(
            self.email_service.recipient_controller, 
            self.email_service.group_controller, 
            parent=self
        )

        if dlg.exec_() == QDialog.DialogCode.Accepted:
            emails = getattr(dlg, 'selected_group_emails', None)
            if emails:
                self.recipients = list(emails)
                
                self.statusBar().showMessage(f"{len(self.recipients)} destinatários carregados")
                QMessageBox.information(self, "Destinatários", f"{len(self.recipients)} destinatário(s) selecionados do grupo.")
                
                if self.sender:
                    try:
                        self.ui.pushButton_3.setEnabled(True)
                    except Exception:
                        pass


def main():
    """
    Main function to run the application.
    """

    logger.info("[START] Iniciando aplicacao Email Sender...")
    print("=" * 50)
    print("INICIANDO EMAIL SENDER")
    print("=" * 50)
    
    try:
        try:
            generate_and_store_master_key("enviador_de_email")
            logger.info("[OK] Master key verificada/gerada com sucesso")
        except Exception as e:
            logger.error(f"[ERRO] Falha ao gerar/verificar master key: {e}")

        app = QApplication(sys.argv)
        logger.debug("[OK] QApplication criado")

        icon_path = join_paths(get_base_path(), "static/images/icon.ico")
        try:
            if file_exists(icon_path):
                app.setWindowIcon(QIcon(icon_path))
                logger.debug("[OK] Icone definido com sucesso")
            else:
                logger.warning("[WARN] Arquivo de icone nao encontrado")
        except Exception:
            logger.error("[ERRO] Falha ao definir icone")
        
        # Configurar aplicação
        app.setApplicationName("Email Sender")
        app.setApplicationVersion("1.0")
        app.setOrganizationName("Rio Software")
        logger.debug("[OK] Configuracoes da aplicacao definidas")
        
        # Criar e mostrar janela principal
        logger.info("[UI] Criando janela principal...")
        window = MainWindow()
        logger.info("[OK] Janela principal criada")
        
        logger.info("[UI] Exibindo janela...")
        window.show()
        logger.info("[OK] Aplicacao iniciada com sucesso!")
        print("[OK] Aplicacao iniciada com sucesso!")
        print("Email Sender esta rodando...")
        print("=" * 50)
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error(f"[ERRO] Erro fatal na inicializacao: {e}")
        print(f"[ERRO FATAL]: {e}")
        print("=" * 50)
        raise


if __name__ == "__main__":
    main()
