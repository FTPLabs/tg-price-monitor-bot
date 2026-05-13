import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup
from typing import Optional

logger = logging.getLogger(__name__)


class PriceMonitor:
    def __init__(self, bot, db):
        self.bot = bot
        self.db = db

    async def fetch_price(self, url: str) -> Optional[float]:
        try:
            if "wildberries.ru" in url:
                return await self._fetch_wb(url)
            elif "ozon.ru" in url:
                return await self._fetch_ozon(url)
            elif "aliexpress" in url:
                return await self._fetch_ali(url)
            else:
                return await self._fetch_generic(url)
        except Exception as e:
            logger.error(f"Ошибка получения цены для {url}: {e}")
            return None

    async def _fetch_wb(self, url: str) -> Optional[float]:
        nm_id = url.rstrip("/").split("/")[-1].replace("catalog/", "")
        api_url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&nm={nm_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                product = data["data"]["products"][0]
                price = product["salePriceU"] / 100
                return price

    async def _fetch_ozon(self, url: str) -> Optional[float]:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, "html.parser")
                price_tag = soup.find("span", {"data-widget": "webPrice"})
                if price_tag:
                    price_text = price_tag.get_text(strip=True).replace("₽", "").replace(" ", "")
                    return float(price_text)
        return None

    async def _fetch_ali(self, url: str) -> Optional[float]:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                html = await r.text()
                soup = BeautifulSoup(html, "html.parser")
                price_tag = soup.find("span", class_="product-price-value")
                if price_tag:
                    return float(price_tag.get_text(strip=True).replace(",", "").replace("RUB", "").strip())
        return None

    async def _fetch_generic(self, url: str) -> Optional[float]:
        return None

    async def check_all(self):
        tracks = self.db.get_all_active()
        for track in tracks:
            new_price = await self.fetch_price(track["url"])
            if new_price is None:
                continue

            self.db.update_price(track["id"], new_price)

            if new_price <= track["target_price"]:
                await self.bot.send_message(
                    chat_id=track["user_id"],
                    text=(
                        f"🔔 <b>Цена снизилась!</b>\n\n"
                        f"🔗 <a href='{track['url']}'>Открыть товар</a>\n"
                        f"💵 Новая цена: <b>{new_price} ₽</b>\n"
                        f"🎯 Твоя цель: <b>{track['target_price']} ₽</b>\n\n"
                        f"🛒 Самое время купить!"
                    ),
                    parse_mode="HTML",
                    disable_web_page_preview=True
                )
                self.db.deactivate(track["id"])

    async def run_periodic(self, interval: int = 1800):
        while True:
            await asyncio.sleep(interval)
            await self.check_all()
