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
    "Accept-Encoding": "gzip"
}
body = {
    "report": {
        "start_date": "2026-12-01",
        "end_date": "2026-12-31",
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
    response = requests.post(url, headers=headers, json=body)

    if response.status_code == 200:
        data = response.json()
        salvar_json(data, "bancoHoras12.json")
        logging.info("Relatório salvo como 'bancoHoras12.json'.")
    else:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                         f"Arquivo: bancoHoras12.py, Hora: {error_time}, "
                         f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
        logging.error(error_message)

except requests.exceptions.RequestException as e:
    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execution_time = time.time() - start_time
    minutes, seconds = divmod(execution_time, 60)
    error_message = (f"Erro ao fazer a requisição: {e} "
                     f"Arquivo: bancoHoras12.py, Hora: {error_time}, "
                     f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
    logging.error(error_message)

end_time = time.time()
end_datetime = datetime.now()
logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

execution_time = end_time - start_time
minutes, seconds = divmod(execution_time, 60)
logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
