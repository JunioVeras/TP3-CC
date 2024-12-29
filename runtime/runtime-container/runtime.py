import os
import redis
import time
import zipfile
import importlib.util
import json

class Context:
    def __init__(self, env):
        self.env = env

def load_function_from_zip(zip_path, entry_function):
    extract_dir = "/tmp/user_code"
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_dir)
    
    main_module_path = os.path.join(extract_dir, "main.py")
    spec = importlib.util.spec_from_file_location("user_module", main_module_path)
    user_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(user_module)
    
    if not hasattr(user_module, entry_function):
        raise AttributeError(f"Function '{entry_function}' not found in 'main.py'")
    
    return getattr(user_module, entry_function)

def main():
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_input_key = os.getenv("REDIS_INPUT_KEY", "metrics")
    redis_output_key = os.getenv("REDIS_OUTPUT_KEY", "output")
    monitoring_period = int(os.getenv("MONITORING_PERIOD", 5))
    zip_file_path = os.getenv("ZIP_FILE_PATH", "/opt/user_function.zip")
    entry_function_name = os.getenv("ENTRY_FUNCTION", "handler")

    r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

    try:
        handler_function = load_function_from_zip(zip_file_path, entry_function_name)
    except Exception as e:
        print(f"Error loading function: {e}")
        return

    context = Context(env={})

    last_seen_data = None

    while True:
        try:
            input_data = r.get(redis_input_key)
            if input_data:
                input_data = json.loads(input_data)
                if input_data != last_seen_data:
                    print("New data detected, invoking the handler...")
                    last_seen_data = input_data

                    try:
                        result = handler_function(input_data, context)
                        if isinstance(result, dict):
                            r.set(redis_output_key, json.dumps(result))
                            print(f"Result stored in Redis under key: {redis_output_key}")
                        else:
                            print("Handler returned a non-dictionary result. Skipping.")
                    except Exception as func_error:
                        print(f"Error during function execution: {func_error}")
                else:
                    print("No new data detected. Skipping invocation.")
            else:
                print(f"No data found for key: {redis_input_key}")

        except Exception as e:
            print(f"Error interacting with Redis: {e}")

        time.sleep(monitoring_period)

if __name__ == "__main__":
    main()
