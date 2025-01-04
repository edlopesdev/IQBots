import pyautogui
import time
import os

def abrir_programa_e_executar():
    # Encontre e abra o programa através do atalho no desktop
    programa_path = r'C:\\Users\\xdgee\\OneDrive\\Área de Trabalho\\Capybara.lnk'  # Caminho correto para o ícone
    os.startfile(programa_path)
    
    # Aguarda o programa abrir (ajuste se necessário)
    time.sleep(5)

    # Pressiona "Tab" e "Espaço"
    pyautogui.press('tab')
    time.sleep(1)
    pyautogui.press('space')  # Posiciona e pressiona

    # Aguarde 5 minutos (310 segundos)
    time.sleep(310)

    # Fechar a janela ativa
    pyautogui.hotkey('alt', 'f4')
    time.sleep(1)
    pyautogui.hotkey('alt', 'f4')

# Executar em loop infinito
while True:
    abrir_programa_e_executar()
