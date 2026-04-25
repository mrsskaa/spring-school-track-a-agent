import json
import requests

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("time-server")

TIME_API_URL = "https://timeapi.io/api/Time/current/zone"


def _get_time_from_timeapi(timezone: str) -> str:
    response = requests.get(TIME_API_URL, params={"timeZone": timezone}, timeout=8)
    response.raise_for_status()
    payload = response.json()
    date = payload.get("date")
    local_time = payload.get("time")
    if not date or not local_time:
        raise ValueError("timeapi payload missing date/time")
    return f"{date} {local_time}"

@mcp.tool()
def get_local_time(timezone: str) -> str:
    try:
        if not timezone:
            return json.dumps({"error": "Не удалось определить таймзону города."}, ensure_ascii=False)
        local_time = _get_time_from_timeapi(timezone)

        response_payload = {
            "timezone": timezone,
            "local_time": local_time,
        }
        return json.dumps(response_payload, ensure_ascii=False)
    except (requests.RequestException, ValueError):
        return json.dumps({"error": "Ошибка при запросе к API времени. Попробуйте позже."}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
