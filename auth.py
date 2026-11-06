"""
Authentication and Session Manager for ipTIME AX3000M Router.

Handles login, session cookie lifecycle, and JSON RPC communication with the router CGI.
"""

from typing import Any, Dict, Optional
import json
import logging
import os
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class IpTimeAuthManager:
    """Manages authentication session and HTTP communication with ipTIME AX3000M."""

    def __init__(self, config_path: str = "config.json") -> None:
        """
        Initialize the authentication manager with configuration parameters.

        Args:
            config_path: Path to the JSON configuration file.
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.base_url: str = self.config.get("router_url", "http://192.168.4.1").rstrip("/")
        self.api_endpoint: str = self.config.get("api_endpoint", "/cgi/service.cgi")
        self.api_url: str = f"{self.base_url}{self.api_endpoint}"
        self.username: str = self.config.get("username", "admin")
        self.password: str = self.config.get("password", "emdeo1004")
        self.timeout: int = int(self.config.get("request_timeout", 5))

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json; charset=UTF-8",
            "Referer": f"{self.base_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
        })
        self._is_logged_in: bool = False

    def _load_config(self) -> Dict[str, Any]:
        """Load router connection settings from local config file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file '{self.config_path}' not found. Using default parameters.")
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read config file '{self.config_path}': {e}")
            return {}

    def login(self) -> bool:
        """
        Perform administrative login against ipTIME Gen3 web service.

        Returns:
            bool: True if authentication succeeded, False otherwise.
        """
        payload = {
            "method": "session/login",
            "params": {
                "id": self.username,
                "pw": self.password
            }
        }
        try:
            response = self.session.post(
                self.api_url,
                data=json.dumps(payload),
                timeout=self.timeout
            )
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("result") == "done" or res_json.get("result") is True:
                    self._is_logged_in = True
                    logger.info("Successfully authenticated with ipTIME AX3000M router.")
                    return True
                else:
                    logger.error(f"Login rejected by router: {res_json}")
                    self._is_logged_in = False
                    return False
            else:
                logger.error(f"Router returned non-200 HTTP status: {response.status_code}")
                self._is_logged_in = False
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection failure during login: {e}")
            self._is_logged_in = False
            return False

    def is_authenticated(self) -> bool:
        """Check if session is currently active by testing system info endpoint."""
        if not self._is_logged_in:
            return False
        try:
            res = self.post("system/info", {}, auto_retry=False)
            return res.get("result") is not None
        except Exception:
            return False

    def post(self, method: str, params: Any = None, auto_retry: bool = True) -> Dict[str, Any]:
        """
        Execute JSON RPC POST request to router CGI endpoint with automatic session recovery.

        Args:
            method: API method name (e.g. 'dhcpd/lease/show', 'firewall/add').
            params: Parameters dictionary or list required by the method.
            auto_retry: If True, attempts re-login on authentication failure.

        Returns:
            Dict[str, Any]: Parsed JSON response from router.
        """
        if params is None:
            params = {}

        if not self._is_logged_in:
            if not self.login():
                return {"result": None, "error": {"code": -1, "message": "Login failed"}}

        payload = {
            "method": method,
            "params": params
        }

        try:
            response = self.session.post(
                self.api_url,
                data=json.dumps(payload),
                timeout=self.timeout
            )
            res_json = response.json()

            # Check if session expired
            if auto_retry and isinstance(res_json, dict) and res_json.get("error"):
                err_msg = str(res_json.get("error", {})).lower()
                if "session" in err_msg or "auth" in err_msg or "login" in err_msg:
                    logger.warning("Session might have expired. Attempting re-authentication...")
                    if self.login():
                        retry_resp = self.session.post(
                            self.api_url,
                            data=json.dumps(payload),
                            timeout=self.timeout
                        )
                        return retry_resp.json()

            return res_json
        except requests.exceptions.RequestException as e:
            logger.error(f"API request '{method}' failed: {e}")
            return {"result": None, "error": {"code": -2, "message": str(e)}}


if __name__ == "__main__":
    auth = IpTimeAuthManager()
    if auth.login():
        print("Login test successful!")
        sys_info = auth.post("system/info")
        print("System info:", sys_info)
    else:
        print("Login test failed.")
