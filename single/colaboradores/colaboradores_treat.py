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

BATCH_SIZE = 1000
SKIP_DROP = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(BASE_DIR, "colaboradores_register.json")
server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
table_name = 'api_Colaboradores'

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
    logging.info(f"Iniciando processamento do colaboradores_treat.py às {start_time}")
    logging.info(f"Usando tamanho de lote: {BATCH_SIZE}")
    
    try:
        logging.info("Tentando conectar ao banco de dados...")
        conn_str = (
            f'DRIVER={{ODBC Driver 18 for SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={database};'
            f'UID={username};'
            f'PWD={password};'
            'TrustServerCertificate=yes;'
            'Encrypt=yes;'
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        logging.info("Conexão estabelecida com sucesso!")

        if not SKIP_DROP:
            logging.info("Verificando e removendo tabela antiga, se existir...")
            cursor.execute("""
            IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'api_Colaboradores')
            BEGIN
                DROP TABLE [api_Colaboradores]
            END
        """)
            conn.commit()
            logging.info("Tabela antiga removida, se existia.")

            create_table_sql = """
        CREATE TABLE [api_Colaboradores] (
            [Nome] NVARCHAR(255),
            [Matricula] NVARCHAR(255),
            [Cargo] NVARCHAR(255),
            [Equipe] NVARCHAR(255),
            [Turno] NVARCHAR(255),
            [ConfigControlePonto] NVARCHAR(255),
            [CLT] NVARCHAR(255),
            [CentroCusto] NVARCHAR(255),
            [DtAdmissao] NVARCHAR(255),
            [DtDemissao] NVARCHAR(255),
            [Grupo] NVARCHAR(255),
            [Ativo] NVARCHAR(255),
            [DtUltFechamento] NVARCHAR(255),
            [UnidadeNegocio] NVARCHAR(255)
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

        data = json_data['data']
        normalized_data = []

        for record in data:
            for entry in record:
                for item_data in entry['data']:
                    item = {
                        'Nome': item_data.get('name', ''),
                        'Matricula': item_data.get('registration_number', ''),
                        'Cargo': item_data.get('job_title', ''),
                        'Equipe': item_data.get('team', ''),
                        'Turno': item_data.get('shift', ''),
                        'ConfigControlePonto': item_data.get('client_preference', ''),
                        'CLT': item_data.get('is_clt', ''),
                        'CentroCusto': item_data.get('cost_center', ''),
                        'DtAdmissao': item_data.get('admission_date', ''),
                        'DtDemissao': item_data.get('resignation_date', ''),
                        'Grupo': item_data.get('group', ''),
                        'Ativo': item_data.get('employee_status', ''),
                        'DtUltFechamento': item_data.get('last_closed_date', ''),
                        'UnidadeNegocio': item_data.get('business_unit', '')
                    }
                    normalized_data.append(item)

        for item in normalized_data:
            item['DtAdmissao'] = item['DtAdmissao'].split(',')[-1].strip()  # Pega a parte após a vírgula
            item['DtDemissao'] = item['DtDemissao'].split(',')[-1].strip()  # Pega a parte após a vírgula
            item['DtUltFechamento'] = item['DtUltFechamento'].split(',')[-1].strip()  # Pega a parte após a vírgula

        logging.info(f"Dados normalizados: {len(normalized_data)} registros encontrados")

        if normalized_data:
            df = pd.DataFrame(normalized_data)
            df = df.fillna('').astype(str)

            insert_sql = """
            INSERT INTO [api_Colaboradores] (
                [Nome], [Matricula], [Cargo], [Equipe], [Turno], [ConfigControlePonto], 
                [CLT], [CentroCusto], [DtAdmissao], [DtDemissao], [Grupo], [Ativo], 
                [DtUltFechamento], [UnidadeNegocio]
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            total_inserted = 0
            num_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
            logging.info(f"Iniciando inserção de {len(df)} registros em {num_batches} lotes")
            
            for i in tqdm(range(0, len(df), BATCH_SIZE), desc="Inserindo registros", total=num_batches):
                batch = df.iloc[i:i + BATCH_SIZE]
                values = [tuple(x) for x in batch.values]
                cursor.fast_executemany = True  # Otimizar inserção em massa
                cursor.executemany(insert_sql, values)
                conn.commit()
                total_inserted += len(batch)
                
                if i % (BATCH_SIZE * 10) == 0 and i > 0:
                    logging.info(f"Progresso: {total_inserted} de {len(df)} registros inseridos ({total_inserted/len(df)*100:.1f}%)")

            logging.info("Consultando total de registros na tabela...")
            cursor.execute("SELECT COUNT(*) FROM [api_Colaboradores]")
            count = cursor.fetchone()[0]
            logging.info(f"Total de registros na tabela: {count}")
            
            del df
            del normalized_data
            del values
            gc.collect()

            if total_inserted > 0:
                if excluir_arquivo_json(json_file):
                    logging.info("Arquivo JSON excluído com sucesso após processamento")
                else:
                    logging.warning("Não foi possível excluir o arquivo JSON")

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
            logging.info("Conexão com o banco de dados fechada")

    logging.info("Processamento concluído com sucesso!")
    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Processamento concluído em {duration}")
    if 'total_inserted' in locals() and total_inserted > 0:
        logging.info(f"Velocidade média: {total_inserted / duration.total_seconds():.2f} registros por segundo")

if __name__ == "__main__":
    main()
