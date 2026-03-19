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
OUTPUT_FILE = os.path.join(BASE_DIR, "horaExtra09.json")

url = "https://api.pontomais.com.br/external_api/v1/reports/extra_times"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json"
}
body = {
    "report": {
        "start_date": "2025-09-01",
        "end_date": "2025-09-30",
        "group_by": "team",
        "row_filters": "",
        "columns": "employee_name,registration_number,team_name,date,time_cards,regular_time,extra_time,motive",
        "format": "json"
    }
}

def main():
    start_time = time.time()
    start_datetime = datetime.now()
    logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        response = requests.post(url, headers=headers, json=body)

        if response.status_code == 200:
            data = response.json()

            with open(OUTPUT_FILE, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)

            logging.info(f"Relatório salvo em: {OUTPUT_FILE}")
        else:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_time = time.time() - start_time
            minutes, seconds = divmod(execution_time, 60)
            error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                           f"Arquivo: horaExtra09.py, Hora: {error_time}, "
                           f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
            logging.error(error_message)

    except requests.exceptions.RequestException as e:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Erro ao fazer a requisição: {e} "
                        f"Arquivo: horaExtra09.py, Hora: {error_time}, "
                        f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
        logging.error(error_message)

    end_time = time.time()
    end_datetime = datetime.now()
    logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    execution_time = end_time - start_time
    minutes, seconds = divmod(execution_time, 60)
    logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")

if __name__ == "__main__":
    main()
