import subprocess
import tempfile
import os
import time
import sys
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class PythonSandbox:
    """Безопасная песочница для выполнения Python-кода."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.python_executable = sys.executable
        logger.info(f"🐍 Sandbox инициализирован. Исполняемый файл: {self.python_executable}")
    
    def execute(self, code: str) -> Dict[str, Any]:
        """
        Выполняет Python-код в изолированном процессе.
        """
        logger.info(f"🛠️ Sandbox: Выполнение кода ({len(code)} символов)")
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            start_time = time.time()
            
            # КРИТИЧЕСКИ ВАЖНО: устанавливаем UTF-8 для ввода/вывода
            env = {
                **os.environ,
                "PYTHONIOENCODING": "utf-8",  # Принудительно UTF-8 для stdin/stdout/stderr
                "PYTHONUTF8": "1",            # Включает UTF-8 mode в Python 3.7+
                "PYTHONUNBUFFERED": "1"       # Отключает буферизацию вывода
            }
            
            # Запускаем в отдельном процессе
            result = subprocess.run(
                [self.python_executable, temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding='utf-8',
                env=env  # Передаем переменные окружения
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "execution_time": round(execution_time, 2)
            }
            
        except subprocess.TimeoutExpired:
            logger.warning(f"⏱️ Sandbox: Превышен лимит времени ({self.timeout}с)")
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {self.timeout} seconds",
                "execution_time": self.timeout
            }
        except Exception as e:
            logger.error(f"❌ Sandbox error: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "execution_time": 0
            }
        finally:
            # Гарантированная очистка
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_path}: {e}")