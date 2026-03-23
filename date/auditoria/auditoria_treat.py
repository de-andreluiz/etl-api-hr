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

BATCH_SIZE = 1000
SKIP_DROP = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(os.path.dirname(SCRIPT_DIR))

def descobrir_arquivos_json():
    """Descobre automaticamente todos os arquivos JSON disponíveis"""
    jsons_dir = os.path.join(SCRIPT_DIR, "jsons")
    json_files = []
    
    if os.path.exists(jsons_dir):
        pattern = os.path.join(jsons_dir, "**", "*.json")
        found_files = glob.glob(pattern, recursive=True)
        json_files = sorted(found_files)
        logging.info(f"Arquivos JSON descobertos automaticamente: {len(json_files)} arquivos")
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
table_name = 'api_Auditoria'

def processar_arquivo(json_file):
    """Processa um único arquivo JSON e retorna os dados normalizados"""
    logging.info(f"Processando arquivo: {json_file}")
    if not os.path.exists(json_file):
        logging.warning(f"Arquivo não encontrado: {json_file}")
        return []

    try:
        logging.info(f"Abrindo arquivo: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        data = json_data.get('data', [])
        normalized_data = []

        for record_group in data:
            for record in record_group:
                for entry in record['data']:
                    normalized_data.append({
                        'Nome': entry.get('name', ''),
                        'Data': entry.get('date', '').split(',')[-1].strip(),
                        'Ocorrencia': entry.get('occurrence', ''),
                        'Valor': entry.get('value', ''),
                        'HorasTrabalhadas': entry.get('worked_hours', ''),
                        'Matricula': entry.get('registration_number', '')
                    })
        
        logging.info(f"Arquivo {os.path.basename(json_file)} processado: {len(normalized_data)} registros")
        return normalized_data
    
    except Exception as e:
        logging.error(f"Erro ao processar {json_file}: {e}")
        return []

def main():
    start_time = datetime.now()
    logging.info(f"Iniciando processamento do auditoria_treat.py às {start_time}")
    logging.info(f"Usando tamanho de lote: {BATCH_SIZE}")
    
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
            create_table_sql = f"""
            CREATE TABLE [{table_name}] (
                [Nome] NVARCHAR(500),
                [Data] NVARCHAR(255),
                [Ocorrencia] NVARCHAR(MAX),
                [Valor] NVARCHAR(MAX),
                [HorasTrabalhadas] NVARCHAR(255),
                [Matricula] NVARCHAR(255)
            )
            """
            cursor.execute(create_table_sql)
            conn.commit()
            logging.info("Nova tabela criada com sucesso")
        else:
            logging.info("Mantendo tabela existente conforme solicitado")

        insert_sql = f"""
        INSERT INTO [{table_name}] (
            [Nome], [Data], [Ocorrencia], [Valor], [HorasTrabalhadas], [Matricula]
        ) VALUES (?, ?, ?, ?, ?, ?)
        """

        total_inserted = 0
        logging.info(f"Iniciando processamento sequencial de {len(json_files)} arquivos")
        
        if not json_files:
            logging.warning("Nenhum arquivo JSON encontrado para processar!")
        
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
