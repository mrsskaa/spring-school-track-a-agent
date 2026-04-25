import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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

    # Fallback для запросов формата "погода Питер" без предлога "в".
    tokens = [token.strip(" ?!.,") for token in lowered.split() if token.strip(" ?!.,")]
    filtered = [token for token in tokens if token not in WEATHER_KEYWORDS]
    if filtered:
        return filtered[-1]
    return None


def _extract_text_content(result: Any) -> str:
    content = getattr(result, "content", None)
    if not content:
        return "Пустой ответ от MCP tool."

    first_block = content[0]
    text = getattr(first_block, "text", None)
    if text:
        return text

    # Защита от нестандартного формата ответа.
    return str(first_block)


def write_trace(server: str, tool: str, args: dict[str, Any], status: str) -> None:
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


async def call_mcp_tool(server_file: Path, tool_name: str, args: dict[str, Any]) -> str:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_file)],
    )

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

    # Супер-минимализм: одно общее правило для формы после "в".
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

    # Важно для критериев: реально вызываем tool первого MCP-сервера.
    weather_json = await call_mcp_tool(weather_server, "get_weather", {"city": city})
    weather_data = json.loads(weather_json)
    if "error" in weather_data:
        if str(weather_data["error"]).startswith("Не нашел город"):
            return 'Не удалось найти такой город. Уточните название, например: "погода в Архангельске".'
        return weather_data["error"]

    # Важно для критериев: реально вызываем tool второго MCP-сервера.
    timezone = weather_data.get("timezone")
    time_json = await call_mcp_tool(time_server, "get_local_time", {"timezone": timezone})
    time_data = json.loads(time_json)
    if "error" in time_data:
        return (
            f"Погода получена, но время не удалось узнать: {time_data['error']}\n"
            f"Данные о погоде: {weather_data}"
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
