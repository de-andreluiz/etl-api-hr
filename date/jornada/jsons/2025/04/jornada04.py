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

url = "https://api.pontomais.com.br/external_api/v1/reports/work_days"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}
body = {
    "report": {
        "start_date": "2025-04-01",
        "end_date": "2025-04-30",
        "group_by": "employee",
        "row_filters": "with_inactives,has_time_cards",
        "columns": "date,shift_name,shift_appointments,summary,extra_time,total_time,shift_time,overnight_time,daylight_extra_time,team_name,managers_names,registration_number,time_balance,motive,has_time_cards",
        "format": "json"
    }
}


def main():
    start_time = time.time()
    start_datetime = datetime.now()
    logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        with requests.Session() as session:
            response = session.post(url, headers=headers, json=body)

            if response.status_code == 200:
                data = response.json()

                output_path = os.path.join(BASE_DIR, "jornada04.json")
                with open(output_path, "w", encoding="utf-8") as json_file:
                    json.dump(data, json_file, ensure_ascii=False, indent=4)

                logging.info("Relatório salvo como 'jornada04.json'.")
            else:
                error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                execution_time = time.time() - start_time
                minutes, seconds = divmod(execution_time, 60)
                error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                                 f"Arquivo: jornada04.py, Hora: {error_time}, "
                                 f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
                logging.error(error_message)


    except requests.exceptions.RequestException as e:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Erro ao fazer a requisição: {e} "
                         f"Arquivo: jornada04.py, Hora: {error_time}, "
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