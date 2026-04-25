import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WEATHER_KEYWORDS = ("погода", "температура", "дождь", "осадки", "зонт", "ветер")
BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "logs" / "tool_trace.jsonl"


def is_weather_query(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in WEATHER_KEYWORDS)


def extract_city(text: str) -> str | None:
    lowered = text.lower().strip()
    if " в " in lowered:
        city = lowered.split(" в ", maxsplit=1)[1].strip(" ?!.,")
        if city:
            return city
    tokens = [token.strip(" ?!.,") for token in lowered.split() if token.strip(" ?!.,")]
    filtered = [token for token in tokens if token not in WEATHER_KEYWORDS]
    if filtered:
        return filtered[-1]
    return None


def _extract_text_content(result: object) -> str:
    content = getattr(result, "content", None)
    if not content:
        return "Пустой ответ от MCP tool."
    first_block = content[0]
    text = getattr(first_block, "text", None)
    if text:
        return text
    return str(first_block)


def write_trace(server: str, tool: str, args: dict[str, object], status: str) -> None:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "server": server,
        "tool": tool,
        "args": args,
        "status": status,
    }
    with TRACE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def call_mcp_tool(server_file: Path, tool_name: str, args: dict[str, object]) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=[str(server_file)])
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            write_trace(server_file.name, tool_name, args, "started")
            result = await session.call_tool(tool_name, args)
            write_trace(server_file.name, tool_name, args, "finished")
            return _extract_text_content(result)


def build_final_answer(weather_json: str, time_json: str) -> str:
    weather_data = json.loads(weather_json)
    time_data = json.loads(time_json)
    city_label = weather_data["city_label"]
    city_name, _, country = city_label.partition(",")
    city_name = city_name.strip()
    country = country.strip()
    city_name_in = city_name
    lowered_city = city_name.lower()
    if lowered_city.endswith("а") and len(city_name) > 1:
        city_name_in = city_name[:-1] + "е"
    location_in = f"{city_name_in}, {country}".strip(", ")
    temperature = round(float(weather_data["temperature"]), 1)
    temperature_unit = weather_data["temperature_unit"]
    wind_speed = round(float(weather_data["wind_speed"]), 1)
    wind_unit = weather_data["wind_unit"]
    precipitation = round(float(weather_data["precipitation"]), 1)
    precipitation_unit = weather_data["precipitation_unit"]
    advice = weather_data["advice"]
    local_time = time_data["local_time"]
    return (
        f"Сейчас в {location_in}: {temperature}{temperature_unit}, "
        f"ветер {wind_speed} {wind_unit}, "
        f"осадки {precipitation}{precipitation_unit}.\n"
        f"Локальное время: {local_time}.\n"
        f"Совет: {advice}"
    )


async def run_agent(query: str) -> str:
    city = extract_city(query)
    if not city:
        return 'Укажите город, например: "погода в Москве".'
    weather_server = BASE_DIR / "mcp_servers" / "weather_server.py"
    time_server = BASE_DIR / "mcp_servers" / "time_server.py"
    weather_json = await call_mcp_tool(weather_server, "get_weather", {"city": city})
    weather_data = json.loads(weather_json)
    if "error" in weather_data:
        error_text = str(weather_data["error"]).lower()
        if "не нашел город" in error_text or "не найден" in error_text:
            return 'Не удалось найти такой город. Уточните название, например: "погода в Архангельске".'
        return weather_data["error"]
    timezone = weather_data.get("timezone")
    time_json = await call_mcp_tool(time_server, "get_local_time", {"timezone": timezone})
    time_data = json.loads(time_json)
    if "error" in time_data:
        temperature = round(float(weather_data["temperature"]), 1)
        temperature_unit = weather_data["temperature_unit"]
        wind_speed = round(float(weather_data["wind_speed"]), 1)
        wind_unit = weather_data["wind_unit"]
        precipitation = round(float(weather_data["precipitation"]), 1)
        precipitation_unit = weather_data["precipitation_unit"]
        advice = weather_data["advice"]
        city_label = weather_data["city_label"]
        return (
            f"Сейчас в {city_label}: {temperature}{temperature_unit}, "
            f"ветер {wind_speed} {wind_unit}, "
            f"осадки {precipitation}{precipitation_unit}.\n"
            f"Совет: {advice}\n"
            f"(Локальное время временно недоступно: {time_data['error']})"
        )
    return build_final_answer(weather_json, time_json)


