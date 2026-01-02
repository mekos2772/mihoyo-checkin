#!/usr/bin/env python3
"""
米哈游签到核心逻辑
"""

import hashlib
import json
import random
import string
import time
import uuid
from typing import Optional, Tuple, List, Dict, Callable

import requests

# ==================== 配置 ====================
GAMES = {
    "genshin": {
        "name": "原神",
        "act_id": "e202311201442471",
        "game_biz": "hk4e_cn",
        "sign_game": "hk4e",
        "sign_url": "https://api-takumi.mihoyo.com/event/luna/sign",
        "info_url": "https://api-takumi.mihoyo.com/event/luna/info",
        "home_url": "https://api-takumi.mihoyo.com/event/luna/home",
        "award_url": "https://api-takumi.mihoyo.com/event/luna/award",
        "role_url": "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie",
    },
    "starrail": {
        "name": "崩坏：星穹铁道",
        "act_id": "e202304121516551",
        "game_biz": "hkrpg_cn",
        "sign_game": "hkrpg",
        "sign_url": "https://api-takumi.mihoyo.com/event/luna/sign",
        "info_url": "https://api-takumi.mihoyo.com/event/luna/info",
        "home_url": "https://api-takumi.mihoyo.com/event/luna/home",
        "award_url": "https://api-takumi.mihoyo.com/event/luna/award",
        "role_url": "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie",
    },
    "zzz": {
        "name": "绝区零",
        "act_id": "e202406242138391",
        "game_biz": "nap_cn",
        "sign_game": "zzz",
        "sign_url": "https://api-takumi.mihoyo.com/event/luna/zzz/sign",
        "info_url": "https://api-takumi.mihoyo.com/event/luna/zzz/info",
        "home_url": "https://api-takumi.mihoyo.com/event/luna/zzz/home",
        "award_url": "https://api-takumi.mihoyo.com/event/luna/zzz/award",
        "role_url": "https://api-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie",
    },
}

# API 地址
QR_CODE_URL = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/fetch"
CHECK_QR_URL = "https://hk4e-sdk.mihoyo.com/hk4e_cn/combo/panda/qrcode/query"
GET_STOKEN_URL = "https://api-takumi.mihoyo.com/account/ma-cn-session/app/getTokenByGameToken"
GET_COOKIE_TOKEN_URL = "https://api-takumi.mihoyo.com/auth/api/getCookieAccountInfoBySToken"
GET_LTOKEN_URL = "https://passport-api.mihoyo.com/account/auth/api/getLTokenBySToken"


# ==================== 工具函数 ====================
def md5(text: str) -> str:
    """计算 MD5"""
    return hashlib.md5(text.encode()).hexdigest()


def random_string(length: int = 6) -> str:
    """生成随机字符串"""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_timestamp() -> int:
    """获取时间戳"""
    return int(time.time())


def get_ds(web: bool = True) -> str:
    """生成 DS 签名"""
    salt = "G1ktdwFL4IyGkHuuWSmz0wUe9Db9scyK" if web else "idMMaGYmVgPzh3wxmWudUXKUPGidO7GM"
    t = str(get_timestamp())
    r = random_string(6)
    c = md5(f"salt={salt}&t={t}&r={r}")
    return f"{t},{r},{c}"


def get_ds2(query: str = "", body: str = "") -> str:
    """生成 DS2 签名"""
    salt = "t0qEgfub6cvueAPgR5m9aQWWVciEer7v"
    t = str(get_timestamp())
    r = str(random.randint(100001, 200000))
    c = md5(f"salt={salt}&t={t}&r={r}&b={body}&q={query}")
    return f"{t},{r},{c}"


def get_device_id() -> str:
    """生成设备 ID"""
    return uuid.uuid4().hex


