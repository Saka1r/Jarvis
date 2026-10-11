"""
Тесты для subsystems/sandbox.py
Проверяет безопасное выполнение Python-кода в изолированной среде.

Запуск: pytest tests/test_sandbox.py -v
"""

import pytest
from subsystems.sandbox import PythonSandbox


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def sandbox():
    """Создает экземпляр песочницы с коротким таймаутом для тестов."""
    return PythonSandbox(timeout=5)


@pytest.fixture
def slow_sandbox():
    """Песочница с увеличенным таймаутом для долгих тестов."""
    return PythonSandbox(timeout=10)


# ============================================================
# БАЗОВЫЕ ТЕСТЫ
# ============================================================

class TestBasicExecution:
    """Тесты базового выполнения кода."""
    
    def test_simple_print(self, sandbox):
        """Тест простого вывода через print()."""
        result = sandbox.execute("print('Hello, World!')")
        
        assert result["success"] is True
        assert result["stdout"] == "Hello, World!"
        assert result["stderr"] == ""
        assert result["execution_time"] >= 0
    
    def test_cyrillic_output(self, sandbox):
        """Тест вывода кириллицы (проверка UTF-8)."""
        result = sandbox.execute("print('Привет, мир! Это Джарвис.')")
        
        assert result["success"] is True
        assert result["stdout"] == "Привет, мир! Это Джарвис."
        assert result["stderr"] == ""
    
    def test_mixed_language_output(self, sandbox):
        """Тест вывода смешанного текста (кириллица + латиница + цифры)."""
        code = "print('CPU: 12%, RAM: 8.2 GB, Статус: онлайн')"
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "CPU: 12%" in result["stdout"]
        assert "Статус: онлайн" in result["stdout"]
    
    def test_empty_code(self, sandbox):
        """Тест с пустым кодом."""
        result = sandbox.execute("")
        
        assert result["success"] is True
        assert result["stdout"] == ""
        assert result["stderr"] == ""
    
    def test_multiline_output(self, sandbox):
        """Тест многострочного вывода."""
        code = """
print('Строка 1')
print('Строка 2')
print('Строка 3')
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "Строка 1" in result["stdout"]
        assert "Строка 2" in result["stdout"]
        assert "Строка 3" in result["stdout"]


# ============================================================
# ТЕСТЫ С ИМПОРТАМИ
# ============================================================

class TestImports:
    """Тесты работы с импортами стандартной библиотеки."""
    
    def test_math_import(self, sandbox):
        """Тест импорта math и математических операций."""
        code = """
import math
result = math.sqrt(144)
print(f"Квадратный корень из 144 равен {result}")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "12.0" in result["stdout"]
    
    def test_json_operations(self, sandbox):
        """Тест работы с JSON."""
        code = """
import json
data = {"name": "Джарвис", "version": 2.0, "active": True}
print(json.dumps(data, ensure_ascii=False))
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "Джарвис" in result["stdout"]
        assert "2.0" in result["stdout"]
    
    def test_datetime_operations(self, sandbox):
        """Тест работы с датой и временем."""
        code = """
from datetime import datetime
now = datetime.now()
print(f"Год: {now.year}")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        # Проверяем, что год корректный (не меньше 2020)
        assert "202" in result["stdout"] or "203" in result["stdout"]
    
    def test_regex_operations(self, sandbox):
        """Тест работы с регулярными выражениями."""
        import textwrap
        
        code = textwrap.dedent(r"""
            import re
            text = "Температура: 23.5°C, Давление: 760 мм"
            numbers = re.findall(r'\d+(?:\.\d+)?', text)
            print(f"Найдено чисел: {len(numbers)}")
            print(f"Числа: {numbers}")
        """).strip()
        
        result = sandbox.execute(code)
        
        if not result["success"]:
            print(f"\n❌ STDOUT:\n{result['stdout']}")
            print(f"\n❌ STDERR:\n{result['stderr']}")
        
        assert result["success"] is True, f"Код не выполнился: {result['stderr']}"
        assert "Найдено чисел: 2" in result["stdout"]
        assert "23.5" in result["stdout"]
        assert "760" in result["stdout"]


# ============================================================
# ТЕСТЫ ОШИБОК
# ============================================================

