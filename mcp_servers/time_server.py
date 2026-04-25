import json

import requests
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("time-server")

TIME_API_URL = "https://timeapi.io/api/Time/current/zone"


def _get_json(url: str, params: dict[str, object]) -> dict[str, object]:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_local_time(timezone: str) -> str:
    try:
        if not timezone:
            return json.dumps(
                {"error": "Не удалось определить таймзону города."},
                ensure_ascii=False,
            )

        # Получаем текущее локальное время по таймзоне из отдельного API.
        time_data = _get_json(TIME_API_URL, {"timeZone": timezone})
        local_time = time_data.get("time")
        date = time_data.get("date")
        if not local_time or not date:
            return json.dumps(
                {"error": "Не удалось получить локальное время."},
                ensure_ascii=False,
            )

        response_payload = {
            "timezone": timezone,
            "local_time": f"{date} {local_time}",
        }
        return json.dumps(response_payload, ensure_ascii=False)

    except requests.RequestException:
        return json.dumps(
            {"error": "Ошибка при запросе к API времени. Попробуйте позже."},
            ensure_ascii=False,
        )
    except (KeyError, TypeError, ValueError):
        return json.dumps(
            {"error": "Получены неожиданные данные от API времени."},
            ensure_ascii=False,
        )


if __name__ == "__main__":
    mcp.run()
