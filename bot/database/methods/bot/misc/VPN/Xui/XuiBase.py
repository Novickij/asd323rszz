from abc import ABC

from pyxui_async import XUI

from bot.misc.VPN.BaseVpn import BaseVpn


class XuiBase(BaseVpn, ABC):

    NAME_VPN: str

    def __init__(self, server):
        adress = server.ip.split(':')
        adress_port = f'{adress[0]}:{adress[1]}'
        if server.connection_method:
            full_address = f'https://{adress_port}'
        else:
            full_address = f'http://{adress_port}'
        self.adress = f'{adress[0]}'
        self.xui = XUI(
            full_address=full_address,
            panel=server.panel,
            https=server.connection_method
        )
        self.inbound_id = int(server.inbound_id)
        self.login_user = server.login
        self.password = server.password

    async def login(self):
        await self.xui.login(username=self.login_user, password=self.password)

    async def get_inbound_server(self):
        try:
            info = await self.xui.get_inbounds()
            obj = info['obj']
            for inbound in obj:
                if inbound['id'] == self.inbound_id:
                    return inbound
        except IndexError:
            return "Error inbound"

    async def get_all_user_server(self):
        try:
            inbound_server = await self.get_inbound_server()
            return inbound_server.get('clientStats')
        except IndexError:
            return "Error inbound"
