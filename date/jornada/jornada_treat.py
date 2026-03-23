import json
import pandas as pd
import pyodbc
import os
import logging
import glob
import gc
import time
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

BATCH_SIZE = 5000
SKIP_DROP = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = SCRIPT_DIR

def descobrir_arquivos_json():
    """Descobre automaticamente todos os arquivos JSON de jornada disponíveis"""
    jsons_dir = os.path.join(SCRIPT_DIR, "jsons")
    json_files = []
    
    if os.path.exists(jsons_dir):
        pattern = os.path.join(jsons_dir, "**", "*.json")
        found_files = glob.glob(pattern, recursive=True)
        
        for arquivo in found_files:
            if 'jornada' in os.path.basename(arquivo):
                json_files.append(arquivo)
        
        json_files = sorted(json_files)
        logging.info(f"Arquivos JSON de jornada descobertos automaticamente: {len(json_files)} arquivos")
        for file in json_files:
            logging.info(f"  - {file}")
    else:
        logging.warning(f"Diretório jsons não encontrado: {jsons_dir}")
    
    return json_files

json_files = descobrir_arquivos_json()

server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
table_name = 'api_Jornada'


def normalize_data(record):
    normalized_data = []
    for entry in record:
        if isinstance(entry, list):
            for item in entry:
                if 'data' in item:
                    for item_data in item['data']:
                        gestores = item_data.get('managers_names', '')
                        if isinstance(gestores, list):
                            gestores = ', '.join(filter(None, gestores))
                        
                        turno = item_data.get('shift_name', '')
                        if turno:
                            turno = turno.replace('Turno ', '').strip()

                        jornada = item_data.get('shift_appointments', [])
                        if isinstance(jornada, list):
                            jornada_formatada = []
                            for horario in jornada:
                                if horario and isinstance(horario, str):
                                    if len(horario.split(':')) == 3:
                                        hora, minuto, _ = horario.split(':')
                                        horario = f"{hora}:{minuto}"
                                    jornada_formatada.append(horario)
                            jornada = ' - '.join(jornada_formatada)

                        summary = item_data.get('summary', ['']*4)
                        if isinstance(summary, list):
                            summary += [''] * (4 - len(summary))
                        else:
                            summary = [''] * 4
                        
                        credito, debito, h_intervalo, horas_normais = summary

                        extra_time = item_data.get('extra_time', [])
                        if isinstance(extra_time, list):
                            extra_time += [{}] * (3 - len(extra_time))
                        else:
                            extra_time = [{}] * 3
                        he1, he2, he3 = [et.get('value', '') if isinstance(et, dict) else '' for et in extra_time]

                        daylight_extra_time = item_data.get('daylight_extra_time', [])
                        if isinstance(daylight_extra_time, list):
                            daylight_extra_time += [{}] * (3 - len(daylight_extra_time))
                        else:
                            daylight_extra_time = [{}] * 3
                        he_diurnas1, he_diurnas2, he_diurnas3 = [det.get('value', '') if isinstance(det, dict) else '' for det in daylight_extra_time]

                        item = {
                            'Data': item_data.get('date', ''),
                            'Equipe': item_data.get('team_name', ''),
                            'Gestores': gestores,
                            'Turno': turno,
                            'JornadaPrevista': jornada,
                            'Credito': credito,
                            'Debito': debito,
                            'HIntervalo': h_intervalo,
                            'HorasNormais': horas_normais,
                            'TotalHE1': he1,
                            'TotalHE2': he2,
                            'TotalHE3': he3,
                            'HorasTotais': item_data.get('total_time', ''),
                            'HorasPrevistas': item_data.get('shift_time', ''),
                            'TotalHEDiurna1': he_diurnas1,
                            'TotalHEDiurna2': he_diurnas2,
                            'TotalHEDiurna3': he_diurnas3,
                            'AdicionalNoturno': item_data.get('overnight_time', ''),
                            'Matricula': item_data.get('registration_number', ''),
                            'Saldo': item_data.get('time_balance', ''),
                            'Motivo/Observacao': item_data.get('motive', '')
                        }
                        normalized_data.append(item)

    logging.info(f"Quantidade de registros normalizados: {len(normalized_data)}")
    if len(normalized_data) == 0:
        logging.warning("Nenhum dado foi normalizado!")
        
    return normalized_data

