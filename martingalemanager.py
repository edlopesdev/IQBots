# martingale_manager.py
import logging
import threading
import time

class MartingaleManager:
    """
    Gerencia a lógica do Martingale, monitorando negociações em paralelo.
    """
    def __init__(self, initial_amount, martingale_limit=5, api=None):
        self.initial_amount = initial_amount
        self.current_amount = initial_amount
        self.martingale_limit = martingale_limit
        self.consecutive_losses = 0
        self.lock = threading.Lock()  # Garantir thread safety
        self.api = api  # Instância da API
        self.running = True  # Controle de execução da thread

        # Inicia a thread de monitoramento contínuo
        threading.Thread(target=self.monitor_trades, daemon=True).start()

    def update_on_result(self, result):
        """
        Atualiza os valores com base no resultado da negociação.
        :param result: Dicionário com status ("win" ou "loss") e amount do resultado.
        """
        print(result)
        with self.lock:
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

    def get_current_amount(self):
        """
        Retorna o valor atual de negociação.
        """
        print(self.current_amount)
        with self.lock:
            return self.current_amount

    def monitor_trades(self):
        """
        Monitora continuamente os trades abertos e atualiza os resultados a cada 10 segundos.
        """
        while self.running:
            print("Executando monitoramento paralelo.")
            try:
                logging.info("Verificando trades abertos...")
                open_trades = self.api.get_open_positions() if self.api else []

                for trade in open_trades:
                    trade_id = trade["id"]
                    result = self.api.check_win_v3(trade_id) if self.api else None

                    if result is not None:
                        logging.info(f"Resultado do trade {trade_id}: {result}")
                        self.update_on_result(result)

                logging.info("Monitoramento de trades concluído. Aguardando 10 segundos...")
            except Exception as e:
                logging.error(f"Erro ao monitorar trades: {e}")

            time.sleep(10)  # Aguarda 10 segundos antes de verificar novamente

    def stop(self):
        """
        Para o monitoramento contínuo.
        """
        self.running = False
