import requests
import json
import logging
import time
import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

url = f"{os.environ['HR_API_BASE_URL'].rstrip('/')}/external_api/v1/reports/audit"
headers = {
    "access-token": os.getenv("HR_API_ACCESS_TOKEN"),
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}
body = {
    "report": {
        "start_date": "2025-04-01",
        "end_date": "2025-06-30",
        "group_by": "",
        "additional_row_filters": "",
        "row_filters": "consecutives_work_days,more_then_ten_hours,less_then_one_hour,missing_work_days,missing_time,missing_rest_time,more_then_two_extra,missing_interval_time",
        "columns": "name,date,occurrence,value,worked_hours",
        "format": "json"
    }
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "auditoria04-06.json")

def main():
    start_time = time.time()
    start_datetime = datetime.now()
    logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        with requests.Session() as session:
            response = session.post(url, headers=headers, json=body)

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
                               f"Arquivo: auditoria04-06.py, Hora: {error_time}, "
                               f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
                logging.error(error_message)

    except requests.exceptions.RequestException as e:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Erro ao fazer a requisição: {e} "
                        f"Arquivo: auditoria04-06.py, Hora: {error_time}, "
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