import sys
import json
import os
import logging  # <-- Importação do logging
import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLineEdit,
    QComboBox, QPushButton, QLabel, QMessageBox, QSpacerItem, QSizePolicy
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

# Definição do nome do arquivo de configuração e estilo
CONFIG_FILE = "config.json"
STYLE_FILE = "style.qss"
# URL da API de cotação (exemplo para AwesomeAPI)
API_URL_TEMPLATE = "https://economia.awesomeapi.com.br/json/last/{origem}-{destino}"


class ConversorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conversor de Moedas")
        self.resize(500, 300)

        # 1. Configuração da Interface
        self._setup_ui()

        # 2. Carregar a configuração inicial (moedas salvas)
        self.carregar_config()

        # 3. Conectar o botão
        self.btn_converter.clicked.connect(self.converter_moeda)

        # LOG: Aplicação iniciada
        logging.info("Aplicação Conversor de Moedas Iniciada.")

    def _setup_ui(self):
        """Define e organiza todos os widgets da interface e aplica os IDs para o QSS."""

        # Estrutura Central e Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # --- Rótulos de Cabeçalho ---
        lbl_titulo = QLabel("Conversor de Moedas Global")
        lbl_titulo.setObjectName("HeaderLabel")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(lbl_titulo)

        # --- Input de Valor ---
        self.input_valor = QLineEdit()
        self.input_valor.setPlaceholderText("Insira o valor a ser convertido")
        main_layout.addWidget(self.input_valor)

        # --- Comboboxes de Moeda ---
        self.combo_origem = QComboBox()
        self.combo_destino = QComboBox()

        # Moedas disponíveis
        moedas = ["USD", "BRL", "EUR", "JPY", "ARS", "CAD", "AUD", "GBP", "CHF"]
        self.combo_origem.addItems(moedas)
        self.combo_destino.addItems(moedas)

        # Layout Horizontal para Comboboxes
        combo_layout = QHBoxLayout()
        combo_layout.addWidget(self.combo_origem)

        label_para = QLabel("→")
        label_para.setAlignment(Qt.AlignCenter)
        label_para.setObjectName("QLabel")
        combo_layout.addWidget(label_para)

        combo_layout.addWidget(self.combo_destino)
        main_layout.addLayout(combo_layout)

        # --- Botão Converter ---
        self.btn_converter = QPushButton("CONVERTER")
        self.btn_converter.setCursor(Qt.PointingHandCursor)
        self.btn_converter.setObjectName("QPushButton")
        main_layout.addWidget(self.btn_converter)

        # --- Resultado e Rodapé ---
        self.lbl_resultado = QLabel("0,00")
        self.lbl_resultado.setObjectName("ResultadoDisplay")
        self.lbl_resultado.setAlignment(Qt.AlignCenter)

        self.lbl_data_cotacao = QLabel("Fonte: AwesomeAPI | Última Cotação: -")
        self.lbl_data_cotacao.setObjectName("FooterLabel")
        self.lbl_data_cotacao.setAlignment(Qt.AlignCenter)

        # Adiciona ao Layout Principal
        main_layout.addWidget(self.lbl_resultado)
        main_layout.addStretch()
        main_layout.addWidget(self.lbl_data_cotacao)

    # =================================================================
    # FUNÇÕES DE CONFIGURAÇÃO (config.json)
    # =================================================================

    def carregar_config(self):
        """
        Carrega as configurações de moeda inicial do arquivo config.json.
        """
        if not os.path.exists(CONFIG_FILE):
            # LOG: Arquivo de config não encontrado
            logging.warning(f"Arquivo '{CONFIG_FILE}' não encontrado. Usando padrões: USD e BRL.")
            return

        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)

            origem = config.get("origem")
            destino = config.get("destino")

            if origem:
                index_origem = self.combo_origem.findText(origem)
                if index_origem >= 0:
                    self.combo_origem.setCurrentIndex(index_origem)

            if destino:
                index_destino = self.combo_destino.findText(destino)
                if index_destino >= 0:
                    self.combo_destino.setCurrentIndex(index_destino)

            # LOG: Configurações carregadas
            logging.info("Configurações carregadas com sucesso.")

        except Exception as e:
            # LOG: Falha ao carregar configurações
            logging.error(f"Falha ao carregar configurações: {e}")

    def closeEvent(self, event):
        """
        Salva as configurações atuais de moeda antes de fechar a janela.
        """

        config_atual = {
            "origem": self.combo_origem.currentText(),
            "destino": self.combo_destino.currentText()
        }

        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config_atual, f, indent=4)

                # LOG: Configurações salvas
            logging.info("Configurações salvas com sucesso ao fechar.")

        except Exception as e:
            # LOG: Erro ao salvar configurações
            logging.error(f"Erro ao salvar configurações: {e}")

        event.accept()

    # =================================================================
    # FUNÇÕES DE CONVERSÃO E API (Correção do erro de par)
    # =================================================================

    def _obter_cotacao(self, origem, destino):
        """
        Faz a requisição na API, tentando a ordem direta e, em caso de falha,
        a ordem inversa (solução para o erro de API).
        Retorna (cotacao, data, par_usado) ou lança exceção.
        """

        par_direto_chave = f"{origem}{destino}"
        url_direta = API_URL_TEMPLATE.format(origem=origem, destino=destino)

        par_inverso_chave = f"{destino}{origem}"
        url_inversa = API_URL_TEMPLATE.format(origem=destino, destino=origem)

        try:
            # 1. Tenta a Cotação Direta
            resposta = requests.get(url_direta, timeout=10)
            resposta.raise_for_status()
            dados = resposta.json()

            if par_direto_chave in dados:
                dados_moeda = dados[par_direto_chave]
                cotacao_bid = float(dados_moeda["bid"])
                data_api = dados_moeda["create_date"]
                return cotacao_bid, data_api, par_direto_chave

        except Exception as e:
            # LOG: Falha na cotação direta
            logging.warning(
                f"Falha na cotação direta ({par_direto_chave}). Tentando inversa ({par_inverso_chave}). Detalhe: {e}")

            try:
                # 2. Tenta a Cotação Inversa
                resposta = requests.get(url_inversa, timeout=10)
                resposta.raise_for_status()
                dados = resposta.json()

                if par_inverso_chave in dados:
                    dados_moeda = dados[par_inverso_chave]
                    cotacao_bid = 1 / float(dados_moeda["bid"])
                    data_api = dados_moeda["create_date"]
                    return cotacao_bid, data_api, par_inverso_chave

            except Exception:
                # Se ambas falharam, o erro será tratado abaixo
                pass

        # Se saiu dos try/except sem sucesso, lança erro.
        raise ValueError(
            f"O par de moedas {origem}-{destino} e o par inverso não foram encontrados ou a API está indisponível.")

    def converter_moeda(self):
        """
        Implementa a lógica principal de conversão de moeda.
        """
        moeda_origem = self.combo_origem.currentText()
        moeda_destino = self.combo_destino.currentText()
        valor_texto = self.input_valor.text().replace(',', '.')

        # LOG: Iniciando a conversão
        logging.info(f"Iniciando conversão de {valor_texto} {moeda_origem} para {moeda_destino}.")

        if moeda_origem == moeda_destino:
            QMessageBox.warning(self, "Aviso", "As moedas de origem e destino não podem ser as mesmas.")
            return

        try:
            # 1. Validação do Valor
            if not valor_texto:
                QMessageBox.warning(self, "Aviso", "Por favor, insira um valor.")
                return

            valor = float(valor_texto)
            if valor <= 0:
                QMessageBox.warning(self, "Aviso", "O valor deve ser maior que zero.")
                return

            # 2. Obter Cotação da API (com fallback)
            cotacao, data_cotacao_str, par_usado = self._obter_cotacao(moeda_origem, moeda_destino)

            # 3. Calcular Resultado
            resultado = valor * cotacao

            # 4. Formatação e Exibição
            texto_resultado = f"{resultado:,.2f}"
            texto_resultado = texto_resultado.replace(",", "_").replace(".", ",").replace("_", ".")  # Inverte . e ,

            self.lbl_resultado.setText(texto_resultado)

            self.lbl_data_cotacao.setText(
                f"Fonte: AwesomeAPI | Par Usado: {par_usado} | Última Cotação: {data_cotacao_str}")

            # LOG: Conversão concluída com sucesso
            logging.info(f"Conversão concluída. Resultado: {resultado:.2f} {moeda_destino} (Cotação: {cotacao:.4f}).")

        except ValueError as ve:
            # LOG: Erro de API/Validação
            logging.error(f"Erro de API/Validação (ValueError): {ve}")
            QMessageBox.critical(self, "Erro de API", f"Valor inválido ou erro de cotação. Detalhe: {ve}")
        except requests.exceptions.RequestException as re:
            # LOG: Erro de Conexão
            logging.error(f"Falha de Conexão (RequestException): {re}")
            QMessageBox.critical(self, "Erro de Conexão",
                                 f"Falha ao conectar na API. Verifique sua internet. Detalhe: {re}")
        except Exception as e:
            # LOG: Erro Desconhecido
            logging.critical(f"Erro Desconhecido: {e}")
            QMessageBox.critical(self, "Erro Desconhecido", f"Ocorreu um erro inesperado: {e}")


# Bloco de execução principal da aplicação
if __name__ == "__main__":
    # CONFIGURAÇÃO DE LOGGING: Escreve no arquivo 'conversor.log'
    logging.basicConfig(filename='conversor.log',
                        level=logging.INFO,  # Nível de logging
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        encoding='utf-8')

    app = QApplication(sys.argv)

    font = QFont("Inter", 10)
    app.setFont(font)

    # CARREGA O STYLE.QSS
    try:
        with open(STYLE_FILE, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        logging.info(f"Estilo '{STYLE_FILE}' carregado com sucesso.")
    except FileNotFoundError:
        logging.error(f"Arquivo de estilo '{STYLE_FILE}' não encontrado. A interface não será estilizada.")
    except Exception as e:
        logging.error(f"Erro ao carregar o estilo: {e}")

    window = ConversorApp()
    window.show()

    sys.exit(app.exec())
