#!/usr/bin/env python3
"""
多账户管理模块
"""

import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# 配置文件路径
DATA_DIR = os.path.join(os.path.expanduser("~"), ".mihoyo_checkin")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
ACCOUNTS_FILE = os.path.join(DATA_DIR, "accounts.json")


@dataclass
class Account:
    """账户数据类"""
    id: str  # 账户唯一 ID (米游社 UID)
    name: str  # 账户名称/昵称
    cookie: str  # Cookie 字符串
    created_at: str  # 创建时间
    last_sign_at: str = ""  # 最后签到时间
    enabled_games: List[str] = None  # 启用的游戏列表
    is_active: bool = True  # 是否激活

    def __post_init__(self):
        if self.enabled_games is None:
            self.enabled_games = ["genshin", "starrail", "zzz"]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        return cls(**data)


@dataclass
class AppConfig:
    """应用配置类"""
    auto_start: bool = False  # 开机自启动
    minimize_to_tray: bool = True  # 最小化到托盘
    schedule_enabled: bool = False  # 是否启用定时签到
    schedule_time: str = "08:00"  # 定时签到时间
    current_account_id: str = ""  # 当前选中的账户 ID
    theme: str = "system"  # 主题: light, dark, system
    language: str = "zh-CN"  # 语言
    notification_enabled: bool = True  # 是否启用通知

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        return cls(**data)


class AccountManager:
    """账户管理器"""

    def __init__(self):
        self._ensure_data_dir()
        self.accounts: Dict[str, Account] = {}
        self.config: AppConfig = AppConfig()
        self._load()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

    def _load(self):
        """加载数据"""
        # 加载账户
        if os.path.exists(ACCOUNTS_FILE):
            try:
                with open(ACCOUNTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for acc_data in data:
                        acc = Account.from_dict(acc_data)
                        self.accounts[acc.id] = acc
            except Exception as e:
                print(f"加载账户数据失败: {e}")

        # 加载配置
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = AppConfig.from_dict(data)
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save(self):
        """保存数据"""
        self._ensure_data_dir()

        # 保存账户
        try:
            accounts_data = [acc.to_dict() for acc in self.accounts.values()]
            with open(ACCOUNTS_FILE, "w", encoding="utf-8") as f:
                json.dump(accounts_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存账户数据失败: {e}")

        # 保存配置
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def add_account(self, account_id: str, name: str, cookie: str, enabled_games: List[str] = None) -> Account:
        """添加账户"""
        account = Account(
            id=account_id,
            name=name,
            cookie=cookie,
            created_at=datetime.now().isoformat(),
            enabled_games=enabled_games or ["genshin", "starrail", "zzz"]
        )
        self.accounts[account_id] = account
        
        # 如果没有当前账户，设置为当前账户
        if not self.config.current_account_id:
            self.config.current_account_id = account_id
        
        self.save()
        return account

    def remove_account(self, account_id: str) -> bool:
        """移除账户"""
        if account_id in self.accounts:
            del self.accounts[account_id]
            
            # 如果删除的是当前账户，切换到其他账户
            if self.config.current_account_id == account_id:
                if self.accounts:
                    self.config.current_account_id = list(self.accounts.keys())[0]
                else:
                    self.config.current_account_id = ""
            
            self.save()
            return True
        return False

    def update_account(self, account_id: str, **kwargs) -> Optional[Account]:
        """更新账户信息"""
        if account_id not in self.accounts:
            return None

        account = self.accounts[account_id]
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)

        self.save()
        return account

    def get_account(self, account_id: str) -> Optional[Account]:
        """获取账户"""
        return self.accounts.get(account_id)

    def get_current_account(self) -> Optional[Account]:
        """获取当前选中的账户"""
        if self.config.current_account_id:
            return self.accounts.get(self.config.current_account_id)
        return None

    def set_current_account(self, account_id: str) -> bool:
        """设置当前账户"""
        if account_id in self.accounts:
            self.config.current_account_id = account_id
            self.save()
            return True
        return False

    def get_all_accounts(self) -> List[Account]:
        """获取所有账户"""
        return list(self.accounts.values())

    def get_active_accounts(self) -> List[Account]:
        """获取所有激活的账户"""
        return [acc for acc in self.accounts.values() if acc.is_active]

    def update_last_sign_time(self, account_id: str):
        """更新最后签到时间"""
        if account_id in self.accounts:
            self.accounts[account_id].last_sign_at = datetime.now().isoformat()
            self.save()

    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        self.save()

    def get_config(self) -> AppConfig:
        """获取配置"""
        return self.config

    def account_exists(self, account_id: str) -> bool:
        """检查账户是否存在"""
        return account_id in self.accounts


# 签到日志
@dataclass
class SignLog:
    """签到日志"""
    account_id: str
    account_name: str
    game: str
    game_name: str
    success: bool
    message: str
    timestamp: str
    role_info: Optional[dict] = None

    def to_dict(self) -> dict:
        return asdict(self)


class SignLogManager:
    """签到日志管理器"""
    
    LOG_FILE = os.path.join(DATA_DIR, "sign_logs.json")
    MAX_LOGS = 500  # 最大保留日志数

    def __init__(self):
        self.logs: List[SignLog] = []
        self._load()

    def _load(self):
        """加载日志"""
        if os.path.exists(self.LOG_FILE):
            try:
                with open(self.LOG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.logs = [SignLog(**log) for log in data]
            except Exception:
                self.logs = []

    def save(self):
        """保存日志"""
        try:
            # 只保留最新的 MAX_LOGS 条
            if len(self.logs) > self.MAX_LOGS:
                self.logs = self.logs[-self.MAX_LOGS:]
            
            with open(self.LOG_FILE, "w", encoding="utf-8") as f:
                json.dump([log.to_dict() for log in self.logs], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存日志失败: {e}")

    def add_log(self, account_id: str, account_name: str, game: str, game_name: str,
                success: bool, message: str, role_info: dict = None):
        """添加日志"""
        log = SignLog(
            account_id=account_id,
            account_name=account_name,
            game=game,
            game_name=game_name,
            success=success,
            message=message,
            timestamp=datetime.now().isoformat(),
            role_info=role_info
        )
        self.logs.append(log)
        self.save()

    def get_logs(self, limit: int = 50, account_id: str = None) -> List[SignLog]:
        """获取日志"""
        logs = self.logs
        if account_id:
            logs = [log for log in logs if log.account_id == account_id]
        return logs[-limit:][::-1]  # 最新的在前

    def get_today_logs(self, account_id: str = None) -> List[SignLog]:
        """获取今日日志"""
        today = datetime.now().date().isoformat()
        logs = [log for log in self.logs if log.timestamp.startswith(today)]
        if account_id:
            logs = [log for log in logs if log.account_id == account_id]
        return logs[::-1]

    def clear_logs(self):
        """清空日志"""
        self.logs = []
        self.save()
