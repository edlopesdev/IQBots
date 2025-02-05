import re

def analyze_log(filepath):
    reasons = {
        "insufficient_consensus": 0,
        "contrary_trend": 0,
        "neutral_trend": 0,
        "low_volume": 0,
        "high_volatility": 0,
        "ignored_asset": 0,
        "no_data": 0,
        "invalid_json": 0,
        "unexpected_error": 0,
        "asset_not_found": 0,
        "trade_failed": 0,
        "market_closed": 0,
        "price_changed": 0,
        "connection_lost": 0,
        "insufficient_balance": 0,
        "trade_rejected": 0,
        "trade_timeout": 0,
        "api_error": 0,
        "unknown_error": 0,
        "network_issue": 0,
        "server_error": 0,
        "timeout_error": 0,
        "authentication_failed": 0,
        "rate_limit_exceeded": 0,
        "data_error": 0,
        "permission_denied": 0,
        "invalid_request": 0
    }

    with open(filepath, 'r') as file:
        for line in file:
            if "Pulando negociação" in line:
                if "Sem consenso ou tendência contrária" in line:
                    reasons["insufficient_consensus"] += 1
                elif "Tendência neutra" in line:
                    reasons["neutral_trend"] += 1
                elif "baixo volume" in line.lower():
                    reasons["low_volume"] += 1
                elif "alta volatilidade" in line.lower():
                    reasons["high_volatility"] += 1
                elif "Ignorando ativo" in line:
                    reasons["ignored_asset"] += 1
                elif "Sem dados suficientes" in line:
                    reasons["no_data"] += 1
                elif "Erro ao decodificar mensagem JSON" in line:
                    reasons["invalid_json"] += 1
                elif "Erro inesperado ao processar mensagem" in line:
                    reasons["unexpected_error"] += 1
                elif "Ativo não encontrado" in line:
                    reasons["asset_not_found"] += 1
                elif "Falha ao realizar negociação" in line:
                    reasons["trade_failed"] += 1
                elif "Mercado fechado" in line:
                    reasons["market_closed"] += 1
                elif "Preço mudou" in line:
                    reasons["price_changed"] += 1
                elif "Conexão perdida" in line:
                    reasons["connection_lost"] += 1
                elif "Saldo insuficiente" in line:
                    reasons["insufficient_balance"] += 1
                elif "Negociação rejeitada" in line:
                    reasons["trade_rejected"] += 1
                elif "Tempo de negociação esgotado" in line:
                    reasons["trade_timeout"] += 1
                elif "Erro na API" in line:
                    reasons["api_error"] += 1
                elif "problema de rede" in line.lower():
                    reasons["network_issue"] += 1
                elif "erro do servidor" in line.lower():
                    reasons["server_error"] += 1
                elif "tempo esgotado" in line.lower():
                    reasons["timeout_error"] += 1
                elif "falha de autenticação" in line.lower():
                    reasons["authentication_failed"] += 1
                elif "limite de taxa excedido" in line.lower():
                    reasons["rate_limit_exceeded"] += 1
                elif "erro de dados" in line.lower():
                    reasons["data_error"] += 1
                elif "permissão negada" in line.lower():
                    reasons["permission_denied"] += 1
                elif "solicitação inválida" in line.lower():
                    reasons["invalid_request"] += 1
                else:
                    reasons["unknown_error"] += 1

    print("Summary of reasons for skipping trades:")
    for reason, count in reasons.items():
        print(f"{reason}: {count}")

if __name__ == "__main__":
    log_filepath = "f:/Users/xdgee/Downloads/IQ bots/venv_name/trade_log.txt"  # Replace with the actual log file path
    analyze_log(log_filepath)
