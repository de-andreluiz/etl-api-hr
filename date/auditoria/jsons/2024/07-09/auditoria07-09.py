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
        "start_date": "2024-07-01",
        "end_date": "2024-09-30",
        "group_by": "",
        "additional_row_filters": "",
        "row_filters": "consecutives_work_days,more_then_ten_hours,less_then_one_hour,missing_work_days,missing_time,missing_rest_time,more_then_two_extra,missing_interval_time",
        "columns": "name,date,occurrence,value,worked_hours",
        "format": "json"
    }
}

def send_telegram_message(message):
    telegram_url = "https://api.telegram.org/bot<SEU_TOKEN_TELEGRAM>/sendmessage"
    params = {
        "chat_id": "7902541123",
        "text": message
    }
    try:
        response = requests.get(telegram_url, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao enviar mensagem para o Telegram: {e}")

start_time = time.time()
start_datetime = datetime.now()
logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    with requests.Session() as session:
        response = session.post(url, headers=headers, json=body)

        if response.status_code == 200:
            data = response.json()

            script_dir = os.path.dirname(os.path.abspath(__file__))
            output_path = os.path.join(script_dir, "auditoria07-09.json")
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(data, json_file, ensure_ascii=False, indent=4)

            logging.info("Relatório salvo como 'auditoria07-09.json'.")
        else:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_time = time.time() - start_time
            minutes, seconds = divmod(execution_time, 60)
            error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                             f"Arquivo: auditoria07-09.py, Hora: {error_time}, "
                             f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
            logging.error(error_message)
            send_telegram_message(f"Erro no processo de registro de auditoria: {error_message}")

except requests.exceptions.RequestException as e:
    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execution_time = time.time() - start_time
    minutes, seconds = divmod(execution_time, 60)
    error_message = (f"Erro ao fazer a requisição: {e} "
                     f"Arquivo: auditoria07-09.py, Hora: {error_time}, "
                     f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
    logging.error(error_message)
    send_telegram_message(f"Erro no processo de registro de auditoria: {error_message}")

end_time = time.time()
end_datetime = datetime.now()
logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

execution_time = end_time - start_time
minutes, seconds = divmod(execution_time, 60)
logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")