def main() -> None:
    if len(sys.argv) < 2:
        print('Использование: python main.py "погода в Москве"')
        return
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Введите непустой запрос.")
        return
    if not is_weather_query(query):
        print("Не умею, спроси про погоду.")
        return
    print(asyncio.run(run_agent(query)))


if __name__ == "__main__":
    main()
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WEATHER_KEYWORDS = ("погода", "температура", "дождь", "осадки", "зонт", "ветер")
BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "logs" / "tool_trace.jsonl"


def is_weather_query(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in WEATHER_KEYWORDS)


def extract_city(text: str) -> str | None:
    lowered = text.lower().strip()
    if " в " in lowered:
        city = lowered.split(" в ", maxsplit=1)[1].strip(" ?!.,")
        if city:
            return city
    tokens = [token.strip(" ?!.,") for token in lowered.split() if token.strip(" ?!.,")]
    filtered = [token for token in tokens if token not in WEATHER_KEYWORDS]
    if filtered:
        return filtered[-1]
    return None


def _extract_text_content(result: object) -> str:
    content = getattr(result, "content", None)
    if not content:
        return "Пустой ответ от MCP tool."
    first_block = content[0]
    text = getattr(first_block, "text", None)
    if text:
        return text
    return str(first_block)


def write_trace(server: str, tool: str, args: dict[str, object], status: str) -> None:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "server": server,
        "tool": tool,
        "args": args,
        "status": status,
    }
    with TRACE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def call_mcp_tool(server_file: Path, tool_name: str, args: dict[str, object]) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=[str(server_file)])
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            write_trace(server_file.name, tool_name, args, "started")
            result = await session.call_tool(tool_name, args)
            write_trace(server_file.name, tool_name, args, "finished")
            return _extract_text_content(result)


def build_final_answer(weather_json: str, time_json: str) -> str:
    weather_data = json.loads(weather_json)
    time_data = json.loads(time_json)
    city_label = weather_data["city_label"]
    city_name, _, country = city_label.partition(",")
    city_name = city_name.strip()
    country = country.strip()
    city_name_in = city_name
    lowered_city = city_name.lower()
    if lowered_city.endswith("а") and len(city_name) > 1:
        city_name_in = city_name[:-1] + "е"
    location_in = f"{city_name_in}, {country}".strip(", ")
    temperature = round(float(weather_data["temperature"]), 1)
    temperature_unit = weather_data["temperature_unit"]
    wind_speed = round(float(weather_data["wind_speed"]), 1)
    wind_unit = weather_data["wind_unit"]
    precipitation = round(float(weather_data["precipitation"]), 1)
    precipitation_unit = weather_data["precipitation_unit"]
    advice = weather_data["advice"]
    local_time = time_data["local_time"]
    return (
        f"Сейчас в {location_in}: {temperature}{temperature_unit}, "
        f"ветер {wind_speed} {wind_unit}, "
        f"осадки {precipitation}{precipitation_unit}.\n"
        f"Локальное время: {local_time}.\n"
        f"Совет: {advice}"
    )


