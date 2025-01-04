import os
import redis
import time
import zipfile
import importlib.util
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

class Context:
    def __init__(self, env):
        self.env = env

def load_function_from_zip(zip_path, zip_entry_file, entry_function):
    extract_dir = "/tmp/user_code"
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        main_module_path = os.path.join(extract_dir, zip_entry_file)
        if not os.path.exists(main_module_path):
            raise FileNotFoundError(f"Arquivo '{zip_entry_file}' não encontrado no ZIP extraído.")
        spec = importlib.util.spec_from_file_location("user_module", main_module_path)
        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)
        if not hasattr(user_module, entry_function):
            raise AttributeError(f"Função '{entry_function}' não encontrada em '{zip_entry_file}'.")
        return getattr(user_module, entry_function)
    except Exception as e:
        logging.error(f"Erro ao carregar a função do ZIP: {e}")
        raise
    finally:
        if os.path.exists(extract_dir):
            for root, dirs, files in os.walk(extract_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))

def load_function_from_pyfile(pyfile_path, entry_function):
    try:
        if not Path(pyfile_path).exists():
            raise FileNotFoundError(f"Arquivo '.py' não encontrado no caminho especificado: {pyfile_path}")
        sys.path.append(os.path.dirname(pyfile_path))
        spec = importlib.util.spec_from_file_location("user_module", pyfile_path)
        user_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(user_module)
        if not hasattr(user_module, entry_function):
            raise AttributeError(f"Função '{entry_function}' não encontrada no arquivo '.py'.")
        return getattr(user_module, entry_function)
    except Exception as e:
        logging.error(f"Erro ao carregar a função do arquivo '.py': {e}")
        raise

def load_handler(pyfile_or_zip, pyfile_path, zip_path, zip_entry_file, entry_function):
    if pyfile_or_zip == "pyfile":
        return load_function_from_pyfile(pyfile_path, entry_function)
    elif pyfile_or_zip == "zip":
        return load_function_from_zip(zip_path, zip_entry_file, entry_function)
    else:
        raise ValueError("O valor de PYFILE_OR_ZIP deve ser 'pyfile' ou 'zip'.")

def process_data(handler_function, input_data, redis_client, output_key, context):
    try:
        result = handler_function(input_data, context)
        if isinstance(result, dict):
            redis_client.set(output_key, json.dumps(result))
            logging.info(f"Resultado armazenado no Redis sob a chave: {output_key}")
        else:
            logging.warning("A função retornou um resultado que não é um dicionário. Ignorando.")
    except Exception as e:
        logging.error(f"Erro durante a execução da função: {e}")

def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_input_key = os.getenv("REDIS_INPUT_KEY", "metrics")
    redis_output_key = os.getenv("REDIS_OUTPUT_KEY", "output")
    monitoring_period = int(os.getenv("MONITORING_PERIOD", 5))
    pyfile_or_zip = os.getenv("PYFILE_OR_ZIP", "pyfile")
    pyfile_path = os.getenv("PYFILE_PATH", "/opt/usermodule.py")
    zip_path = os.getenv("ZIP_FILE_PATH", "/opt/user_function.zip")
    zip_entry_file = os.getenv("ZIP_ENTRY_FILE", "handler.py")
    entry_function_name = os.getenv("ENTRY_FUNCTION", "handler")

    try:
        redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        redis_client.ping()
        logging.info(f"Conectado ao Redis em {redis_host}:{redis_port}")
    except redis.ConnectionError as e:
        logging.error(f"Erro ao conectar ao Redis: {e}")
        return

    try:
        handler_function = load_handler(
            pyfile_or_zip, pyfile_path, zip_path, zip_entry_file, entry_function_name
        )
    except Exception as e:
        logging.error(f"Falha ao carregar a função do arquivo: {e}")
        return

    context = Context(env={})
    last_seen_data = None
    while True:
        try:
            input_data = redis_client.get(redis_input_key)
            if input_data:
                input_data = json.loads(input_data)
                if input_data != last_seen_data:
                    logging.info("Novos dados detectados, invocando a função handler...")
                    last_seen_data = input_data
                    process_data(handler_function, input_data, redis_client, redis_output_key, context)
                else:
                    logging.info("Nenhum novo dado detectado. Aguardando.")
            else:
                logging.warning(f"Nenhum dado encontrado para a chave: {redis_input_key}")
        except json.JSONDecodeError as e:
            logging.error(f"Erro ao decodificar os dados do Redis: {e}")
        except Exception as e:
            logging.error(f"Erro ao interagir com o Redis: {e}")
        time.sleep(monitoring_period)

if __name__ == "__main__":
    main()
