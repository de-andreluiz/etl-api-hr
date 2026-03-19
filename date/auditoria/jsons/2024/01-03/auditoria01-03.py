import requests
import json
import logging
import time
import os
from dotenv import load_dotenv

load_dotenv()

from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

url = "https://api.pontomais.com.br/external_api/v1/reports/audit"
headers = {
    "access-token": os.getenv("PONTOMAIS_ACCESS_TOKEN"),
    "Content-Type": "application/json"
}
body = {
    "report": {
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
        "group_by": "",
        "additional_row_filters": "",
        "row_filters": "consecutives_work_days,more_then_ten_hours,less_then_one_hour,missing_work_days,missing_time,missing_rest_time,more_then_two_extra,missing_interval_time",
        "columns": "name,date,occurrence,value,worked_hours",
        "format": "json"
    }
}

start_time = time.time()
start_datetime = datetime.now()
logging.info(f"Início da execução: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

try:
    logging.info("Iniciando sessão de requisição HTTP...")
    with requests.Session() as session:
        tempo_antes_post = time.time() - start_time
        logging.info(f"Tempo decorrido antes do POST: {tempo_antes_post:.2f} segundos.")
        logging.info(f"Enviando POST para {url} com headers e body definidos.")
        response = session.post(url, headers=headers, json=body)
        tempo_apos_post = time.time() - start_time
        logging.info(f"Resposta recebida após {tempo_apos_post:.2f} segundos. Status code: {response.status_code}")
        content_encoding = response.headers.get('Content-Encoding')
        if content_encoding == 'gzip':
            logging.info("A resposta veio comprimida com gzip!")
        else:
            logging.info(f"Content-Encoding: {content_encoding} (não é gzip ou não veio definido)")
        data = response.json()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "auditoria01-03.json")
        tempo_antes_salvar = time.time() - start_time
        logging.info(f"Salvando arquivo JSON em: {output_path} (tempo decorrido: {tempo_antes_salvar:.2f} segundos)")
        with open(output_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)

        tempo_apos_salvar = time.time() - start_time
        logging.info(f"Relatório salvo como 'auditoria01-03.json'. Tempo total até aqui: {tempo_apos_salvar:.2f} segundos.")
        if response.status_code == 200:
            logging.info("Resposta 200 OK. Decodificando JSON...")

        else:
            error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            execution_time = time.time() - start_time
            minutes, seconds = divmod(execution_time, 60)
            error_message = (f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                             f"Arquivo: auditoria01-03.py, Hora: {error_time}, "
                             f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
            logging.error(error_message)
            logging.error(f"Conteúdo da resposta da API: {response.text}")

except requests.exceptions.RequestException as e:
    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execution_time = time.time() - start_time
    minutes, seconds = divmod(execution_time, 60)
    error_message = (f"Erro ao fazer a requisição: {e} "
                     f"Arquivo: auditoria01-03.py, Hora: {error_time}, "
                     f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")
    logging.error(error_message)
    logging.error("Exceção capturada durante a requisição HTTP.")

end_time = time.time()
end_datetime = datetime.now()
logging.info(f"Término da execução: {end_datetime.strftime('%Y-%m-%d %H:%M:%S')}")

execution_time = end_time - start_time
minutes, seconds = divmod(execution_time, 60)
logging.info(f"Tempo total de execução: {int(minutes)} minutos e {seconds:.2f} segundos.")