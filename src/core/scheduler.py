#!/usr/bin/env python3
"""
定时任务和自启动模块
"""

import os
import sys
import time
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional
import winreg


class AutoStart:
    """Windows 开机自启动管理"""
    
    APP_NAME = "MihoyoCheckin"
    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    @classmethod
    def get_exe_path(cls) -> str:
        """获取当前程序路径"""
        if getattr(sys, 'frozen', False):
            # 打包后的 exe
            return sys.executable
        else:
            # 开发模式
            return sys.executable
    
    @classmethod
    def is_enabled(cls) -> bool:
        """检查是否已设置自启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REG_PATH,
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, cls.APP_NAME)
                return True
            except WindowsError:
                return False
            finally:
                winreg.CloseKey(key)
        except WindowsError:
            return False
    
    @classmethod
    def enable(cls) -> bool:
        """启用自启动"""
        try:
            exe_path = cls.get_exe_path()
            # 添加 --minimized 参数使程序启动时最小化到托盘
            command = f'"{exe_path}" --minimized'
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REG_PATH,
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, cls.APP_NAME, 0, winreg.REG_SZ, command)
            winreg.CloseKey(key)
            return True
        except WindowsError as e:
            print(f"启用自启动失败: {e}")
            return False
    
    @classmethod
    def disable(cls) -> bool:
        """禁用自启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                cls.REG_PATH,
                0,
                winreg.KEY_SET_VALUE
            )
            try:
                winreg.DeleteValue(key, cls.APP_NAME)
            except WindowsError:
                pass  # 值不存在
            winreg.CloseKey(key)
            return True
        except WindowsError as e:
            print(f"禁用自启动失败: {e}")
            return False
    
    @classmethod
    def set_enabled(cls, enabled: bool) -> bool:
        """设置自启动状态"""
        if enabled:
            return cls.enable()
        else:
            return cls.disable()


class Scheduler:
    """定时任务调度器"""
    
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable] = None
        self._schedule_time: str = "08:00"  # 默认时间 HH:MM
        self._last_run_date: Optional[str] = None
        self._lock = threading.Lock()
    
    def set_callback(self, callback: Callable):
        """设置定时任务回调函数"""
        self._callback = callback
    
    def set_schedule_time(self, time_str: str):
        """设置定时时间 (HH:MM 格式)"""
        # 验证时间格式
        try:
            datetime.strptime(time_str, "%H:%M")
            self._schedule_time = time_str
        except ValueError:
            raise ValueError(f"无效的时间格式: {time_str}，请使用 HH:MM 格式")
    
    def get_schedule_time(self) -> str:
        """获取定时时间"""
        return self._schedule_time
    
    def _get_next_run_time(self) -> datetime:
        """计算下次运行时间"""
        now = datetime.now()
        hour, minute = map(int, self._schedule_time.split(":"))
        
        # 今天的定时时间
        scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 如果今天的时间已过，则安排到明天
        if scheduled_time <= now:
            scheduled_time += timedelta(days=1)
        
        return scheduled_time
    
    def _should_run_today(self) -> bool:
        """检查今天是否应该运行"""
        today = datetime.now().date().isoformat()
        return self._last_run_date != today
    
    def _run_loop(self):
        """定时任务循环"""
        while self._running:
            try:
                now = datetime.now()
                hour, minute = map(int, self._schedule_time.split(":"))
                
                # 检查是否到达定时时间
                if (now.hour == hour and 
                    now.minute == minute and 
                    self._should_run_today()):
                    
                    with self._lock:
                        self._last_run_date = now.date().isoformat()
                    
                    # 执行回调
                    if self._callback:
                        try:
                            self._callback()
                        except Exception as e:
                            print(f"定时任务执行失败: {e}")
                
                # 每 30 秒检查一次
                time.sleep(30)
            except Exception as e:
                print(f"定时任务循环错误: {e}")
                time.sleep(60)
    
    def start(self):
        """启动定时任务"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"定时任务已启动，每天 {self._schedule_time} 执行")
    
    def stop(self):
        """停止定时任务"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        print("定时任务已停止")
    
    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
    
    def get_next_run_time(self) -> str:
        """获取下次运行时间的字符串表示"""
        next_time = self._get_next_run_time()
        return next_time.strftime("%Y-%m-%d %H:%M")
    
    def run_now(self):
        """立即执行一次"""
        if self._callback:
            threading.Thread(target=self._callback, daemon=True).start()


class SchedulerManager:
    """定时任务管理器（整合账户和签到）"""
    
    def __init__(self, account_manager, sign_callback: Callable):
        """
        初始化
        :param account_manager: 账户管理器实例
        :param sign_callback: 签到回调函数，参数为 (account_id, results)
        """
        self.account_manager = account_manager
        self.sign_callback = sign_callback
        self.scheduler = Scheduler()
        self.scheduler.set_callback(self._do_scheduled_sign)
        
        # 从配置加载设置
        config = account_manager.get_config()
        self.scheduler.set_schedule_time(config.schedule_time)
        
        if config.schedule_enabled:
            self.scheduler.start()
    
    def _do_scheduled_sign(self):
        """执行定时签到"""
        from .checkin import CheckinService
        
        # 获取所有激活的账户
        accounts = self.account_manager.get_active_accounts()
        
        for account in accounts:
            try:
                service = CheckinService(account.cookie)
                results = service.sign_all(account.enabled_games)
                
                # 更新最后签到时间
                self.account_manager.update_last_sign_time(account.id)
                
                # 调用回调
                if self.sign_callback:
                    self.sign_callback(account.id, results)
                
                # 账户之间间隔
                time.sleep(5)
            except Exception as e:
                print(f"账户 {account.name} 签到失败: {e}")
    
    def update_schedule(self, enabled: bool, time_str: str = None):
        """更新定时设置"""
        if time_str:
            self.scheduler.set_schedule_time(time_str)
            self.account_manager.update_config(schedule_time=time_str)
        
        if enabled:
            if not self.scheduler.is_running():
                self.scheduler.start()
        else:
            self.scheduler.stop()
        
        self.account_manager.update_config(schedule_enabled=enabled)
    
    def get_status(self) -> dict:
        """获取定时任务状态"""
        return {
            "enabled": self.scheduler.is_running(),
            "schedule_time": self.scheduler.get_schedule_time(),
            "next_run": self.scheduler.get_next_run_time() if self.scheduler.is_running() else None
        }
    
    def sign_now(self):
        """立即执行签到"""
        self.scheduler.run_now()
