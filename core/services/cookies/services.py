from typing import Optional

from gram_core.base_service import BaseService
from gram_core.basemodel import RegionEnum
from gram_core.services.cookies.error import CookieServiceError
from gram_core.services.cookies.models import CookiesStatusEnum, CookiesDataBase as Cookies
from gram_core.services.cookies.services import (
    CookiesService,
    PublicCookiesService as BasePublicCookiesService,
    NeedContinue,
)

from simnet import GenshinClient, Region, Game
from simnet.errors import InvalidCookies, TooManyRequests, BadRequest as SimnetBadRequest, NeedChallenge

from utils.log import logger

__all__ = ("CookiesService", "PublicCookiesService")


class PublicCookiesService(BaseService, BasePublicCookiesService):
    async def initialize(self) -> None:
        logger.info("正在初始化公共Cookies池")
        await self.refresh()
        logger.success("刷新公共Cookies池成功")

    async def check_public_cookie(self, region: RegionEnum, cookies: Cookies, public_id: int):  # skipcq: PY-R1000 #
        device_id: Optional[str] = None
        device_fp: Optional[str] = None
        devices = await self.devices_repository.get(cookies.account_id)
        if devices:
            device_id = devices.device_id
            device_fp = devices.device_fp

        if region == RegionEnum.HYPERION:
            client = GenshinClient(
                cookies=cookies.data, region=Region.CHINESE, device_id=device_id, device_fp=device_fp
            )
        elif region == RegionEnum.HOYOLAB:
            client = GenshinClient(
                cookies=cookies.data, region=Region.OVERSEAS, lang="zh-cn", device_id=device_id, device_fp=device_fp
            )
        else:
            raise CookieServiceError
        try:
            if client.account_id is None:
                raise RuntimeError("account_id not found")
            record_cards = await client.get_record_cards()
            for record_card in record_cards:
                if record_card.game == Game.GENSHIN:
                    await client.get_partial_genshin_user(record_card.uid)
                    break
            else:
                accounts = await client.get_game_accounts()
                for account in accounts:
                    if account.game == Game.GENSHIN:
                        await client.get_partial_genshin_user(account.uid)
                        break
        except InvalidCookies as exc:
            if exc.ret_code in (10001, -100):
                logger.warning("用户 [%s] Cookies无效", public_id)
            elif exc.ret_code == 10103:
                logger.warning("用户 [%s] Cookies有效，但没有绑定到游戏帐户", public_id)
            else:
                logger.warning("Cookies无效 ")
                logger.exception(exc)
            cookies.status = CookiesStatusEnum.INVALID_COOKIES
            await self._repository.update(cookies)
            await self._cache.delete_public_cookies(cookies.user_id, region)
            raise NeedContinue
        except TooManyRequests:
            logger.warning("用户 [%s] 查询次数太多或操作频繁", public_id)
            cookies.status = CookiesStatusEnum.TOO_MANY_REQUESTS
            await self._repository.update(cookies)
            await self._cache.delete_public_cookies(cookies.user_id, region)
            raise NeedContinue
        except NeedChallenge:
            logger.warning("用户 [%s] 触发验证", public_id)
            await self.set_device_valid(client.account_id, False)
            await self._cache.delete_public_cookies(cookies.user_id, region)
            raise NeedContinue
        except SimnetBadRequest as exc:
            if "invalid content type" in exc.message:
                raise exc
            logger.warning("用户 [%s] 获取账号信息发生错误，错误信息为", public_id)
            logger.exception(exc)
            await self._cache.delete_public_cookies(cookies.user_id, region)
            raise NeedContinue
        except RuntimeError as exc:
            if "account_id not found" in str(exc):
                cookies.status = CookiesStatusEnum.INVALID_COOKIES
                await self._repository.update(cookies)
                await self._cache.delete_public_cookies(cookies.user_id, region)
                raise NeedContinue
            raise exc
        except Exception as exc:
            await self._cache.delete_public_cookies(cookies.user_id, region)
            raise exc
        finally:
            await client.shutdown()
