import json

import requests
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("weather-server")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def _get_json(url: str, params: dict[str, object]) -> dict[str, object]:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def _city_search_variants(city: str) -> list[str]:
    variants = [city]
    cleaned = city.strip()
    if cleaned.lower().endswith("е") and len(cleaned) > 1:
        variants.append(cleaned[:-1])
    return variants


def _build_advice(temperature: float, precipitation: float) -> str:
    if temperature <= 0:
        clothes_advice = "Очень холодно - наденьте теплую куртку, шапку и перчатки."
    elif temperature <= 10:
        clothes_advice = "Прохладно - лучше надеть куртку или пальто."
    elif temperature <= 18:
        clothes_advice = "Комфортно, но свежо - подойдет легкая куртка."
    else:
        clothes_advice = "Тепло - можно одеться легко."

    if precipitation > 0:
        rain_advice = "Сейчас есть осадки, возьмите зонт."
    else:
        rain_advice = "Осадков не ожидается, зонт можно не брать."

    return f"{clothes_advice} {rain_advice}"


@mcp.tool()
def get_weather(city: str) -> str:
    try:
        results = []
        for city_variant in _city_search_variants(city):
            geo_data = _get_json(
                GEOCODING_URL,
                {
                    "name": city_variant,
                    "count": 1,
                    "language": "ru",
                    "format": "json",
                },
            )
            results = geo_data.get("results") or []
            if results:
                break

        if not results:
            return json.dumps(
                {"error": f"Не нашел город: {city}"},
                ensure_ascii=False,
            )

        place = results[0]
        latitude = place["latitude"]
        longitude = place["longitude"]
        place_name = place.get("name", city)
        country = place.get("country", "")

        weather_data = _get_json(
            FORECAST_URL,
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,wind_speed_10m,precipitation",
            },
        )

        current = weather_data.get("current")
        if not current:
            return json.dumps(
                {"error": "Не удалось получить актуальную погоду."},
                ensure_ascii=False,
            )

        temperature = float(current.get("temperature_2m"))
        wind_speed = float(current.get("wind_speed_10m"))
        precipitation = float(current.get("precipitation", 0.0))

        units = weather_data.get("current_units", {})
        response_payload = {
            "city_label": f"{place_name}, {country}".strip(", "),
            "timezone": place.get("timezone"),
            "temperature": temperature,
            "temperature_unit": units.get("temperature_2m", "°C"),
            "wind_speed": wind_speed,
            "wind_unit": units.get("wind_speed_10m", "km/h"),
            "precipitation": precipitation,
            "precipitation_unit": units.get("precipitation", "mm"),
            "advice": _build_advice(temperature, precipitation),
        }
        return json.dumps(response_payload, ensure_ascii=False)

    except requests.RequestException:
        return json.dumps(
            {"error": "Ошибка при запросе к погодному API. Попробуйте позже."},
            ensure_ascii=False,
        )
    except (KeyError, TypeError, ValueError):
        return json.dumps(
            {"error": "Получены неожиданные данные от погодного API."},
            ensure_ascii=False,
        )


if __name__ == "__main__":
    mcp.run()
