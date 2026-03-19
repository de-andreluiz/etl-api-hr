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
OUTPUT_FILE = os.path.join(BASE_DIR, "ponto09.json")

url = "https://api.pontomais.com.br/external_api/v1/reports/time_cards"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}
body = {
    "report": {
        "start_date": "2026-09-01",
        "end_date": "2026-09-30",
        "group_by": "team",
        "row_filters": "",
        "columns": "employee_name,registration_number,team_name,shift_name,date,time,source,edited_address,manually_changed,motive,updated_by,time_card_index,software_method",
        "format": "json"
    }
}

def main():
    start_time = time.time()
    start_datetime = datetime.now()
    logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    success = False
    while not success:
        try:
            response = requests.post(url, headers=headers, json=body)

            if response.status_code == 200:
                data = response.json()

                with open(OUTPUT_FILE, "w", encoding="utf-8") as json_file:
                    json.dump(data, json_file, ensure_ascii=False, indent=4)

                logging.info(f"Relatório salvo como '{OUTPUT_FILE}'.")
                success = True
            else:
                error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                                 f"Arquivo: ponto09.py, Hora: {error_time}")
                logging.error(error_message)
                time.sleep(3)

        except requests.exceptions.RequestException as e:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            error_message = (f"Erro ao fazer a requisição: {e} "
                             f"Arquivo: ponto09.py, Hora: {error_time}")
            logging.error(error_message)
            time.sleep(3)

    end_time = time.time()
    end_datetime = datetime.now()
    logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    execution_time = end_time - start_time
    minutes, seconds = divmod(execution_time, 60)
    logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")

if __name__ == "__main__":
    main()