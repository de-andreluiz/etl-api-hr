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

BATCH_SIZE = 5000
SKIP_DROP = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(BASE_DIR, "unidadesNegocio_register.json")
server = os.getenv("DB_SERVER")
database = os.getenv("DB_DATABASE")
username = os.getenv("DB_USERNAME")
password = os.getenv("DB_PASSWORD")
table_name = 'api_UnidadesNegocio'

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
    logging.info(f"Iniciando processamento do unidadesNegocio_treat.py às {start_time}")
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
        conn.autocommit = False  # Desativar autocommit para melhor performance
        cursor = conn.cursor()
        logging.info("Conexão estabelecida com sucesso!")
        
        if not SKIP_DROP:
            logging.info("Verificando e removendo tabela antiga, se existir...")
            cursor.execute(f"""
                IF EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{table_name}')
                BEGIN
                    DROP TABLE [{table_name}]
                    PRINT 'Tabela antiga removida'
                END
            """)
            conn.commit()
            logging.info("Tabela antiga removida, se existia.")

            logging.info("Criando nova tabela...")
            create_table_sql = """
            CREATE TABLE [api_UnidadesNegocio] (
                [Código] NVARCHAR(255),
                [Nome] NVARCHAR(255),
                [Razão Social] NVARCHAR(255),
                [É Empregador] NVARCHAR(255),
                [Tipo de Rua] NVARCHAR(255),
                [Cidade] NVARCHAR(255),
                [Estado] NVARCHAR(255),
                [Estado Nome] NVARCHAR(255),
                [Preferência do Cliente] NVARCHAR(255),
                [Contagem de Funcionários] NVARCHAR(255)
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
        
        business_units = json_data['business_units']
        normalized_data = []

        for unit in business_units:
            address = unit.get('address') or {}
            street_type = address.get('street_type') or {}
            city = address.get('city') or {}
            state = address.get('state') or {}
            client_preference = unit.get('client_preference') or {}

            item = {
                'Código': unit.get('code', ''),
                'Nome': unit.get('name', ''),
                'Razão Social': unit.get('corporate_name', ''),
                'É Empregador': unit.get('is_employer', ''),
                'Tipo de Rua': street_type.get('name', ''),
                'Cidade': city.get('name', ''),
                'Estado': city.get('state', ''),
                'Estado Nome': state.get('name', ''),
                'Preferência do Cliente': client_preference.get('name', ''),
                'Contagem de Funcionários': unit.get('employees_count', '')
            }
            normalized_data.append(item)

        logging.info(f"Dados normalizados: {len(normalized_data)} registros encontrados")
        
        if normalized_data:
            df = pd.DataFrame(normalized_data)
            df = df[['Código', 'Nome', 'Razão Social', 'É Empregador', 'Tipo de Rua', 'Cidade', 
                     'Estado', 'Estado Nome', 'Preferência do Cliente', 'Contagem de Funcionários']]
            df = df.fillna('').astype(str)

            insert_sql = """
            INSERT INTO [api_UnidadesNegocio] (
                [Código], [Nome], [Razão Social], [É Empregador], [Tipo de Rua], 
                [Cidade], [Estado], [Estado Nome], [Preferência do Cliente], [Contagem de Funcionários]
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            logging.info("Conexão com o banco de dados fechada")

    end_time = datetime.now()
    duration = end_time - start_time
    logging.info(f"Processamento concluído em {duration}")
    if 'total_inserted' in locals() and total_inserted > 0:
        logging.info(f"Velocidade média: {total_inserted / duration.total_seconds():.2f} registros por segundo")

if __name__ == "__main__":
    main()