async def run_agent(query: str) -> str:
    city = extract_city(query)
    if not city:
        return 'Укажите город, например: "погода в Москве".'
    weather_server = BASE_DIR / "mcp_servers" / "weather_server.py"
    time_server = BASE_DIR / "mcp_servers" / "time_server.py"
    weather_json = await call_mcp_tool(weather_server, "get_weather", {"city": city})
    weather_data = json.loads(weather_json)
    if "error" in weather_data:
        error_text = str(weather_data["error"]).lower()
        if "не нашел город" in error_text or "не найден" in error_text:
            return 'Не удалось найти такой город. Уточните название, например: "погода в Архангельске".'
        return weather_data["error"]
    timezone = weather_data.get("timezone")
    time_json = await call_mcp_tool(time_server, "get_local_time", {"timezone": timezone})
    time_data = json.loads(time_json)
    if "error" in time_data:
        temperature = round(float(weather_data["temperature"]), 1)
        temperature_unit = weather_data["temperature_unit"]
        wind_speed = round(float(weather_data["wind_speed"]), 1)
        wind_unit = weather_data["wind_unit"]
        precipitation = round(float(weather_data["precipitation"]), 1)
        precipitation_unit = weather_data["precipitation_unit"]
        advice = weather_data["advice"]
        city_label = weather_data["city_label"]
        return (
            f"Сейчас в {city_label}: {temperature}{temperature_unit}, "
            f"ветер {wind_speed} {wind_unit}, "
            f"осадки {precipitation}{precipitation_unit}.\n"
            f"Совет: {advice}\n"
            f"(Локальное время временно недоступно: {time_data['error']})"
        )
    return build_final_answer(weather_json, time_json)


def main() -> None:
    if len(sys.argv) < 2:
        print('Использование: python main.py "погода в Москве"')
        return
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Введите непустой запрос.")
        return
    if not is_weather_query(query):
        print("Не умею, спроси про погоду.")
        return
    print(asyncio.run(run_agent(query)))


if __name__ == "__main__":
    main()
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

WEATHER_KEYWORDS = ("погода", "температура", "дождь", "осадки", "зонт", "ветер")
BASE_DIR = Path(__file__).resolve().parent
TRACE_FILE = BASE_DIR / "logs" / "tool_trace.jsonl"


def is_weather_query(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in WEATHER_KEYWORDS)


def extract_city(text: str) -> str | None:
    lowered = text.lower().strip()
    if " в " in lowered:
        city = lowered.split(" в ", maxsplit=1)[1].strip(" ?!.,")
        if city:
            return city
    tokens = [token.strip(" ?!.,") for token in lowered.split() if token.strip(" ?!.,")]
    filtered = [token for token in tokens if token not in WEATHER_KEYWORDS]
    if filtered:
        return filtered[-1]
    return None


def _extract_text_content(result: object) -> str:
    content = getattr(result, "content", None)
    if not content:
        return "Пустой ответ от MCP tool."
    first_block = content[0]
    text = getattr(first_block, "text", None)
    if text:
        return text
    return str(first_block)


def write_trace(server: str, tool: str, args: dict[str, object], status: str) -> None:
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "server": server,
        "tool": tool,
        "args": args,
        "status": status,
    }
    with TRACE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


async def call_mcp_tool(server_file: Path, tool_name: str, args: dict[str, object]) -> str:
    server_params = StdioServerParameters(command=sys.executable, args=[str(server_file)])
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            write_trace(server_file.name, tool_name, args, "started")
            result = await session.call_tool(tool_name, args)
            write_trace(server_file.name, tool_name, args, "finished")
            return _extract_text_content(result)


def build_final_answer(weather_json: str, time_json: str) -> str:
    weather_data = json.loads(weather_json)
    time_data = json.loads(time_json)
    city_label = weather_data["city_label"]
    city_name, _, country = city_label.partition(",")
    city_name = city_name.strip()
    country = country.strip()
    city_name_in = city_name
    lowered_city = city_name.lower()
    if lowered_city.endswith("а") and len(city_name) > 1:
        city_name_in = city_name[:-1] + "е"
    location_in = f"{city_name_in}, {country}".strip(", ")
    temperature = round(float(weather_data["temperature"]), 1)
    temperature_unit = weather_data["temperature_unit"]
    wind_speed = round(float(weather_data["wind_speed"]), 1)
    wind_unit = weather_data["wind_unit"]
    precipitation = round(float(weather_data["precipitation"]), 1)
    precipitation_unit = weather_data["precipitation_unit"]
    advice = weather_data["advice"]
    local_time = time_data["local_time"]
    return (
        f"Сейчас в {location_in}: {temperature}{temperature_unit}, "
        f"ветер {wind_speed} {wind_unit}, "
        f"осадки {precipitation}{precipitation_unit}.\n"
        f"Локальное время: {local_time}.\n"
        f"Совет: {advice}"
    )