class TestErrors:
    """Тесты обработки ошибок выполнения."""
    
    def test_division_by_zero(self, sandbox):
        """Тест ошибки деления на ноль."""
        result = sandbox.execute("print(1 / 0)")
        
        assert result["success"] is False
        assert "ZeroDivisionError" in result["stderr"]
        assert result["stdout"] == ""
    
    def test_syntax_error(self, sandbox):
        """Тест синтаксической ошибки."""
        result = sandbox.execute("print('unclosed string)")
        
        assert result["success"] is False
        assert "SyntaxError" in result["stderr"]
    
    def test_name_error(self, sandbox):
        """Тест обращения к несуществующей переменной."""
        result = sandbox.execute("print(undefined_variable)")
        
        assert result["success"] is False
        assert "NameError" in result["stderr"]
    
    def test_import_error(self, sandbox):
        """Тест импорта несуществующего модуля."""
        result = sandbox.execute("import nonexistent_module_xyz")
        
        assert result["success"] is False
        assert "ModuleNotFoundError" in result["stderr"]
    
    def test_index_error(self, sandbox):
        """Тест выхода за границы списка."""
        result = sandbox.execute("""
my_list = [1, 2, 3]
print(my_list[10])
""")
        
        assert result["success"] is False
        assert "IndexError" in result["stderr"]
    
    def test_partial_output_with_error(self, sandbox):
        """Тест, когда часть вывода успела выполниться до ошибки."""
        code = """
print("Строка 1 - успех")
print("Строка 2 - успех")
raise ValueError("Намеренная ошибка")
print("Строка 3 - не выполнится")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is False
        assert "Строка 1 - успех" in result["stdout"]
        assert "Строка 2 - успех" in result["stdout"]
        assert "Строка 3" not in result["stdout"]
        assert "ValueError" in result["stderr"]
        assert "Намеренная ошибка" in result["stderr"]


# ============================================================
# ТЕСТЫ ТАЙМАУТА
# ============================================================

class TestTimeout:
    """Тесты ограничения времени выполнения."""
    
    def test_infinite_loop_timeout(self, sandbox):
        """Тест бесконечного цикла (должен быть убит по таймауту)."""
        result = sandbox.execute("while True: pass")
        
        assert result["success"] is False
        assert "timed out" in result["stderr"].lower()
        assert result["execution_time"] >= 5  # Не меньше нашего timeout
    
    def test_sleep_timeout(self, sandbox):
        """Тест долгого sleep (должен быть убит по таймауту)."""
        result = sandbox.execute("import time; time.sleep(20)")
        
        assert result["success"] is False
        assert "timed out" in result["stderr"].lower()
    
    def test_fast_execution_no_timeout(self, sandbox):
        """Тест быстрого выполнения (не должно быть таймаута)."""
        result = sandbox.execute("print('быстро')")
        
        assert result["success"] is True
        assert result["execution_time"] < 5


# ============================================================
# ТЕСТЫ СЕТИ
# ============================================================

class TestNetwork:
    """Тесты сетевых операций."""
    
    def test_http_request(self, slow_sandbox):
        """Тест HTTP запроса к внешнему сервису."""
        code = """
import urllib.request
response = urllib.request.urlopen("https://httpbin.org/get", timeout=5)
print(f"Status: {response.status}")
"""
        result = slow_sandbox.execute(code)
        
        assert result["success"] is True
        assert "Status: 200" in result["stdout"]
    
    def test_http_request_with_json(self, slow_sandbox):
        """Тест HTTP запроса с парсингом JSON ответа."""
        code = """
import urllib.request
import json

response = urllib.request.urlopen("https://httpbin.org/get", timeout=5)
data = json.loads(response.read().decode('utf-8'))
print(f"URL получен: {data.get('url', 'unknown')}")
"""
        result = slow_sandbox.execute(code)
        
        assert result["success"] is True
        assert "URL получен:" in result["stdout"]


# ============================================================
# ТЕСТЫ ВЫЧИСЛЕНИЙ
# ============================================================

class TestComputations:
    """Тесты математических вычислений."""
    
    def test_complex_calculation(self, sandbox):
        """Тест сложных математических вычислений."""
        code = """
import math

# Площадь круга
radius = 5
area = math.pi * radius ** 2
print(f"Площадь круга: {area:.2f}")

# Факториал
fact = math.factorial(10)
print(f"10! = {fact}")

