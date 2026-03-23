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

url = f"{os.environ['HR_API_BASE_URL'].rstrip('/')}/external_api/v1/reports/work_days"
headers = {
    "access-token": os.getenv("HR_API_ACCESS_TOKEN"),
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
    "Connection": "keep-alive"
}
body = {
    "report": {
        "start_date": "2024-07-01",
        "end_date": "2024-09-30",
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
            tentativas_max = 5
            espera = 10
            dados = None
            for tentativa in range(1, tentativas_max + 1):
                try:
                    response = session.post(url, headers=headers, json=body, timeout=(30, 300))
                except requests.exceptions.RequestException as e:
                    if tentativa < tentativas_max:
                        time.sleep(espera)
                        continue
                    raise e
                if response.status_code != 200:
                    if response.status_code == 404:
                        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        execution_time = time.time() - start_time
                        minutes, seconds = divmod(execution_time, 60)
                        logging.error((f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                                       f"Arquivo: jornada07-09.py, Hora: {error_time}, "
                                       f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos."))
                        return
                    if tentativa < tentativas_max:
                        time.sleep(espera)
                        continue
                    error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    execution_time = time.time() - start_time
                    minutes, seconds = divmod(execution_time, 60)
                    logging.error((f"Erro na requisição: {response.status_code}. Detalhes: {response.text} "
                                   f"Arquivo: jornada07-09.py, Hora: {error_time}, "
                                   f"Tempo de execução: {int(minutes)} minutos e {seconds:.2f} segundos."))
                    return
                try:
                    dados = response.json()
                except ValueError:
                    if tentativa < tentativas_max:
                        time.sleep(espera)
                        continue
                    raise
                quantidade = 0
                try:
                    bloco = dados.get("data", [])
                    if isinstance(bloco, list) and bloco:
                        secao = bloco[0][0] if isinstance(bloco[0], list) and bloco[0] else None
                        if isinstance(secao, dict):
                            tabela = secao.get("data", [])
                            if isinstance(tabela, list):
                                quantidade = len(tabela)
                except Exception:
                    quantidade = 0
                if quantidade > 0:
                    break
                if tentativa < tentativas_max:
                    time.sleep(espera)
            if dados is None:
                return
            output_path = os.path.join(BASE_DIR, "jornada07-09.json")
            with open(output_path, "w", encoding="utf-8") as json_file:
                json.dump(dados, json_file, ensure_ascii=False, indent=4)
            logging.info("Relatório salvo como 'jornada07-09.json'.")
    except requests.exceptions.RequestException as e:
        error_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        execution_time = time.time() - start_time
        minutes, seconds = divmod(execution_time, 60)
        error_message = (f"Erro ao fazer a requisição: {e} "
                         f"Arquivo: jornada07-09.py, Hora: {error_time}, "
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