# core/tools.py
"""
Реестр инструментов (Tool Registry) для J.A.R.V.I.S.

ВАЖНО: это отдельный механизм от голосовых команд плагинов.
  - Голосовые команды  -> Registry.voice_plug_start() (точное совпадение триггера)
  - Инструменты для LLM -> ToolRegistry.execute()     (явный allowlist)

Модель НЕ может вызвать произвольный метод произвольного плагина:
выполняются только инструменты, зарегистрированные здесь.

Намеренно не реализовано в MVP (только чтение данных):
  - уровни подтверждения / permissions
  - инструменты, изменяющие файлы или выполняющие внешние действия
"""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import platform
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MAX_RESULT_CHARS = 4000
DEFAULT_TOOL_TIMEOUT = 5.0
_JSON_TYPES = {"string", "integer", "number", "boolean", "array", "object", "null"}


# --------------------------------------------------------------------------
# Валидация аргументов (минимальный JSON-Schema валидатор, без зависимостей)
# --------------------------------------------------------------------------
def _type_ok(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "null":
        return value is None
    return True


def validate_arguments(schema: Dict[str, Any], args: Any) -> Tuple[bool, Dict[str, Any], str]:
    """
    Проверяет аргументы инструмента по JSON Schema.

    Returns: (ok, cleaned_args, error_message)
    """
    if args is None:
        args = {}

    if not isinstance(args, dict):
        return False, {}, "аргументы должны быть JSON-объектом"

    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    additional = schema.get("additionalProperties", True)

    cleaned: Dict[str, Any] = {}

    # 1. обязательные поля
    for name in required:
        if name not in args or args[name] is None:
            return False, {}, f"отсутствует обязательный аргумент '{name}'"

    # 2. неизвестные поля
    for key in args:
        if key not in properties:
            if additional is False:
                return False, {}, f"неизвестный аргумент '{key}'"
            logger.debug("Пропущен неизвестный аргумент '%s'", key)
            continue

        spec = properties[key] or {}
        value = args[key]

        expected = spec.get("type")
        if expected:
            if expected not in _JSON_TYPES:
                return False, {}, f"схема содержит неподдерживаемый тип '{expected}'"
            if not _type_ok(value, expected):
                return False, {}, (
                    f"аргумент '{key}' должен иметь тип '{expected}', "
                    f"получено '{type(value).__name__}'"
                )

        enum = spec.get("enum")
        if enum and value not in enum:
            return False, {}, f"аргумент '{key}' должен быть одним из {enum}"

        cleaned[key] = value

    return True, cleaned, ""


# --------------------------------------------------------------------------
# Спецификация инструмента
# --------------------------------------------------------------------------
@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    timeout: float = DEFAULT_TOOL_TIMEOUT
    enabled: bool = True

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Хранилище и исполнитель инструментов, разрешённых для LLM."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    # -- регистрация -------------------------------------------------------
    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            logger.warning("Инструмент '%s' уже зарегистрирован — перезапись", spec.name)
        self._tools[spec.name] = spec
        logger.info("🧰 Зарегистрирован инструмент: %s", spec.name)

    def register_function(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        handler: Callable[..., Any],
        timeout: float = DEFAULT_TOOL_TIMEOUT,
    ) -> None:
        self.register(ToolSpec(name, description, parameters, handler, timeout))

    # -- запросы -----------------------------------------------------------
    def is_allowed(self, name: str) -> bool:
        spec = self._tools.get(name)
        return bool(spec and spec.enabled)

    def list_names(self) -> List[str]:
        return [n for n, s in self._tools.items() if s.enabled]

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Схемы инструментов в формате OpenAI function calling."""
        return [s.to_openai_schema() for s in self._tools.values() if s.enabled]

    def describe_for_prompt(self) -> str:
        """Текстовое описание для JSON-fallback режима."""
        lines = []
        for spec in self._tools.values():
            if not spec.enabled:
                continue
            lines.append(
                f"- {spec.name}: {spec.description}\n"
                f"  arguments JSON Schema: {json.dumps(spec.parameters, ensure_ascii=False)}"
            )
        return "\n".join(lines)

    # -- выполнение --------------------------------------------------------
    async def execute(self, name: str, arguments: Any) -> Dict[str, Any]:
        """
        Выполняет инструмент. Никогда не бросает исключение наружу.

        Returns: {"ok": bool, "tool": str, "result"|"error": ...}
        """
        if not isinstance(name, str) or not name.strip():
            return {"ok": False, "tool": name, "error": "пустое имя инструмента"}

        name = name.strip()

        if not self.is_allowed(name):
            logger.warning("🚫 Отклонён вызов неразрешённого инструмента: %s", name)
            return {
                "ok": False,
                "tool": name,
                "error": f"инструмент '{name}' не зарегистрирован или отключён",
            }

        spec = self._tools[name]

        ok, cleaned, err = validate_arguments(spec.parameters, arguments)
        if not ok:
            logger.warning("🚫 Некорректные аргументы '%s': %s", name, err)
            return {"ok": False, "tool": name, "error": f"некорректные аргументы: {err}"}

        try:
            if inspect.iscoroutinefunction(spec.handler):
                coro = spec.handler(**cleaned)
            else:
                coro = asyncio.to_thread(spec.handler, **cleaned)

            raw = await asyncio.wait_for(coro, timeout=spec.timeout)

        except asyncio.TimeoutError:
            # NOTE: asyncio.to_thread физически не прерывается; управление
            # возвращается event loop, а поток завершится самостоятельно.
            logger.error("⏱️ Тайм-аут инструмента '%s' (%.1fs)", name, spec.timeout)
            return {"ok": False, "tool": name, "error": f"тайм-аут ({spec.timeout:.0f} сек)"}
        except TypeError as e:
            logger.error("❌ Несовпадение сигнатуры '%s': %s", name, e)
            return {"ok": False, "tool": name, "error": "несовпадение сигнатуры инструмента"}
        except Exception as e:
            # traceback НЕ показываем модели и пользователю
            logger.exception("❌ Сбой инструмента '%s'", name)
            return {"ok": False, "tool": name, "error": f"сбой инструмента: {type(e).__name__}"}

        return {"ok": True, "tool": name, "result": _truncate(raw)}


def _truncate(value: Any) -> Any:
    """Ограничивает размер результата инструмента."""
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(value)

    if len(text) <= MAX_RESULT_CHARS:
        return value

    return {
        "_truncated": True,
        "note": f"результат превысил {MAX_RESULT_CHARS} символов и был обрезан",
        "preview": text[:MAX_RESULT_CHARS],
    }


# --------------------------------------------------------------------------
# Встроенные инструменты (только чтение данных)
# --------------------------------------------------------------------------
def get_time() -> Dict[str, Any]:
    """Текущие локальные дата и время."""
    now = datetime.now().astimezone()
    return {
        "time": now.strftime("%H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "weekday": now.strftime("%A"),
        "timezone": str(now.tzname()),
    }


def _cpu_info() -> Dict[str, Any]:
    info: Dict[str, Any] = {"logical_cores": os.cpu_count()}
    try:
        import psutil
        info["usage_percent"] = psutil.cpu_percent(interval=0.1)
    except Exception:
        info["usage_percent"] = None
    return info


def _memory_info() -> Dict[str, Any]:
    try:
        import psutil
        vm = psutil.virtual_memory()
        return {
            "total_gb": round(vm.total / 1024 ** 3, 2),
            "available_gb": round(vm.available / 1024 ** 3, 2),
            "percent": vm.percent,
        }
    except Exception as e:
        return {"error": f"недоступно: {type(e).__name__}"}


def _disk_info() -> Dict[str, Any]:
    try:
        root = os.path.abspath(os.sep)
        du = shutil.disk_usage(root)
        return {
            "path": root,
            "total_gb": round(du.total / 1024 ** 3, 2),
            "free_gb": round(du.free / 1024 ** 3, 2),
            "percent_used": round((du.used / du.total) * 100, 1) if du.total else None,
        }
    except Exception as e:
        return {"error": f"недоступно: {type(e).__name__}"}


def get_system_status(component: str = "all") -> Dict[str, Any]:
    """
    Состояние системы. Только безопасные stdlib/psutil вызовы.
    Никаких shell-команд.
    """
    component = (component or "all").lower()
    data: Dict[str, Any] = {}

    if component in ("all", "cpu"):
        data["cpu"] = _cpu_info()
    if component in ("all", "memory"):
        data["memory"] = _memory_info()
    if component in ("all", "disk"):
        data["disk"] = _disk_info()
    if component == "all":
        data["platform"] = {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        }
    return data


GET_TIME_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {},
    "required": [],
    "additionalProperties": False,
}

GET_SYSTEM_STATUS_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "component": {
            "type": "string",
            "enum": ["all", "cpu", "memory", "disk"],
            "description": "Какую подсистему оценить. По умолчанию 'all'.",
        }
    },
    "required": [],
    "additionalProperties": False,
}


def register_builtin_tools(tool_registry: ToolRegistry) -> None:
    """Регистрирует безопасные инструменты только для чтения."""
    tool_registry.register_function(
        name="get_time",
        description="Возвращает текущие локальные системные дату и время.",
        parameters=GET_TIME_SCHEMA,
        handler=get_time,
        timeout=2.0,
    )
    tool_registry.register_function(
        name="get_system_status",
        description=(
            "Возвращает состояние системы: загрузку CPU, память, свободное место "
            "на диске, версию ОС и Python. Только чтение, никаких shell-команд."
        ),
        parameters=GET_SYSTEM_STATUS_SCHEMA,
        handler=get_system_status,
        timeout=5.0,
    )