# Сумма чисел от 1 до 100
total = sum(range(1, 101))
print(f"Сумма 1..100 = {total}")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "78.54" in result["stdout"]  # pi * 25
        assert "3628800" in result["stdout"]  # 10!
        assert "5050" in result["stdout"]  # сумма 1..100
    
    def test_list_comprehension(self, sandbox):
        """Тест list comprehension и генераторов."""
        code = """
# Квадраты четных чисел от 0 до 10
squares = [x**2 for x in range(11) if x % 2 == 0]
print(f"Квадраты четных: {squares}")
print(f"Сумма: {sum(squares)}")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "[0, 4, 16, 36, 64, 100]" in result["stdout"]
        assert "220" in result["stdout"]


# ============================================================
# ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ
# ============================================================

class TestParameterized:
    """Параметризованные тесты для проверки различных сценариев."""
    
    @pytest.mark.parametrize("code,expected_output", [
        ("print(2 + 2)", "4"),
        ("print('a' * 5)", "aaaaa"),
        ("print(len([1, 2, 3, 4, 5]))", "5"),
        ("print(max(10, 20, 30))", "30"),
        ("print(min(10, 20, 30))", "10"),
    ])
    def test_simple_expressions(self, sandbox, code, expected_output):
        """Тест различных простых выражений."""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert expected_output in result["stdout"]
    
    @pytest.mark.parametrize("code,error_type", [
        ("1/0", "ZeroDivisionError"),
        ("int('abc')", "ValueError"),
        ("[][0]", "IndexError"),
        ("{}['key']", "KeyError"),
    ])
    def test_common_errors(self, sandbox, code, error_type):
        """Тест типичных ошибок Python."""
        result = sandbox.execute(code)
        
        assert result["success"] is False
        assert error_type in result["stderr"]


# ============================================================
# ТЕСТЫ СТРУКТУРЫ ВОЗВРАЩАЕМОГО СЛОВАРЯ
# ============================================================

class TestResultStructure:
    """Тесты структуры возвращаемого результата."""
    
    def test_result_has_all_keys(self, sandbox):
        """Проверка, что результат содержит все ожидаемые ключи."""
        result = sandbox.execute("print('test')")
        
        assert "success" in result
        assert "stdout" in result
        assert "stderr" in result
        assert "execution_time" in result
    
    def test_execution_time_is_float(self, sandbox):
        """Проверка, что execution_time - это float."""
        result = sandbox.execute("print('test')")
        
        assert isinstance(result["execution_time"], float)
    
    def test_stdout_is_string(self, sandbox):
        """Проверка, что stdout - это строка."""
        result = sandbox.execute("print('test')")
        
        assert isinstance(result["stdout"], str)
    
    def test_stderr_is_string(self, sandbox):
        """Проверка, что stderr - это строка."""
        result = sandbox.execute("print('test')")
        
        assert isinstance(result["stderr"], str)


# ============================================================
# INTEGRATION-STYLE ТЕСТЫ (имитация реальных сценариев)
# ============================================================

class TestRealWorldScenarios:
    """Тесты, имитирующие реальные сценарии использования Джарвисом."""
    
    def test_currency_conversion(self, sandbox):
        """Сценарий: конвертация валют (как мог бы делать Джарвис)."""
        code = """
usd_to_rub = 92.5
amount_usd = 100
amount_rub = amount_usd * usd_to_rub
print(f"{amount_usd} USD = {amount_rub:.2f} RUB")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "100 USD = 9250.00 RUB" in result["stdout"]
    
    def test_data_parsing_simulation(self, sandbox):
        """Сценарий: парсинг данных (как при работе с веб-поиском)."""
        code = """
import json

# Имитация ответа от API
raw_response = '''
{
    "results": [
        {"title": "Квантовая механика", "url": "https://wiki.org/qm"},
        {"title": "Квантовые компьютеры", "url": "https://wiki.org/qc"}
    ]
}
'''

data = json.loads(raw_response)
for r in data['results']:
    print(f"- {r['title']}: {r['url']}")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "Квантовая механика" in result["stdout"]
        assert "Квантовые компьютеры" in result["stdout"]
    
    def test_statistics_calculation(self, sandbox):
        """Сценарий: статистические расчеты."""
        code = """
import statistics

data = [23.5, 24.1, 22.8, 25.0, 23.9, 24.5, 23.2]
print(f"Среднее: {statistics.mean(data):.2f}")
print(f"Медиана: {statistics.median(data):.2f}")
print(f"Стд. откл.: {statistics.stdev(data):.2f}")
"""
        result = sandbox.execute(code)
        
        assert result["success"] is True
        assert "Среднее:" in result["stdout"]
        assert "Медиана:" in result["stdout"]
        assert "Стд. откл.:" in result["stdout"]