# ==================== HTTP 客户端 ====================
class MihoyoClient:
    def __init__(self, cookie: str = ""):
        self.session = requests.Session()
        self.cookie = cookie
        self.device_id = get_device_id()

    def _get_headers(self, ds_type: int = 1, referer: str = "https://act.mihoyo.com/", sign_game: str = "") -> dict:
        """获取请求头"""
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,en-US;q=0.8",
            "Accept-Encoding": "gzip, deflate",
            "User-Agent": "Mozilla/5.0 (Linux; Android 12; Unspecified Device) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/103.0.5060.129 Mobile Safari/537.36 miHoYoBBS/2.93.1",
            "x-rpc-app_version": "2.93.1",
            "x-rpc-client_type": "5",
            "x-rpc-device_id": self.device_id,
            "x-rpc-channel": "miyousheluodi",
            "X-Requested-With": "com.mihoyo.hyperion",
            "Referer": referer,
            "Origin": "https://act.mihoyo.com",
        }

        if sign_game:
            headers["x-rpc-signgame"] = sign_game

        if ds_type == 1:
            headers["DS"] = get_ds(True)
        elif ds_type == 2:
            headers["DS"] = get_ds(False)

        if self.cookie:
            headers["Cookie"] = self.cookie

        return headers

    def get(self, url: str, params: dict = None, sign_game: str = "") -> dict:
        """GET 请求"""
        resp = self.session.get(url, params=params, headers=self._get_headers(sign_game=sign_game))
        return resp.json()

    def post(self, url: str, data: dict = None, json_data: dict = None, sign_game: str = "") -> dict:
        """POST 请求"""
        resp = self.session.post(url, data=data, json=json_data, headers=self._get_headers(sign_game=sign_game))
        return resp.json()


