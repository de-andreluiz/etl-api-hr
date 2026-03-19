import json
import pandas as pd
import pyodbc
import os
import logging
import gc
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(BASE_DIR, "cargo_register.json")

BATCH_SIZE = 1000
SKIP_DROP = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
table_name = 'api_Cargos'

def excluir_arquivo_json(arquivo):
    try:
        if os.path.exists(arquivo):
            os.remove(arquivo)
            logging.info(f"Arquivo excluído com sucesso: {arquivo}")
            return True
        else:
            logging.warning(f"Arquivo não encontrado para exclusão: {arquivo}")
            return False
    except Exception as e:
        logging.error(f"Erro ao excluir o arquivo {arquivo}: {e}")
        return False

def main():
    start_time = datetime.now()
    logging.info(f"Iniciando processamento do cargo_treat.py às {start_time}")
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
        )

        logging.info("Conectando ao banco de dados...")
        conn = pyodbc.connect(conn_str)
        conn.autocommit = False
        cursor = conn.cursor()
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
                [Codigo] NVARCHAR(255),
                [Nome] NVARCHAR(255),
                [Nome Feminino] NVARCHAR(255),
                [CodCBO] NVARCHAR(255),
                [NomeCBO] NVARCHAR(255)
            )
            """
            cursor.execute(create_table_sql)
            conn.commit()
            logging.info("Nova tabela criada com sucesso")
        else:
            logging.info("Mantendo tabela existente conforme solicitado")

        if not os.path.exists(json_file):
            raise FileNotFoundError(f"Arquivo JSON não encontrado em: {json_file}")
        
        logging.info(f"Carregando dados do arquivo: {json_file}")
        with open(json_file, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        logging.info("Dados JSON carregados com sucesso")

        job_titles = json_data['job_titles']
        normalized_data = []

        for job in job_titles:
            cbo = job.get('cbo') or {}
            item = {
                'Codigo': job.get('code', ''),
                'Nome': job.get('name', ''),
                'Nome Feminino': job.get('female_name', ''),
                'CodCBO': cbo.get('code', ''),
                'NomeCBO': cbo.get('name', '')
            }
            normalized_data.append(item)

        logging.info(f"Dados normalizados: {len(normalized_data)} registros encontrados")

        if normalized_data:
            df = pd.DataFrame(normalized_data)
            df = df[['Codigo', 'Nome', 'Nome Feminino', 'CodCBO', 'NomeCBO']]
            df = df.fillna('').astype(str)

            insert_sql = f"""
            INSERT INTO [{table_name}] (
                [Codigo], [Nome], [Nome Feminino], [CodCBO], [NomeCBO]
            ) VALUES (?, ?, ?, ?, ?)
            """

            total_inserted = 0
            num_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
            logging.info(f"Iniciando inserção de {len(df)} registros em {num_batches} lotes")
            
            for i in tqdm(range(0, len(df), BATCH_SIZE), desc="Inserindo registros", total=num_batches):
                batch = df.iloc[i:i + BATCH_SIZE]
                values = [tuple(x) for x in batch.values]
                cursor.fast_executemany = True
                cursor.executemany(insert_sql, values)
                
                conn.commit()
                total_inserted += len(batch)
                
                if i % (BATCH_SIZE * 10) == 0 and i > 0:
                    logging.info(f"Progresso: {total_inserted} de {len(df)} registros inseridos ({total_inserted/len(df)*100:.1f}%)")
            
            logging.info(f"Total de registros inseridos: {total_inserted}")
            
            del df
            del normalized_data
            del values
            gc.collect()


            if total_inserted > 0:
                if excluir_arquivo_json(json_file):
                    logging.info("Arquivo JSON excluído com sucesso após processamento")
                else:
                    logging.warning("Não foi possível excluir o arquivo JSON")

        logging.info("Consultando total de registros na tabela...")
        cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
        count = cursor.fetchone()[0]
        logging.info(f"Total de registros na tabela: {count}")

    except FileNotFoundError as e:
        logging.error(f"Erro ao ler arquivo: {e}")
        raise
    except pyodbc.Error as e:
        logging.error(f"Erro no banco de dados: {e}")
        raise
    except Exception as e:
        logging.error(f"Erro inesperado: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
            logging.info("Conexão fechada.")

    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Processamento concluído em {duration}")
    if 'total_inserted' in locals() and total_inserted > 0:
        logging.info(f"Velocidade média: {total_inserted / duration.total_seconds():.2f} registros por segundo")

if __name__ == "__main__":
    main()
