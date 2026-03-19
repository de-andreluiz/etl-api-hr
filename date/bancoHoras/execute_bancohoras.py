import os
import sys
import logging
import subprocess
import time
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def descobrir_scripts_disponiveis():
    scripts = {}
    jsons_dir = os.path.join(BASE_DIR, "jsons")
    
    if not os.path.exists(jsons_dir):
        logging.warning(f"Diretório jsons não encontrado: {jsons_dir}")
        return scripts
    
    for ano_item in os.listdir(jsons_dir):
        ano_path = os.path.join(jsons_dir, ano_item)
        if not os.path.isdir(ano_path) or not ano_item.isdigit():
            continue
            
        scripts[ano_item] = {}
        
        for periodo_item in os.listdir(ano_path):
            periodo_path = os.path.join(ano_path, periodo_item)
            if not os.path.isdir(periodo_path):
                continue
                
            for arquivo in os.listdir(periodo_path):
                if arquivo.endswith('.py'):
                    script_path = os.path.join(periodo_path, arquivo)
                    scripts[ano_item][periodo_item] = script_path
                    logging.debug(f"Script descoberto: {ano_item}/{periodo_item} -> {arquivo}")
                    break
    
    logging.info(f"Scripts descobertos automaticamente: {scripts}")
    return scripts

def obter_periodos_inteligentes():
    agora = datetime.now()
    mes_atual = agora.month
    ano_atual = agora.year
    
    primeiro_dia_mes_atual = agora.replace(day=1)
    ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
    mes_anterior = ultimo_dia_mes_anterior.month
    ano_anterior = ultimo_dia_mes_anterior.year
    
    logging.info(f"Mês atual: {mes_atual}/{ano_atual}, Mês anterior: {mes_anterior}/{ano_anterior}")
    
    def mapear_mes_para_periodo(mes, ano):
        if ano >= 2026:
            return f"{mes:02d}"

        elif ano == 2024:
            if mes in [1, 2, 3]:
                return "01-03"
            elif mes in [4, 5, 6]:
                return "04-06"
            elif mes in [7, 8, 9]:
                return "07-09"
            elif mes in [10, 11]:
                return "10-11"
            elif mes == 12:
                return "12"
        else:
            if mes in [1, 2, 3]:
                return "01-03"
            elif mes in [4, 5, 6]:
                return "04-06"
            elif mes == 7:
                return "07"
            elif mes == 8:
                return "08"
            elif mes == 9:
                return "09"
            elif mes == 10:
                return "10"
            elif mes == 11:
                return "11"
            elif mes == 12:
                return "12"
        
        return None
    
    periodos_necessarios = {}
    
    periodo_anterior = mapear_mes_para_periodo(mes_anterior, ano_anterior)
    if periodo_anterior:
        if str(ano_anterior) not in periodos_necessarios:
            periodos_necessarios[str(ano_anterior)] = []
        periodos_necessarios[str(ano_anterior)].append(periodo_anterior)
        logging.info(f"Adicionado PRIMEIRO (mês anterior): {ano_anterior}/{periodo_anterior}")
    
    periodo_atual = mapear_mes_para_periodo(mes_atual, ano_atual)
    if periodo_atual:
        if str(ano_atual) not in periodos_necessarios:
            periodos_necessarios[str(ano_atual)] = []
        if periodo_atual not in periodos_necessarios[str(ano_atual)]:
            periodos_necessarios[str(ano_atual)].append(periodo_atual)
            logging.info(f"Adicionado SEGUNDO (mês atual): {ano_atual}/{periodo_atual}")
    
    logging.info(f"Períodos identificados para execução: {periodos_necessarios}")
    return periodos_necessarios

def executar_script(script_path, descricao, max_tentativas=5, tempo_espera=30):
    
    script_dir = os.path.dirname(script_path)
    script_name = os.path.basename(script_path)
    json_name = script_name.replace('.py', '.json')
    json_path = os.path.join(script_dir, json_name)
    
    if os.path.exists(json_path):
        logging.info(f"JSON já existe para {descricao} em {json_path}. Sobrescrevendo...")
    
    tentativas = 0
    while tentativas < max_tentativas:
        tentativas += 1
        try:
            logging.info(f"Executando {descricao}: {script_path} (Tentativa {tentativas}/{max_tentativas})")
            resultado = subprocess.run([sys.executable, script_path], 
                                     capture_output=True, 
                                     text=True)
            
            if resultado.returncode == 0:
                logging.info(f"Script {os.path.basename(script_path)} executado com sucesso.")
                return True
            else:
                logging.error(f"Erro ao executar {os.path.basename(script_path)} (Tentativa {tentativas}/{max_tentativas})")
                logging.error(f"Saída de erro: {resultado.stderr}")
                
                if tentativas < max_tentativas:
                    logging.info(f"Aguardando {tempo_espera} segundos antes de tentar novamente...")
                    time.sleep(tempo_espera)
        except Exception as e:
            logging.error(f"Erro ao executar {os.path.basename(script_path)}: {e} (Tentativa {tentativas}/{max_tentativas})")
            
            if tentativas < max_tentativas:
                logging.info(f"Aguardando {tempo_espera} segundos antes de tentar novamente...")
                time.sleep(tempo_espera)
    
    logging.error(f"Falha ao executar {descricao} após {max_tentativas} tentativas.")
    return False

def main():
    max_retry = 5
    retry_wait = 30
    
    try:
        logging.info("Iniciando download dos dados de banco de horas (MODO INTELIGENTE)")
        
        scripts = descobrir_scripts_disponiveis()
        
        if not scripts:
            logging.error("Nenhum script encontrado na estrutura de pastas!")
            return False
        
        periodos_inteligentes = obter_periodos_inteligentes()
        scripts_para_executar = {}
        
        for ano, periodos in periodos_inteligentes.items():
            if ano in scripts:
                scripts_para_executar[ano] = {}
                for periodo in periodos:
                    if periodo in scripts[ano]:
                        scripts_para_executar[ano][periodo] = scripts[ano][periodo]
                        logging.info(f"Adicionado para execução: {ano}/{periodo}")
                    else:
                        logging.warning(f"Período não encontrado nos scripts: {ano}/{periodo}")
        
        if not scripts_para_executar:
            logging.warning("Nenhum script encontrado para os períodos inteligentes")
            return False
        
        logging.info("Modo inteligente ativo: executando apenas mês atual e anterior")
        
        anos_ordenados = sorted(scripts_para_executar.keys())
        scripts_executados = 0
        
        for ano_sel in anos_ordenados:
            periodos = scripts_para_executar[ano_sel]
            
            def ordenar_periodo(periodo):
                if '-' in periodo:
                    return int(periodo.split('-')[0])
                else:
                    return int(periodo)
            
            periodos_ordenados = sorted(periodos.keys(), key=ordenar_periodo)
            
            for periodo_sel in periodos_ordenados:
                script_path = periodos[periodo_sel]
                descricao = f"script de banco de horas {ano_sel}/{periodo_sel}"
                logging.info(f"Executando em ordem cronológica: {ano_sel}/{periodo_sel}")
                if executar_script(script_path, descricao, max_retry, retry_wait):
                    scripts_executados += 1
        
        logging.info(f"Download concluído. {scripts_executados} scripts executados com sucesso.")
        return True
    
    except Exception as e:
        logging.error(f"Erro na execução do processamento: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 