# ==================== 二维码登录 ====================
class QRLogin:
    def __init__(self):
        self.session = requests.Session()
        self.device_id = get_device_id()
        self.device = random_string(64)
        self._stop_flag = False

    def stop(self):
        """停止登录流程"""
        self._stop_flag = True

    def _get_headers(self, body: str = "") -> dict:
        """获取请求头"""
        return {
            "x-rpc-app_version": "2.71.1",
            "DS": get_ds2(body=body),
            "x-rpc-aigis": "",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-rpc-game_biz": "bbs_cn",
            "x-rpc-sys_version": "12",
            "x-rpc-device_id": self.device_id,
            "x-rpc-device_name": "Xiaomi MI 6",
            "x-rpc-device_model": "MI 6",
            "x-rpc-app_id": "bll8iq97cem8",
            "x-rpc-client_type": "4",
            "User-Agent": "okhttp/4.9.3",
        }

    def get_qr_code(self) -> Tuple[Optional[str], Optional[str]]:
        """获取二维码"""
        body = json.dumps({"app_id": "7", "device": self.device})
        resp = self.session.post(QR_CODE_URL, data=body, headers=self._get_headers(body))
        data = resp.json()

        if data.get("retcode") != 0:
            return None, None

        url = data["data"]["url"]
        ticket = self._extract_ticket(url)
        return url, ticket

    def _extract_ticket(self, url: str) -> str:
        """从 URL 中提取 ticket"""
        if "ticket=" in url:
            start = url.index("ticket=") + 7
            end = url.find("&", start)
            if end == -1:
                end = len(url)
            return url[start:end]
        return ""

    def check_login(self, ticket: str, status_callback: Callable[[str], None] = None) -> Tuple[Optional[str], Optional[str]]:
        """检查登录状态"""
        body = json.dumps({"app_id": "7", "ticket": ticket, "device": self.device})
        self._stop_flag = False

        while not self._stop_flag:
            time.sleep(2)
            try:
                resp = self.session.post(CHECK_QR_URL, data=body, headers=self._get_headers(body))
                data = resp.json()
            except Exception:
                continue

            if data.get("retcode") != 0:
                if data.get("retcode") in [-3503, -102]:
                    continue
                return None, None

            stat = data.get("data", {}).get("stat")

            if stat == "Init":
                if status_callback:
                    status_callback("等待扫码...")
            elif stat == "Scanned":
                if status_callback:
                    status_callback("已扫码，请在手机上确认...")
            elif stat == "Confirmed":
                if status_callback:
                    status_callback("登录成功！")
                payload = data.get("data", {}).get("payload", {})
                raw = payload.get("raw", "{}")
                raw_data = json.loads(raw)
                return raw_data.get("uid"), raw_data.get("token")
            elif stat == "Expired":
                if status_callback:
                    status_callback("二维码已过期")
                return None, None

        return None, None

    def get_stoken(self, uid: str, game_token: str) -> Tuple[Optional[str], Optional[str]]:
        """获取 SToken"""
        body = json.dumps({"account_id": int(uid), "game_token": game_token})
        resp = self.session.post(GET_STOKEN_URL, data=body, headers=self._get_headers(body))
        data = resp.json()

        if data.get("retcode") != 0:
            return None, None

        mid = data.get("data", {}).get("user_info", {}).get("mid")
        stoken = data.get("data", {}).get("token", {}).get("token")
        return mid, stoken

    def get_cookie_token(self, uid: str, stoken: str, mid: str) -> Optional[str]:
        """获取 CookieToken"""
        headers = {
            "Cookie": f"stuid={uid}; stoken={stoken}; mid={mid}",
            "DS": get_ds(),
            "x-rpc-app_version": "2.93.1",
            "x-rpc-client_type": "5",
            "User-Agent": "okhttp/4.9.3",
        }
        resp = self.session.get(f"{GET_COOKIE_TOKEN_URL}?stoken={stoken}&uid={uid}", headers=headers)
        data = resp.json()

        if data.get("retcode") == 0:
            return data.get("data", {}).get("cookie_token")
        return None

    def get_ltoken(self, uid: str, stoken: str, mid: str) -> Optional[str]:
        """获取 LToken"""
        headers = {
            "Cookie": f"stuid={uid}; stoken={stoken}; mid={mid}",
            "DS": get_ds(),
            "x-rpc-app_version": "2.93.1",
            "x-rpc-client_type": "5",
            "User-Agent": "okhttp/4.9.3",
        }
        resp = self.session.get(GET_LTOKEN_URL, headers=headers)
        data = resp.json()

        if data.get("retcode") == 0:
            return data.get("data", {}).get("ltoken")
        return None

    def login(self, status_callback: Callable[[str], None] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        执行完整登录流程
        返回: (cookie, uid, nickname)
        """
        # 获取二维码
        url, ticket = self.get_qr_code()
        if not url:
            return None, None, None

        if status_callback:
            status_callback("等待扫码...")

        # 等待扫码（外部需要显示二维码）
        uid, game_token = self.check_login(ticket, status_callback)

        if not uid:
            return None, None, None

        # 获取 SToken
        mid, stoken = self.get_stoken(uid, game_token)
        if not stoken:
            return None, None, None

        # 获取 CookieToken
        cookie_token = self.get_cookie_token(uid, stoken, mid)

        # 获取 LToken
        ltoken = self.get_ltoken(uid, stoken, mid)

        # 构建完整 Cookie
        cookie_parts = [
            f"stuid={uid}",
            f"ltuid={uid}",
            f"ltuid_v2={uid}",
            f"account_id={uid}",
            f"account_id_v2={uid}",
            f"stoken={stoken}",
            f"mid={mid}",
            f"ltmid_v2={mid}",
        ]

        if cookie_token:
            cookie_parts.extend([
                f"cookie_token={cookie_token}",
                f"cookie_token_v2={cookie_token}",
                f"account_mid_v2={mid}",
            ])

        if ltoken:
            cookie_parts.extend([
                f"ltoken={ltoken}",
                f"ltoken_v2={ltoken}",
            ])

        cookie = "; ".join(cookie_parts)
        
        return cookie, uid, url

    def get_qr_url(self) -> Tuple[Optional[str], Optional[str]]:
        """获取二维码 URL 和 ticket"""
        return self.get_qr_code()


# ==================== 签到服务 ====================
class CheckinService:
    def __init__(self, cookie: str):
        self.client = MihoyoClient(cookie)
        self.cookie = cookie

    def get_game_roles(self, game: str) -> List[Dict]:
        """获取游戏角色列表"""
        config = GAMES.get(game)
        if not config:
            return []

        params = {"game_biz": config["game_biz"]}
        resp = self.client.get(config["role_url"], params)

        if resp.get("retcode") == 0:
            return resp.get("data", {}).get("list", [])
        return []

    def get_sign_info(self, game: str, region: str = "", uid: str = "") -> dict:
        """获取签到信息"""
        config = GAMES.get(game)
        if not config:
            return None

        params = {"act_id": config["act_id"], "lang": "zh-cn"}
        if region:
            params["region"] = region
        if uid:
            params["uid"] = uid

        return self.client.get(config["info_url"], params, sign_game=config.get("sign_game", ""))

    def get_rewards(self, game: str) -> List[Dict]:
        """获取奖励列表"""
        config = GAMES.get(game)
        if not config:
            return []

        params = {"act_id": config["act_id"], "lang": "zh-cn"}
        resp = self.client.get(config["home_url"], params)

        if resp.get("retcode") == 0:
            return resp.get("data", {}).get("awards", [])
        return []

    def sign(self, game: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        执行签到
        返回: (成功, 消息, 角色信息)
        """
        config = GAMES.get(game)
        if not config:
            return False, "游戏不存在", None

        sign_game = config.get("sign_game", "")

        # 获取游戏角色
        roles = self.get_game_roles(game)
        if not roles:
            return False, "未查询到游戏角色", None

        # 使用第一个角色
        role = roles[0]
        region = role.get("region", "")
        uid = role.get("game_uid", "")
        nickname = role.get("nickname", "未知")
        level = role.get("level", 0)

        role_info = {
            "nickname": nickname,
            "uid": uid,
            "region": region,
            "level": level
        }

        # 检查签到状态
        info_resp = self.get_sign_info(game, region, uid)
        if info_resp.get("retcode") != 0:
            return False, info_resp.get("message", "获取签到信息失败"), role_info

        info = info_resp.get("data", {})
        if info.get("is_sign"):
            return True, f"今日已签到 (第{info.get('total_sign_day', 0)}天)", role_info

        # 执行签到
        data = {
            "act_id": config["act_id"],
            "lang": "zh-cn",
            "region": region,
            "uid": uid
        }
        resp = self.client.post(config["sign_url"], json_data=data, sign_game=sign_game)

        if resp.get("retcode") == 0:
            # 获取奖励信息
            rewards = self.get_rewards(game)
            day = info.get("total_sign_day", 0) + 1
            if rewards and day <= len(rewards):
                reward = rewards[day - 1]
                return True, f"签到成功！获得「{reward.get('name')}」x{reward.get('cnt')}", role_info
            return True, "签到成功！", role_info
        else:
            return False, resp.get("message", "签到失败"), role_info

    def sign_all(self, games: List[str] = None) -> Dict[str, Dict]:
        """签到所有游戏"""
        if games is None:
            games = list(GAMES.keys())

        results = {}
        for game in games:
            if game in GAMES:
                success, message, role_info = self.sign(game)
                results[game] = {
                    "success": success,
                    "message": message,
                    "role_info": role_info,
                    "game_name": GAMES[game]["name"]
                }
                time.sleep(3)  # 避免请求过快

        return results

    def get_user_info(self) -> Optional[Dict]:
        """获取用户信息"""
        all_roles = {}
        for game_key, game_config in GAMES.items():
            roles = self.get_game_roles(game_key)
            if roles:
                all_roles[game_key] = {
                    "name": game_config["name"],
                    "roles": roles
                }
        return all_roles if all_roles else None
