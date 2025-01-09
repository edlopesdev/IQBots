from threading import Lock
import logging

class MartingaleManager:
    def __init__(self, initial_amount, martingale_limit):
        self.lock = Lock()
        self.initial_amount = initial_amount
        self.current_amount = initial_amount
        self.martingale_limit = martingale_limit
        self.consecutive_losses = 0
        self.is_executing_trade = False  # Certifique-se de inicializar este atributo

    def execute_trade_MGM(self, asset, action, iq):
        """
        Realiza uma negociação Martingale com controle de execução simultânea.
        """
        with self.lock:
            if self.is_executing_trade:
                logging.warning("Execução de trade já em andamento. Ignorando nova tentativa.")
                return  # Ignorar se uma negociação já estiver em andamento
            self.is_executing_trade = True  # Marcar negociação como em execução

        try:
            trade_amount = self.current_amount
            logging.info(f"Executando trade: Ativo={asset}, Ação={action}, Valor={trade_amount}")

            # Tenta realizar o trade
            success, trade_id = iq.buy(trade_amount, asset, action, 5)
            if success:
                logging.info(f"Trade iniciado: ID={trade_id}")
                result = iq.check_win_v4(trade_id)  # Aguarda o resultado do trade
                if result is not None:
                    status = "win" if result > 0 else "loss"
                    self.update_on_result({"status": status, "amount": result})
            else:
                logging.warning(f"Falha ao executar trade para {asset}.")
        except Exception as e:
            logging.error(f"Erro ao executar trade para {asset}: {e}")
        finally:
            with self.lock:
                self.is_executing_trade = False  # Liberar para novas negociações

    def update_on_result(self, asset, amount):
        """
        Atualiza as informações de Martingale com base no resultado do trade.
        """
        with self.lock:
            # Exemplo de lógica de atualização
            print(f"Atualizando resultado para o ativo {asset} com valor {amount}.")
            # Lógica de Martingale, por exemplo:
            self.consecutive_losses += 1
            self.current_amount = amount * 2 if self.consecutive_losses < self.martingale_limit else self.initial_amount
            if result.get("status") == "win":
                logging.info(f"Vitória! Restaurando valor inicial: {self.initial_amount}")
                self.current_amount = self.initial_amount
                self.consecutive_losses = 0
            elif result.get("status") == "loss":
                self.consecutive_losses += 1
                if self.consecutive_losses <= self.martingale_limit:
                    self.current_amount *= 2
                    logging.warning(f"Derrota. Aplicando Martingale. Novo valor: {self.current_amount}")
                else:
                    logging.error("Limite de Martingale atingido. Resetando valores.")
                    self.current_amount = self.initial_amount
                    self.consecutive_losses = 0

print('MGM Funcionando corretamente')


# # Usando a instância
# trade_amount = martingale_manager.get_current_amount()
# print(f"Valor atual de negociação: {trade_amount}")

# # Atualizar com o resultado de um trade
# result = {"status": "loss", "amount": -2}
# martingale_manager.update_on_result(result)

# # Iniciar monitoramento em uma thread
# threading.Thread(target=martingale_manager.monitor_trades, daemon=True).start()
