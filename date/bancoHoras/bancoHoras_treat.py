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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(os.path.dirname(SCRIPT_DIR))

BATCH_SIZE = 5000
THREADS = 4
SKIP_DROP = False

def encontrar_arquivos_json():
    """Descobre automaticamente todos os arquivos JSON de banco de horas disponíveis"""
    json_dir = os.path.join(SCRIPT_DIR, "jsons")
    arquivos = []
    
    if os.path.exists(json_dir):
        pattern = os.path.join(json_dir, "**", "*.json")
        found_files = glob.glob(pattern, recursive=True)
        
        for arquivo in found_files:
            if 'bancoHoras' in os.path.basename(arquivo):
                arquivos.append(arquivo)
        
        arquivos = sorted(arquivos)
        logging.info(f"Encontrados {len(arquivos)} arquivos JSON para processamento")
        
        
    else:
        logging.warning(f"Diretório jsons não encontrado: {json_dir}")
    
    return arquivos

server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
table_name = 'api_BancoHoras'

def processar_arquivo(json_file):
    """Processa um único arquivo JSON e retorna os dados normalizados"""
    logging.info(f"Processando arquivo: {json_file}")
    if not os.path.exists(json_file):
        logging.warning(f"Arquivo não encontrado: {json_file}")
        return []

    try:
        with open(json_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)
            logging.info(f"Arquivo carregado com sucesso: {json_file}")

        data = json_data.get('data', [])
        normalized_data = []

        for record in data:
            for entry in record:
                for item_data in entry['data']:
                    extra_time = item_data.get('extra_time', [])
                    
                    while len(extra_time) < 3:
                        extra_time.append({})
                    
                    he1 = extra_time[0].get('value', '') if isinstance(extra_time[0], dict) else ''
                    he2 = extra_time[1].get('value', '') if isinstance(extra_time[1], dict) else ''
                    he3 = extra_time[2].get('value', '') if isinstance(extra_time[2], dict) else ''
                    
                    he1 = '' if he1 is None else he1
                    he2 = '' if he2 is None else he2
                    he3 = '' if he3 is None else he3

                    time_balance_resume = item_data.get('time_balance_resume', [])
                    if isinstance(time_balance_resume, list) and len(time_balance_resume) >= 3:
                        saldo_inicial = time_balance_resume[0].get('value', '')
                        total_horas_positivas = time_balance_resume[1].get('value', '')
                        total_horas_negativas = time_balance_resume[2].get('value', '')
                    else:
                        saldo_inicial = ''
                        total_horas_positivas = ''
                        total_horas_negativas = ''

                    item = {
                        'Nome': item_data.get('name', ''),
                        'Matricula': item_data.get('registration_number', ''),
                        'Equipe': item_data.get('team_name', ''),
                        'Data': item_data.get('date', '').split(',')[-1].strip(),
                        'HorasFaltantes': item_data.get('missing_time', ''),
                        'HorasNormais': item_data.get('regular_time', ''),
                        'HoraSemIntervalo': item_data.get('interval_time', ''),
                        'SaldoBH': item_data.get('time_balance', ''),
                        'SaldoBHNegativo': item_data.get('overtime_missing_hours', ''),
                        'HorasQuitadas': item_data.get('time_balance_settled', ''),
                        'UnidadeNegocio': item_data.get('business_unit_name', ''),
                        'Departamento': item_data.get('department_name', ''),
                        'TotalHE1': he1,
                        'TotalHE2': he2,
                        'TotalHE3': he3,
                        'SaldoInicial': saldo_inicial,
                        'TotalHorasPositivas': total_horas_positivas,
                        'TotalHorasNegativas': total_horas_negativas
                    }
                    normalized_data.append(item)

        logging.info(f"Dados normalizados do arquivo {os.path.basename(json_file)}: {len(normalized_data)} registros")
        return normalized_data
    
    except Exception as e:
        logging.error(f"Erro ao processar {json_file}: {e}")
        return []

def main():
    start_time = datetime.now()
    logging.info(f"Iniciando processamento do bancoHoras_treat.py às {start_time}")
    
    try:
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

            create_table_sql = f"""
            CREATE TABLE [{table_name}] (
                [Nome] NVARCHAR(500),
                [Matricula] NVARCHAR(255),
                [Equipe] NVARCHAR(500),
                [Data] NVARCHAR(255),
                [HorasFaltantes] NVARCHAR(255),
                [HorasNormais] NVARCHAR(255),
                [HoraSemIntervalo] NVARCHAR(255),
                [SaldoBH] NVARCHAR(255),
                [SaldoBHNegativo] NVARCHAR(255),
                [HorasQuitadas] NVARCHAR(255),
                [UnidadeNegocio] NVARCHAR(500),
                [Departamento] NVARCHAR(500),
                [TotalHE1] NVARCHAR(255),
                [TotalHE2] NVARCHAR(255),
                [TotalHE3] NVARCHAR(255),
                [SaldoInicial] NVARCHAR(255),
                [TotalHorasPositivas] NVARCHAR(255),
                [TotalHorasNegativas] NVARCHAR(255)
            )
            """
            cursor.execute(create_table_sql)
            conn.commit()
            logging.info("Nova tabela criada com sucesso")
        else:
            logging.info("Mantendo tabela existente conforme solicitado")

        json_files = encontrar_arquivos_json()
        
        if not json_files:
            logging.warning("Nenhum arquivo JSON encontrado para processamento")
            return
        
        insert_sql = f"""
        INSERT INTO [{table_name}] (
            [Nome], [Matricula], [Equipe], [Data], [HorasFaltantes], 
            [HorasNormais], [HoraSemIntervalo], [SaldoBH], [SaldoBHNegativo],
            [HorasQuitadas], [UnidadeNegocio], [Departamento],
            [TotalHE1], [TotalHE2], [TotalHE3],
            [SaldoInicial], [TotalHorasPositivas], [TotalHorasNegativas]
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
