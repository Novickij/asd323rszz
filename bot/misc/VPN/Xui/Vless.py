import json
import logging
from typing import Optional, Dict, Any, List

import aiohttp

log = logging.getLogger(__name__)

class Vless:
    def __init__(self, ip: str, port: int, username: str, password: str, https: bool):
        self.ip = ip
        self.port = port
        self.username = username
        self.password = password
        self.protocol = "https" if https else "http"
        self.session = None
        self.base_url = f"{self.protocol}://{self.ip}:{self.port}"

    async def login(self) -> bool:
        try:
            self.session = aiohttp.ClientSession()
            url = f"{self.base_url}/login"
            data = {"username": self.username, "password": self.password}
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    log.error(f"Failed to login to {self.base_url}: Status {response.status}")
                    return False
                result = await response.json()
                if not result.get("success"):
                    log.error(f"Login failed: {result.get('msg')}")
                    return False
                log.info(f"Successfully logged in to {self.base_url}")
                return True
        except Exception as e:
            log.error(f"Error during login to {self.base_url}: {e}")
            return False

    async def get_all_user(self) -> Optional[List[Dict[str, Any]]]:
        try:
            url = f"{self.base_url}/panel/api/inbounds/list"
            async with self.session.get(url) as response:
                if response.status != 200:
                    log.error(f"Failed to get users from {self.base_url}: Status {response.status}")
                    return None
                data = await response.json()
                if not data.get("success"):
                    log.error(f"Failed to get users: {data.get('msg')}")
                    return None
                users = []
                for obj in data.get("obj", []):
                    for client in obj.get("clientStats", []):
                        users.append(client)
                return users
        except Exception as e:
            log.error(f"Error getting users from {self.base_url}: {e}")
            return None

    async def enable_client(self, email: str) -> bool:
        try:
            url = f"{self.base_url}/panel/api/inbounds/updateClient/{email}"
            data = {"enable": True}
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    log.error(f"Failed to enable client {email}: Status {response.status}")
                    return False
                result = await response.json()
                if not result.get("success"):
                    log.error(f"Failed to enable client {email}: {result.get('msg')}")
                    return False
                return True
        except Exception as e:
            log.error(f"Error enabling client {email}: {e}")
            return False

    async def disable_client(self, email: str) -> bool:
        try:
            url = f"{self.base_url}/panel/api/inbounds/updateClient/{email}"
            data = {"enable": False}
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    log.error(f"Failed to disable client {email}: Status {response.status}")
                    return False
                result = await response.json()
                if not result.get("success"):
                    log.error(f"Failed to disable client {email}: {result.get('msg')}")
                    return False
                return True
        except Exception as e:
            log.error(f"Error disabling client {email}: {e}")
            return False

    async def add_client(self, email: str, flow: str, limit_ip: int, total_GB: int) -> bool:
        try:
            url = f"{self.base_url}/panel/api/inbounds/addClient"
            data = {
                "id": 1,
                "settings": json.dumps({
                    "clients": [{
                        "email": email,
                        "flow": flow,
                        "limitIp": limit_ip,
                        "totalGB": total_GB,
                        "enable": True
                    }]
                })
            }
            async with self.session.post(url, json=data) as response:
                if response.status != 200:
                    log.error(f"Failed to add client {email}: Status {response.status}")
                    return False
                result = await response.json()
                if not result.get("success"):
                    log.error(f"Failed to add client {email}: {result.get('msg')}")
                    return False
                return True
        except Exception as e:
            log.error(f"Error adding client {email}: {e}")
            return False

    async def delete_client(self, email: str) -> bool:
        try:
            url = f"{self.base_url}/panel/api/inbounds/deleteClient/{email}"
            async with self.session.post(url) as response:
                if response.status != 200:
                    log.error(f"Failed to delete client {email}: Status {response.status}")
                    return False
                result = await response.json()
                if not result.get("success"):
                    log.error(f"Failed to delete client {email}: {result.get('msg')}")
                    return False
                return True
        except Exception as e:
            log.error(f"Error deleting client {email}: {e}")
            return False

    async def get_key(self, name: str, name_key: str, key_id: int) -> Optional[str]:
        try:
            url = f"{self.base_url}/panel/api/inbounds/list"
            async with self.session.get(url) as response:
                if response.status != 200:
                    log.error(f"Failed to get keys from {self.base_url}: Status {response.status}")
                    return None
                data = await response.json()
                if not data.get("success"):
                    log.error(f"Failed to get keys: {data.get('msg')}")
                    return None
                for obj in data.get("obj", []):
                    settings = json.loads(obj.get("settings", "{}"))
                    for client in settings.get("clients", []):
                        if client.get("email") == f"{name}.{key_id}":
                            link = f"vless://{client['id']}@{self.ip}:{obj['port']}?type=tcp&security=none&flow={client['flow']}#{name_key}"
                            return link
                return None
        except Exception as e:
            log.error(f"Error getting key for {name}.{key_id}: {e}")
            return None

    async def restart_app(self) -> bool:
        try:
            url = f"{self.base_url}/panel/api/system/restart"
            async with self.session.post(url) as response:
                if response.status != 200:
                    log.error(f"Failed to restart app on {self.base_url}: Status {response.status}")
                    return False
                result = await response.json()
                if not result.get("success"):
                    log.error(f"Failed to restart app: {result.get('msg')}")
                    return False
                return True
        except Exception as e:
            log.error(f"Error restarting app on {self.base_url}: {e}")
            return False