async def run_agent(query: str) -> str:
    city = extract_city(query)
    if not city:
        return 'Укажите город, например: "погода в Москве".'
    weather_server = BASE_DIR / "mcp_servers" / "weather_server.py"
    time_server = BASE_DIR / "mcp_servers" / "time_server.py"
    weather_json = await call_mcp_tool(weather_server, "get_weather", {"city": city})
    weather_data = json.loads(weather_json)
    if "error" in weather_data:
        error_text = str(weather_data["error"]).lower()
        if "не нашел город" in error_text or "не найден" in error_text:
            return 'Не удалось найти такой город. Уточните название, например: "погода в Архангельске".'
        return weather_data["error"]
    timezone = weather_data.get("timezone")
    time_json = await call_mcp_tool(time_server, "get_local_time", {"timezone": timezone})
    time_data = json.loads(time_json)
    if "error" in time_data:
        temperature = round(float(weather_data["temperature"]), 1)
        temperature_unit = weather_data["temperature_unit"]
        wind_speed = round(float(weather_data["wind_speed"]), 1)
        wind_unit = weather_data["wind_unit"]
        precipitation = round(float(weather_data["precipitation"]), 1)
        precipitation_unit = weather_data["precipitation_unit"]
        advice = weather_data["advice"]
        city_label = weather_data["city_label"]
        return (
            f"Сейчас в {city_label}: {temperature}{temperature_unit}, "
            f"ветер {wind_speed} {wind_unit}, "
            f"осадки {precipitation}{precipitation_unit}.\n"
            f"Совет: {advice}\n"
            f"(Локальное время временно недоступно: {time_data['error']})"
        )
    return build_final_answer(weather_json, time_json)


def main() -> None:
    if len(sys.argv) < 2:
        print('Использование: python main.py "погода в Москве"')
        return
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Введите непустой запрос.")
        return
    if not is_weather_query(query):
        print("Не умею, спроси про погоду.")
        return
    print(asyncio.run(run_agent(query)))


if __name__ == "__main__":
    main()
# Нужен для запуска асинхронных функций из обычного Python-скрипта.
import asyncio
# Нужен для работы с JSON-ответами от MCP tools.
import json
# Нужен для чтения аргументов командной строки.
import sys
# Нужен для метки времени в файле трассировки.
from datetime import datetime
# Удобная объектная работа с путями к файлам/папкам.
from pathlib import Path

# Основные объекты MCP-клиента.
from mcp import ClientSession, StdioServerParameters
# Транспорт stdio: запускаем сервер как подпроцесс и общаемся через stdin/stdout.
from mcp.client.stdio import stdio_client


# Ключевые слова, по которым считаем запрос погодным.
WEATHER_KEYWORDS = ("погода", "температура", "дождь", "осадки", "зонт", "ветер")
# Абсолютный путь к директории текущего файла (корень проекта для main.py).
BASE_DIR = Path(__file__).resolve().parent
# Путь к JSONL-файлу, где фиксируем вызовы tools.
TRACE_FILE = BASE_DIR / "logs" / "tool_trace.jsonl"


# Проверяем, относится ли пользовательский запрос к погодной теме.
def is_weather_query(text: str) -> bool:
    # Нормализуем регистр, чтобы поиск слов был нечувствителен к заглавным буквам.
    lowered = text.lower()
    # Возвращаем True, если в тексте есть хотя бы одно ключевое слово.
    return any(keyword in lowered for keyword in WEATHER_KEYWORDS)


# Извлекаем город из пользовательского запроса.
def extract_city(text: str) -> str | None:
    # Базовая нормализация: нижний регистр + обрезка пробелов по краям.
    lowered = text.lower().strip()
    # Основной сценарий: фраза вида "... в <город>".
    if " в " in lowered:
        # Берем часть после первого " в " и чистим знаки препинания.
        city = lowered.split(" в ", maxsplit=1)[1].strip(" ?!.,")
        # Если после очистки город непустой — возвращаем его.
        if city:
            return city

    # Fallback: запросы типа "погода Питер" (без предлога "в").
    # Разбиваем на токены и чистим хвостовые знаки препинания.
    tokens = [token.strip(" ?!.,") for token in lowered.split() if token.strip(" ?!.,")]
    # Убираем служебные погодные слова, чтобы остался потенциальный город.
    filtered = [token for token in tokens if token not in WEATHER_KEYWORDS]
    # Если остались слова — берем последнее как наиболее вероятное название города.
    if filtered:
        return filtered[-1]
    # Если ничего не нашли — возвращаем None, чтобы попросить пользователя уточнить город.
    return None


