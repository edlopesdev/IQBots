# martingale_manager.py

import logging
import threading

class MartingaleManager:
    """
    Gerencia a lógica do Martingale, monitorando negociações em paralelo.
    """
    def __init__(self, initial_amount, martingale_limit=5):
        self.initial_amount = initial_amount
        self.current_amount = initial_amount
        self.martingale_limit = martingale_limit
        self.consecutive_losses = 0
        self.lock = threading.Lock()  # Garantir thread safety

    def update_on_result(self, result):
        """
        Atualiza os valores com base no resultado da negociação.
        :param result: Dicionário com status ("win" ou "loss") e amount do resultado.
        """
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
                    from ACapybara import execute_trades
                    execute_trades()
                else:
                    logging.error("Limite de Martingale atingido. Resetando valores.")
                    self.current_amount = self.initial_amount
                    self.consecutive_losses = 0

    def get_current_amount(self):
        """
        Retorna o valor atual de negociação.
        """
        with self.lock:
            return self.current_amount