def processar_arquivo(json_file):
    logging.info(f"Processando arquivo: {json_file}")
    if not os.path.exists(json_file):
        logging.warning(f"Arquivo não encontrado: {json_file}")
        return []

    try:
        logging.info(f"Abrindo arquivo: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        if 'data' not in json_data:
            logging.error(f"A chave 'data' não foi encontrada no arquivo {os.path.basename(json_file)}.")
            return []

        normalized_data = normalize_data(json_data['data'])

        for item in normalized_data:
            item['Data'] = item['Data'].split(',')[-1].strip()

        logging.info(f"Arquivo {os.path.basename(json_file)} processado: {len(normalized_data)} registros")
        return normalized_data
    
    except Exception as e:
        logging.error(f"Erro ao processar {json_file}: {e}")
        return []

def main():
    start_time = datetime.now()
    logging.info(f"Iniciando processamento do jornada_treat.py às {start_time}")
    
    try:
        logging.info("Montando string de conexão...")
        conn_str = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'TrustServerCertificate=yes;'
            'Encrypt=yes;'
            'Connection Timeout=60;'
            'Login Timeout=60;'
        )

        logging.info("Conectando ao banco de dados...")
        conn = pyodbc.connect(conn_str)
        conn.autocommit = False
        cursor = conn.cursor()
        cursor.fast_executemany = True
        logging.info("Conexão estabelecida com sucesso!")

        if not SKIP_DROP:
            logging.info("Verificando e removendo tabela antiga, se existir...")
            cursor.execute(f"""
                IF EXISTS (
                    SELECT * 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = '{table_name}'
                )
                BEGIN
                    DROP TABLE [{table_name}]
                    PRINT 'Tabela antiga removida'
                END
            """)
            conn.commit()
            logging.info("Tabela antiga removida, se existia.")

            logging.info("Criando nova tabela...")
            create_table_sql = """
            CREATE TABLE [api_Jornada] (
                [Data] NVARCHAR(255),
                [Equipe] NVARCHAR(500),
                [Gestores] NVARCHAR(MAX),
                [Turno] NVARCHAR(255),
                [JornadaPrevista] NVARCHAR(500),
                [Credito] NVARCHAR(255),
                [Debito] NVARCHAR(255),
                [HIntervalo] NVARCHAR(255),
                [HorasNormais] NVARCHAR(255),
                [TotalHE1] NVARCHAR(255),
                [TotalHE2] NVARCHAR(255),
                [TotalHE3] NVARCHAR(255),
                [HorasTotais] NVARCHAR(255),
                [HorasPrevistas] NVARCHAR(255),
                [TotalHEDiurna1] NVARCHAR(255),
                [TotalHEDiurna2] NVARCHAR(255),
                [TotalHEDiurna3] NVARCHAR(255),
                [AdicionalNoturno] NVARCHAR(255),
                [Matricula] NVARCHAR(255),
                [Saldo] NVARCHAR(255),
                [Motivo/Observacao] NVARCHAR(MAX)
            )
            """
            cursor.execute(create_table_sql)
            conn.commit()
            logging.info("Nova tabela criada com sucesso")
        else:
            logging.info("Mantendo tabela existente conforme solicitado")

        insert_sql = """
        INSERT INTO [api_Jornada] VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        total_inserted = 0
        logging.info(f"Iniciando processamento sequencial de {len(json_files)} arquivos")

        for json_file in tqdm(json_files, desc="Processando e Inserindo"):
            data_list = processar_arquivo(json_file)
            
            if data_list:
                df_temp = pd.DataFrame(data_list)
                df_temp = df_temp.fillna('').astype(str)
                
                values = [tuple(x) for x in df_temp.values]
                
                num_records = len(values)
                batch_count = 0
                
                for i in range(0, num_records, BATCH_SIZE):
                    batch = values[i:i + BATCH_SIZE]
                    retry_count = 0
                    max_retries = 3
                    
                    while retry_count < max_retries:
                        try:
                            cursor.fast_executemany = True
                            cursor.executemany(insert_sql, batch)
                            conn.commit()
                            batch_count += len(batch)
                            break
                        except (pyodbc.OperationalError, pyodbc.ProgrammingError) as e:
                            retry_count += 1
                            logging.warning(f"Erro na inserção (tentativa {retry_count}/{max_retries}): {e}")
                            
                            if retry_count < max_retries:
                                if isinstance(e, pyodbc.OperationalError):
                                    logging.info("Reconectando ao banco de dados...")
                                    try:
                                        conn.close()
                                    except:
                                        pass
                                    
                                    conn = pyodbc.connect(conn_str)
                                    conn.autocommit = False
                                    cursor = conn.cursor()
                                    time.sleep(2)
                                else:
                                    logging.error(f"Erro de dados: {e}. Pulando este lote.")
                                    break
                            else:
                                raise
                
                total_inserted += batch_count
                
                del df_temp
                del data_list
                del values
            
            gc.collect()

        logging.info(f"Total de registros inseridos: {total_inserted}")

        logging.info("Consultando total de registros na tabela...")
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = cursor.fetchone()[0]
        logging.info(f"Total de registros na tabela: {count}")
        
        end_time = datetime.now()
        duration = end_time - start_time
        logging.info(f"Processamento concluído em {duration}")
        if duration.total_seconds() > 0:
            logging.info(f"Velocidade média: {total_inserted / duration.total_seconds():.2f} registros por segundo")


    except Exception as e:
        logging.error(f"Erro: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            logging.info("Conexão fechada.")

if __name__ == "__main__":
    main()
