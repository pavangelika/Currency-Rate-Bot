import aiohttp

from logger.logging_settings import logger


async def get_city_by_coordinates(latitude: float, longitude: float) -> str:
    url = f"https://us1.api-bdc.net/data/reverse-geocode-client?latitude={latitude}&longitude={longitude}&localityLanguage=ru"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                logger.info(f"get_city_by_coordinates: {data}")
                return data
                # return data.get("city", "Неизвестный город")
            else:
                return "Не удалось определить город"