# Унифицируем извлечение текстового содержимого из ответа MCP.
def _extract_text_content(result: object) -> str:
    # Пробуем достать поле content (список блоков) из ответа.
    content = getattr(result, "content", None)
    # Если контент отсутствует, возвращаем диагностическое сообщение.
    if not content:
        return "Пустой ответ от MCP tool."

    # В типичном кейсе берем первый контент-блок.
    first_block = content[0]
    # У большинства блоков текст лежит в поле text.
    text = getattr(first_block, "text", None)
    # Если текст есть — возвращаем.
    if text:
        return text

    # Fallback на случай нестандартного блока: приводим его к строке.
    return str(first_block)


# Пишем один элемент трассы вызова tool-а в JSONL.
def write_trace(server: str, tool: str, args: dict[str, object], status: str) -> None:
    # Гарантируем, что папка logs существует.
    TRACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Формируем структуру одной записи трассы.
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "server": server,
        "tool": tool,
        "args": args,
        "status": status,
    }
    # Добавляем запись в конец файла (append), кодировка UTF-8 для русского текста.
    with TRACE_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


# Универсальный вызов MCP tool по файлу сервера, имени tool-а и аргументам.
async def call_mcp_tool(server_file: Path, tool_name: str, args: dict[str, object]) -> str:
    # Настраиваем запуск MCP-сервера как отдельного Python-процесса.
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

    # Открываем stdio-транспорт (каналы чтения/записи между клиентом и сервером).
    async with stdio_client(server_params) as (read_stream, write_stream):
        # Создаем MCP-сессию поверх транспортных потоков.
        async with ClientSession(read_stream, write_stream) as session:
            # Инициализируем MCP-сессию (рукопожатие протокола).
            await session.initialize()
            # Пишем отметку старта вызова в trace.
            write_trace(server_file.name, tool_name, args, "started")
            # Реально вызываем tool на стороне сервера.
            result = await session.call_tool(tool_name, args)
            # Пишем отметку завершения вызова в trace.
            write_trace(server_file.name, tool_name, args, "finished")
            # Возвращаем текстовое содержимое ответа.
            return _extract_text_content(result)


# Собираем финальный ответ пользователю из двух JSON-ответов (погода + время).
def build_final_answer(weather_json: str, time_json: str) -> str:
    # Парсим JSON от weather tool.
    weather_data = json.loads(weather_json)
    # Парсим JSON от time tool.
    time_data = json.loads(time_json)

    # Берем подпись города вида "Москва, Россия".
    city_label = weather_data["city_label"]
    # Делим подпись на город и страну.
    city_name, _, country = city_label.partition(",")
    # Чистим пробелы вокруг названия города.
    city_name = city_name.strip()
    # Чистим пробелы вокруг названия страны.
    country = country.strip()

    # Супер-минимализм: одно общее правило для формы после "в".
    city_name_in = city_name
    # Нижний регистр нужен для проверки окончания.
    lowered_city = city_name.lower()
    # Если город заканчивается на "а", преобразуем "Самара" -> "Самаре".
    if lowered_city.endswith("а") and len(city_name) > 1:
        city_name_in = city_name[:-1] + "е"
    # Финальная строка локации в контексте "Сейчас в ...".
    location_in = f"{city_name_in}, {country}".strip(", ")

    # Температура, округленная до 1 знака после запятой.
    temperature = round(float(weather_data["temperature"]), 1)
    # Единица температуры (обычно °C).
    temperature_unit = weather_data["temperature_unit"]
    # Скорость ветра, округленная до 1 знака.
    wind_speed = round(float(weather_data["wind_speed"]), 1)
    # Единица скорости ветра (обычно km/h).
    wind_unit = weather_data["wind_unit"]
    # Осадки, округленные до 1 знака.
    precipitation = round(float(weather_data["precipitation"]), 1)
    # Единица осадков (обычно mm).
    precipitation_unit = weather_data["precipitation_unit"]
    # Текстовый совет (одежда/зонт) от weather tool.
    advice = weather_data["advice"]
    # Локальное время от time tool.
    local_time = time_data["local_time"]

    # Собираем трехстрочный итоговый ответ.
    return (
        f"Сейчас в {location_in}: {temperature}{temperature_unit}, "
        f"ветер {wind_speed} {wind_unit}, "
        f"осадки {precipitation}{precipitation_unit}.\n"
        f"Локальное время: {local_time}.\n"
        f"Совет: {advice}"
    )


