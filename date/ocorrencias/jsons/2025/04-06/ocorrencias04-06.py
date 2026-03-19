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
OUTPUT_FILE = os.path.join(BASE_DIR, "ocorrencias04-06.json")

url = "https://api.pontomais.com.br/external_api/v1/reports/occurrences"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json"
}
body = {
    "report": {
        "start_date": "2025-04-01",
        "end_date": "2025-06-30",
        "columns": "registration_number,employee_name,date,job_title_name",
        "row_filters":"with_inactives",
        "format": "json"
    }
}

start_time = time.time()
start_datetime = datetime.now()
logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    max_tentativas = 5
    espera_segundos = 5
    data = None
    for tentativa in range(1, max_tentativas + 1):
        response = requests.post(url, headers=headers, json=body, timeout=60)
        if response.status_code != 200:
            logging.warning(f"Tentativa {tentativa}/{max_tentativas} falhou com status {response.status_code}")
            if tentativa < max_tentativas:
                time.sleep(espera_segundos)
            continue
        try:
            data = response.json()
        except ValueError:
            logging.warning(f"Tentativa {tentativa}/{max_tentativas} retornou corpo não-JSON")
            if tentativa < max_tentativas:
                time.sleep(espera_segundos)
            continue
        registros = 0
        try:
            bloco = data.get("data", [])
            if isinstance(bloco, list) and bloco:
                secao = bloco[0][0] if isinstance(bloco[0], list) and bloco[0] else None
                if isinstance(secao, dict):
                    tabela = secao.get("data", [])
                    if isinstance(tabela, list):
                        registros = len(tabela)
        except Exception:
            registros = 0
        if registros > 0:
            break
        logging.info(f"Tentativa {tentativa}/{max_tentativas} retornou 0 registros. Aguardando {espera_segundos}s e tentando novamente.")
        if tentativa < max_tentativas:
            time.sleep(espera_segundos)
    if data is None:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Falha ao obter dados após {max_tentativas} tentativas "
                         f"Arquivo: ocorrencias04-06.py, Hora: {error_time}, "
                         f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
        logging.error(error_message)
    else:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        try:
            bloco = data.get("data", [])
            secao = bloco[0][0] if isinstance(bloco, list) and bloco and isinstance(bloco[0], list) and bloco[0] else None
            tabela = secao.get("data", []) if isinstance(secao, dict) else []
            logging.info(f"Registros no relatório: {len(tabela)}")
        except Exception:
            logging.info("Registros no relatório: 0")
        logging.info(f"Relatório salvo como '{OUTPUT_FILE}'.")

except requests.exceptions.RequestException as e:
    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execution_time = time.time() - start_time
    minutes, seconds = divmod(execution_time, 60)
    error_message = (f"Erro ao fazer a requisição: {e} "
                     f"Arquivo: ocorrencias04-06.py, Hora: {error_time}, "
                     f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
    logging.error(error_message)

end_time = time.time()
end_datetime = datetime.now()
logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

execution_time = end_time - start_time
minutes, seconds = divmod(execution_time, 60)
logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")