import sys
import io

# Настройка UTF-8 для stdout и stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Импортируем и запускаем основной модуль
if __name__ == "__main__":
    if len(sys.argv) > 1:
        module_name = sys.argv[1]
        if module_name == "ml_pipeline":
            import ml_pipeline
        elif module_name == "ml_api":
            import ml_api
        elif module_name == "ml_testing_framework":
            import ml_testing_framework
        elif module_name == "ml_monitoring":
            import ml_monitoring
        elif module_name == "run_ml_system":
            import run_ml_system
    else:
        print("Usage: python run_with_utf8.py <module_name>")
