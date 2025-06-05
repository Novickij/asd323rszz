import logging

from bot.misc.VPN.Xui.Vless import Vless
from bot.misc.VPN.Xui.Shadowsocks import Shadowsocks
from bot.misc.VPN.Outline import Outline
from bot.misc.util import CONFIG

log = logging.getLogger(__name__)


class ServerManager:
    VPN_TYPES = {0: Outline, 1: Vless, 2: Shadowsocks}

    def __init__(self, server):
        try:
            self.client = self.VPN_TYPES.get(server.type_vpn)(server)
        except Exception as e:
            print(e, 'ServerManager.py Line 13')

    async def login(self):
        await self.client.login()

    async def get_all_user(self):
        try:
            return await self.client.get_all_user_server()
        except Exception as e:
            log.error(e, 'Error get all user server')

    async def get_user(self, name, key_id):
        try:
            name_str = f'{name}.{key_id}'
            return await self.client.get_client(str(name_str))
        except Exception as e:
            log.error(e, 'Error get user server')

    async def add_client(
            self,
            name,
            key_id,
            limit_ip=CONFIG.limit_ip,
            limit_gb=CONFIG.limit_GB
    ):
        try:
            name_str = f'{name}.{key_id}'
            return await self.client.add_client(str(name_str), limit_ip, limit_gb)
        except Exception as e:
            log.error(e, 'Error add client server')

    async def delete_client(self, name, key_id):
        try:
            name_str = f'{name}.{key_id}'
            await self.client.delete_client(str(name_str))
            return True
        except Exception as e:
            log.error(e, 'Error delete client server')
            return False

    async def get_key(self, name, name_key, key_id):
        try:
            name_str = f'{name}.{key_id}'
            name_key = CONFIG.name + ' | ' + name_key
            return await self.client.get_key_user(str(name_str), str(name_key))
        except Exception as e:
            log.error(e, 'get key server')
