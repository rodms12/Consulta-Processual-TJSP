import os
import sys
import pandas as pd
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options

def pesquisa_andamento_tj(num_unico_processo):
    options = Options()
    options.headless = True  

    driver = webdriver.Firefox(options=options, service=Service(GeckoDriverManager().install()))

    try:
        url_pesquisa = 'https://esaj.tjsp.jus.br/cpopg/open.do'
        driver.get(url_pesquisa)

        campo_numero_unico = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="numeroDigitoAnoUnificado"]'))
        )
        campo_numero_unico.send_keys(num_unico_processo)
        btn_consulta = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="botaoConsultarProcessos"]'))
        )
        btn_consulta.click()

        # Verificar se o processo está em segredo de justiça
        try:
            mensagem_segredo_justica = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="mensagemRetorno"]'))
            )
            if "Segredo de Justiça" in mensagem_segredo_justica.text:
                return None, None, None
        except:
            pass  # Se não encontrar a mensagem, continua normalmente

        elementos_requeridos = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="containerDadosPrincipaisProcesso"]/div[2]'))
        )
        elementos_outros = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="tablePartesPrincipais"]/tbody'))
        )
        elementos_mais = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="tabelaUltimasMovimentacoes"]/tr[1]'))
        )

        texto_elementos_requeridos = elementos_requeridos.text.replace('\n', '  ')
        texto_elementos_outros = elementos_outros.text.replace('\n', '  ')
        texto_elementos_mais = elementos_mais.text.replace('\n', '  ')

        # Garantir que os detalhes estão completos
        detalhes_processos = texto_elementos_requeridos.split('  ')
        if len(detalhes_processos) < 10:
            raise ValueError("Detalhes do processo incompletos")

        detalhes_formatados = (
            f"Classe: {detalhes_processos[1]}\n"
            f"Assunto: {detalhes_processos[3]}\n"
            f"Foro: {detalhes_processos[5]}\n" 
            f"Vara: {detalhes_processos[7]}\n"
            f"Juiz: {detalhes_processos[9]}\n"
        )

        # Formatar as partes envolvidas
        partes_formatadas = "\nPartes Envolvidas:\n"
        linhas = texto_elementos_outros.split('  ')
        for i in range(0, len(linhas)):
            if "Reqte" in linhas[i]:
                partes_formatadas += f"Reqte: {linhas[i+1]}\n"
                if i+3 < len(linhas) and "Advogado" in linhas[i+2]:
                    partes_formatadas += f"Advogado Reqte: {linhas[i+3]}\n"
            elif "Reqdo" in linhas[i]:
                partes_formatadas += f"Reqdo: {linhas[i+1]}\n"
                if i+3 < len(linhas) and "Advogado" in linhas[i+2]:
                    partes_formatadas += f"Advogado Reqdo: {linhas[i+3]}\n"

        # Verificar se há pelo menos uma movimentação
        movimentacoes = []
        for i in range(1, 4):
            try:
                elemento_mov = driver.find_element(By.XPATH, f'//*[@id="tabelaUltimasMovimentacoes"]/tr[{i}]')
                movimentacoes.append(elemento_mov.text.replace('\n', '  '))
            except:
                movimentacoes.append("Movimentação não encontrada")

        return detalhes_formatados, partes_formatadas, movimentacoes
    
    except Exception as e:
        # Se ocorrer qualquer erro, simplesmente retornar None para todos os valores
        return None, None, None

    finally:
        driver.quit()

def carregar_dados_excel(nome_arquivo_excel):
    if getattr(sys, 'frozen', False):
        diretorio_atual = os.path.dirname(sys.executable)
    else:
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))

    caminho_arquivo_excel = os.path.join(diretorio_atual, nome_arquivo_excel)

    if not os.path.exists(caminho_arquivo_excel):
        print(f"Erro: O arquivo {caminho_arquivo_excel} não foi encontrado.")
        return None

    try:
        df = pd.read_excel(caminho_arquivo_excel)
        return df
    except Exception as e:
        print(f"Ocorreu um erro ao tentar carregar o arquivo Excel: {e}")
        return None

nome_arquivo_excel = "PYTHONPANDAS.xlsx"

df = carregar_dados_excel(nome_arquivo_excel)

if df is not None:
    for num_unico_processo in df['Numero do Processo']:
        print('Ok, por favor aguarde um momento...')
        detalhes, partes, movimentacoes = pesquisa_andamento_tj(str(num_unico_processo))

        if detalhes is None and partes is None and movimentacoes is None:
            print(f"O processo {num_unico_processo} está em segredo de justiça. Pulando para o próximo processo.")
            continue

        if detalhes:
            print('Aqui está o seu resultado:')
            print(f"Detalhes do Processo:\n{detalhes}")
            print(f"{partes}\n")
            for i, mov in enumerate(movimentacoes, 1):
                print(f"Movimentação {i}: {mov}\n")
        else:
            print(f"Não foi possível obter o resultado para o processo: {num_unico_processo}")

        resposta = input("Deseja continuar para o próximo processo? (s/n): ")
        if resposta.lower() != 's':
            break

