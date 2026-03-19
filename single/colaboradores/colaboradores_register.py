import requests
import json
import logging
import time
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

url = "https://api.pontomais.com.br/external_api/v1/reports/employees"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json"
}
body = {
    "report": {
        "group_by": "",
        "row_filters": "with_inactives,has_time_cards",
        "columns": "client_preference,business_unit,resignation_date,name,registration_number,job_title,team,shift,is_clt,cost_center,admission_date,group,employee_status,last_closed_date",
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

            output_path = os.path.join(BASE_DIR, "colaboradores_register.json")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)

            logging.info(f"Relatório salvo em: {output_path}")
        else:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_time = time.time() - start_time
            minutes, seconds = divmod(execution_time, 60)
            error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                           f"Arquivo: colaboradores_register.py, Hora: {error_time}, "
                           f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
            logging.error(error_message)


    except requests.exceptions.RequestException as e:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Erro ao fazer a requisição: {e} "
                        f"Arquivo: colaboradores_register.py, Hora: {error_time}, "
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