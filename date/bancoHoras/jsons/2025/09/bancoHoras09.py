import requests
import json
import logging
import time
import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def salvar_json(data, nome_arquivo):
    output_file = os.path.join(BASE_DIR, nome_arquivo)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logging.info(f"Relatório salvo em: {output_file}")

url = "https://api.pontomais.com.br/external_api/v1/reports/time_balances"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "keep-alive"
}
body = {
    "report": {
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "group_by": "team",
        "row_filters": "",
        "columns": "name,registration_number,date,team_name,extra_time,missing_time,interval_time,regular_time,time_balance,time_balance_resume,department_name,overtime_missing_hours,time_balance_settled,business_unit_name",
        "format": "json"
    }
}

start_time = time.time()
start_datetime = datetime.now()
logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    with requests.Session() as session:
        max_tentativas = 5
        espera = 10
        dados = None
        for tentativa in range(1, max_tentativas + 1):
            try:
                response = session.post(url, headers=headers, json=body, timeout=(30, 300))
            except requests.exceptions.RequestException as e:
                if tentativa < max_tentativas:
                    time.sleep(espera)
                    continue
                raise e
            if response.status_code != 200:
                if tentativa < max_tentativas:
                    time.sleep(espera)
                    continue
                error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_time = time.time() - start_time
                minutes, seconds = divmod(execution_time, 60)
                error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                                 f"Arquivo: bancoHoras09.py, Hora: {error_time}, "
                                 f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
                logging.error(error_message)
                break
            try:
                dados = response.json()
            except ValueError:
                if tentativa < max_tentativas:
                    time.sleep(espera)
                    continue
                raise
            registros = 0
            try:
                bloco = dados.get("data", [])
                if isinstance(bloco, list):
                    for grupo in bloco:
                        if isinstance(grupo, list):
                            for secao in grupo:
                                if isinstance(secao, dict):
                                    tabela = secao.get("data", [])
                                    if isinstance(tabela, list):
                                        registros += len(tabela)
            except Exception:
                registros = 0
            if registros > 0:
                break
            if tentativa < max_tentativas:
                time.sleep(espera)
        if dados is not None and registros > 0:
            salvar_json(dados, "bancoHoras09.json")
            logging.info("Relatório salvo como 'bancoHoras09.json'.")

except requests.exceptions.RequestException as e:
    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execution_time = time.time() - start_time
    minutes, seconds = divmod(execution_time, 60)
    error_message = (f"Erro ao fazer a requisição: {e} "
                     f"Arquivo: bancoHoras09.py, Hora: {error_time}, "
                     f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
    logging.error(error_message)

end_time = time.time()
end_datetime = datetime.now()
logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

execution_time = end_time - start_time
minutes, seconds = divmod(execution_time, 60)
logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
