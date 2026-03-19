import json
import pandas as pd
import pyodbc
import os
import logging
import time
import glob
import gc
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BATCH_SIZE = 5000
SKIP_DROP = False

def descobrir_jsons_disponiveis():
    """
    Descobre dinamicamente todos os arquivos .json disponíveis na estrutura de pastas
    Retorna uma lista de caminhos para todos os arquivos JSON encontrados
    """
    json_files = []
    jsons_dir = os.path.join(BASE_DIR, "jsons")
    
    if not os.path.exists(jsons_dir):
        logging.warning(f"Diretório jsons não encontrado: {jsons_dir}")
        return json_files
    
    for ano_item in os.listdir(jsons_dir):
        ano_path = os.path.join(jsons_dir, ano_item)
        if not os.path.isdir(ano_path) or not ano_item.isdigit():
            continue
            
        for periodo_item in os.listdir(ano_path):
            periodo_path = os.path.join(ano_path, periodo_item)
            if not os.path.isdir(periodo_path):
                continue
                
            for arquivo in os.listdir(periodo_path):
                if arquivo.endswith('.json'):
                    json_path = os.path.join(periodo_path, arquivo)
                    json_files.append(json_path)
                    logging.debug(f"JSON descoberto: {ano_item}/{periodo_item} -> {arquivo}")
    
    json_files.sort()
    logging.info(f"JSONs descobertos automaticamente: {len(json_files)} arquivos")
    for json_file in json_files:
        logging.info(f"  - {json_file}")
    
    return json_files

json_files = descobrir_jsons_disponiveis()

server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
table_name = 'api_RegistroPonto'

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

        for record in data:
            for entry in record:
                for item_data in entry['data']:
                    item = {
                        'Nome': item_data.get('employee_name', ''),
                        'Data': item_data.get('date', '').split(',')[-1].strip(),
                        'Hora': item_data.get('time', ''),
                        'Matricula': item_data.get('registration_number', ''),
                        'Departamento': item_data.get('team_name', ''),
                        'Turno': item_data.get('shift_name', ''),
                        'Metodo': item_data.get('source', ''),
                        'Ajustado': item_data.get('manually_changed', ''),
                        'MotivoAjuste': item_data.get('motive', ''),
                        'QuemAjustou': item_data.get('updated_by', ''),
                        'TipoRegistro': item_data.get('time_card_index', ''),
                        'Origem': item_data.get('software_method', '')
                    }
                    normalized_data.append(item)
        
        logging.info(f"Arquivo {os.path.basename(json_file)} processado: {len(normalized_data)} registros")
        return normalized_data
    
    except Exception as e:
        logging.error(f"Erro ao processar {json_file}: {e}")
        return []

def main():
    start_time = datetime.now()
    logging.info(f"Iniciando processamento do ponto_treat.py às {start_time}")
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
                [Nome] NVARCHAR(255),
                [Data] NVARCHAR(255),
                [Hora] NVARCHAR(255),
                [Matricula] NVARCHAR(255),
                [Departamento] NVARCHAR(255),
                [Turno] NVARCHAR(255),
                [Metodo] NVARCHAR(255),
                [Ajustado] NVARCHAR(255),
                [MotivoAjuste] NVARCHAR(255),
                [QuemAjustou] NVARCHAR(255),
                [TipoRegistro] NVARCHAR(255),
                [Origem] NVARCHAR(255)
            )
            """
            cursor.execute(create_table_sql)
            conn.commit()
            logging.info("Nova tabela criada com sucesso")
        else:
            logging.info("Mantendo tabela existente conforme solicitado")

        insert_sql = f"""
        INSERT INTO [{table_name}] (
            [Nome], [Data], [Hora], [Matricula], [Departamento], [Turno], [Metodo], 
            [Ajustado], [MotivoAjuste], [QuemAjustou], [TipoRegistro], [Origem]
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        except pyodbc.OperationalError as e:
                            retry_count += 1
                            logging.warning(f"Erro na inserção (tentativa {retry_count}/{max_retries}): {e}")
                            
                            if retry_count < max_retries:
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