# Главный агентный пайплайн: извлечение города -> вызов двух tools -> сборка ответа.
async def run_agent(query: str) -> str:
    # Достаем город из пользовательского текста.
    city = extract_city(query)
    # Если город не удалось извлечь, просим пользователя указать его явно.
    if not city:
        return 'Укажите город, например: "погода в Москве".'

    # Путь к MCP weather-серверу.
    weather_server = BASE_DIR / "mcp_servers" / "weather_server.py"
    # Путь к MCP time-серверу.
    time_server = BASE_DIR / "mcp_servers" / "time_server.py"

    # Вызываем weather tool первого MCP-сервера.
    weather_json = await call_mcp_tool(weather_server, "get_weather", {"city": city})
    # Парсим weather-ответ в dict.
    weather_data = json.loads(weather_json)
    # Если weather tool вернул ошибку, обрабатываем ее.
    if "error" in weather_data:
        # Отдельно даем более дружелюбную подсказку для кейса "город не найден".
        error_text = str(weather_data["error"]).lower()
        if "не нашел город" in error_text or "не найден" in error_text:
            return 'Не удалось найти такой город. Уточните название, например: "погода в Архангельске".'
        # Остальные ошибки возвращаем как есть.
        return weather_data["error"]

    # Берем таймзону из weather-ответа для второго tool-а.
    timezone = weather_data.get("timezone")
    # Вызываем time tool второго MCP-сервера.
    time_json = await call_mcp_tool(time_server, "get_local_time", {"timezone": timezone})
    # Парсим time-ответ в dict.
    time_data = json.loads(time_json)
    # Если time tool вернул ошибку, сообщаем частичный результат.
    if "error" in time_data:
        # Показываем погоду и совет даже при сбое API времени, чтобы ответ оставался полезным.
        temperature = round(float(weather_data["temperature"]), 1)
        temperature_unit = weather_data["temperature_unit"]
        wind_speed = round(float(weather_data["wind_speed"]), 1)
        wind_unit = weather_data["wind_unit"]
        precipitation = round(float(weather_data["precipitation"]), 1)
        precipitation_unit = weather_data["precipitation_unit"]
        advice = weather_data["advice"]
        city_label = weather_data["city_label"]
        return (
            f"Сейчас в {city_label}: {temperature}{temperature_unit}, "
            f"ветер {wind_speed} {wind_unit}, "
            f"осадки {precipitation}{precipitation_unit}.\n"
            f"Совет: {advice}\n"
            f"(Локальное время временно недоступно: {time_data['error']})"
        )

    # Если оба tool-а успешны, формируем финальный человекочитаемый ответ.
    return build_final_answer(weather_json, time_json)


# CLI-вход в программу.
def main() -> None:
    # Если аргументов нет, выводим инструкцию по использованию.
    if len(sys.argv) < 2:
        print('Использование: python main.py "погода в Москве"')
        return

    # Собираем все аргументы после имени скрипта в единый текст запроса.
    query = " ".join(sys.argv[1:]).strip()
    # Защита от пустого запроса.
    if not query:
        print("Введите непустой запрос.")
        return

    # Если запрос не погодный, возвращаем fallback.
    if not is_weather_query(query):
        print("Не умею, спроси про погоду.")
        return

    # Запускаем асинхронный пайплайн и печатаем результат в консоль.
    print(asyncio.run(run_agent(query)))


# Стандартная точка входа Python-скрипта.
if __name__ == "__main__":
    main()
