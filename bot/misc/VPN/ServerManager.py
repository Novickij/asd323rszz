import logging
from typing import Optional, Dict, Any, List

from bot.database.models.main import Servers
from bot.misc.VPN.Xui.Vless import Vless  # Проверяем правильность пути

log = logging.getLogger(__name__)

class ServerManager:
    class VPN:
        def __init__(self, name: str):
            self.NAME_VPN = name

    VPN_TYPES = {
        "vless": VPN("VLESS"),
        "vmess": VPN("VMESS"),
        "trojan": VPN("TROJAN"),
        "shadowsocks": VPN("SHADOWSOCKS"),
    }

    def __init__(self, server: Servers):
        self.server = server
        self.vpn = None

    async def login(self) -> bool:
        try:
            if self.server.panel == "sanaei":
                # Проверяем наличие всех необходимых атрибутов
                if not all(hasattr(self.server.vds_table, attr) for attr in ['ip', 'port']):
                    raise AttributeError("Missing required attributes in vds_table")
                self.vpn = Vless(
                    ip=self.server.vds_table.ip,
                    port=self.server.vds_table.port,
                    username=self.server.login,
                    password=self.server.password,
                    https=self.server.https
                )
                # Используем run_sync для корректной обработки синхронных вызовов внутри Vless.login()
                from sqlalchemy.ext.asyncio import async_context
                from greenlet import greenlet_spawn
                success = await async_context.run_sync(lambda: greenlet_spawn(self.vpn.login).wait())
                if not success:
                    log.error(f"Failed to login to server {self.server.id}")
                    self.vpn = None  # Сбрасываем, если логин не удался
                return success
            else:
                log.error(f"Unsupported panel type: {self.server.panel}")
                return False
        except AttributeError as e:
            log.error(f"Error during login to server {self.server.id}: {e}")
            self.vpn = None
            return False
        except Exception as e:
            log.error(f"Error during login to server {self.server.id}: {e}")
            self.vpn = None
            return False

    async def get_all_user(self) -> Optional[List[Dict[str, Any]]]:
        try:
            if not self.vpn:
                if not await self.login():
                    return None
            users = await self.vpn.get_all_user()
            return users
        except Exception as e:
            log.error(f"Failed to get users from server {self.server.id}: {e}")
            return None

    async def enable_client(self, user_tgid: int, key_id: int) -> bool:
        try:
            if not self.vpn:
                if not await self.login():
                    return False
            email = f"{user_tgid}.{key_id}"
            success = await self.vpn.enable_client(email)
            if success:
                log.info(f"Enabled client {email} on server {self.server.id}")
            else:
                log.warning(f"Failed to enable client {email} on server {self.server.id}")
            return success
        except Exception as e:
            log.error(f"Error enabling client {email} on server {self.server.id}: {e}")
            return False

    async def disable_client(self, user_tgid: int, key_id: int) -> bool:
        try:
            if not self.vpn:
                if not await self.login():
                    return False
            email = f"{user_tgid}.{key_id}"
            success = await self.vpn.disable_client(email)
            if success:
                log.info(f"Disabled client {email} on server {self.server.id}")
            else:
                log.warning(f"Failed to disable client {email} on server {self.server.id}")
            return success
        except Exception as e:
            log.error(f"Error disabling client {email} on server {self.server.id}: {e}")
            return False

    async def get_key(self, name: str, name_key: str, key_id: int) -> Optional[str]:
        try:
            if not self.vpn:
                if not await self.login():
                    return None
            key = await self.vpn.get_key(name, name_key, key_id)
            return key
        except Exception as e:
            log.error(f"Error getting key for server {self.server.id}: {e}")
            return None

    async def add_client(self, user_tgid: int, key_id: int) -> bool:
        try:
            if not self.vpn:
                if not await self.login():
                    return False
            email = f"{user_tgid}.{key_id}"
            success = await self.vpn.add_client(
                email=email,
                flow="xtls-rprx-vision",
                limit_ip=self.server.limit_ip,
                total_GB=self.server.total_GB
            )
            if success:
                log.info(f"Added client {email} to server {self.server.id}")
            else:
                log.warning(f"Failed to add client {email} to server {self.server.id}")
            return success
        except Exception as e:
            log.error(f"Error adding client {email} to server {self.server.id}: {e}")
            return False

    async def delete_client(self, user_tgid: int, key_id: int) -> bool:
        try:
            if not self.vpn:
                if not await self.login():
                    return False
            email = f"{user_tgid}.{key_id}"
            success = await self.vpn.delete_client(email)
            if success:
                log.info(f"Deleted client {email} from server {self.server.id}")
            else:
                log.warning(f"Failed to delete client {email} from server {self.server.id}")
            return success
        except Exception as e:
            log.error(f"Error deleting client {email} from server {self.server.id}: {e}")
            return False

    async def restart_app(self) -> bool:
        try:
            if not self.vpn:
                if not await self.login():
                    return False
            success = await self.vpn.restart_app()
            if success:
                log.info(f"Restarted app on server {self.server.id}")
            else:
                log.warning(f"Failed to restart app on server {self.server.id}")
            return success
        except Exception as e:
            log.error(f"Error restarting app on server {self.server.id}: {e}")
            return False