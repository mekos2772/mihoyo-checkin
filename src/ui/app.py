#!/usr/bin/env python3
"""
米哈游签到工具 - 主界面
使用 Flet 框架实现 WinUI3 风格界面
"""

import flet as ft
import threading
import io
from datetime import datetime
from typing import Optional

try:
    import qrcode
    from PIL import Image
    import base64
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (
    CheckinService, QRLogin, GAMES,
    AccountManager, Account, SignLogManager,
    AutoStart, SchedulerManager
)


class MihoyoCheckinApp:
    """米哈游签到应用主类"""
    
    def __init__(self, page: ft.Page):
        self.page = page
        self.account_manager = AccountManager()
        self.log_manager = SignLogManager()
        self.scheduler_manager: Optional[SchedulerManager] = None
        self.qr_login: Optional[QRLogin] = None
        self.current_qr_url: Optional[str] = None
        
        self._setup_page()
        self._init_scheduler()
        self._build_ui()
    
    def _setup_page(self):
        """设置页面属性"""
        self.page.title = "米哈游自动签到"
        self.page.window.width = 900
        self.page.window.height = 650
        self.page.window.min_width = 800
        self.page.window.min_height = 600
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.padding = 0
        
        # WinUI3 风格主题
        self.page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.BLUE,
            visual_density=ft.VisualDensity.COMFORTABLE,
        )
    
    def _init_scheduler(self):
        """初始化定时任务"""
        def on_sign_complete(account_id: str, results: dict):
            # 记录日志
            account = self.account_manager.get_account(account_id)
            if account:
                for game_key, result in results.items():
                    self.log_manager.add_log(
                        account_id=account_id,
                        account_name=account.name,
                        game=game_key,
                        game_name=result.get("game_name", ""),
                        success=result.get("success", False),
                        message=result.get("message", ""),
                        role_info=result.get("role_info")
                    )
            # 刷新界面
            if hasattr(self, 'home_view'):
                self.page.run_thread(self._refresh_home)
        
        self.scheduler_manager = SchedulerManager(
            self.account_manager,
            on_sign_complete
        )
    
    def _refresh_home(self):
        """刷新首页"""
        self._update_home_content()
        self.page.update()
    
    def _build_ui(self):
        """构建界面"""
        # 导航栏
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="首页",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                    selected_icon=ft.Icons.ACCOUNT_CIRCLE,
                    label="账户",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SCHEDULE_OUTLINED,
                    selected_icon=ft.Icons.SCHEDULE,
                    label="定时",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.HISTORY_OUTLINED,
                    selected_icon=ft.Icons.HISTORY,
                    label="日志",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="设置",
                ),
            ],
            on_change=self._on_nav_change,
        )
        
        # 内容区域
        self.content_area = ft.Container(
            expand=True,
            padding=20,
        )
        
        # 主布局
        self.page.add(
            ft.Row(
                [
                    self.nav_rail,
                    ft.VerticalDivider(width=1),
                    self.content_area,
                ],
                expand=True,
            )
        )
        
        # 显示首页
        self._show_home()
    
    def _on_nav_change(self, e):
        """导航切换"""
        index = e.control.selected_index
        if index == 0:
            self._show_home()
        elif index == 1:
            self._show_accounts()
        elif index == 2:
            self._show_schedule()
        elif index == 3:
            self._show_logs()
        elif index == 4:
            self._show_settings()
    
    # ==================== 首页 ====================
    def _show_home(self):
        """显示首页"""
        self._update_home_content()
    
    def _update_home_content(self):
        """更新首页内容"""
        account = self.account_manager.get_current_account()
        
        if not account:
            # 无账户提示
            self.content_area.content = ft.Column(
                [
                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, size=80, color=ft.Colors.GREY_400),
                    ft.Text("尚未添加账户", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text("请先添加米游社账户以使用签到功能", color=ft.Colors.GREY_600),
                    ft.ElevatedButton(
                        "添加账户",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: self._show_add_account_dialog(),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        else:
            # 显示账户信息和签到按钮
            games_cards = []
            for game_key, game_info in GAMES.items():
                enabled = game_key in (account.enabled_games or [])
                games_cards.append(
                    self._create_game_card(game_key, game_info["name"], enabled, account)
                )
            
            # 获取今日签到状态
            today_logs = self.log_manager.get_today_logs(account.id)
            signed_games = {log.game for log in today_logs if log.success}
            
            self.content_area.content = ft.Column(
                [
                    # 账户信息卡片
                    ft.Card(
                        content=ft.Container(
                            content=ft.Row(
                                [
                                    ft.CircleAvatar(
                                        content=ft.Text(account.name[0] if account.name else "?"),
                                        bgcolor=ft.Colors.BLUE_400,
                                        radius=30,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(account.name, size=18, weight=ft.FontWeight.BOLD),
                                            ft.Text(f"UID: {account.id}", color=ft.Colors.GREY_600),
                                            ft.Text(
                                                f"最后签到: {account.last_sign_at[:10] if account.last_sign_at else '从未'}", 
                                                color=ft.Colors.GREY_500,
                                                size=12
                                            ),
                                        ],
                                        spacing=2,
                                    ),
                                    ft.Container(expand=True),
                                    ft.ElevatedButton(
                                        "一键签到",
                                        icon=ft.Icons.CHECK_CIRCLE,
                                        on_click=lambda _: self._do_sign_all(account),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                            ),
                            padding=20,
                        ),
                    ),
                    ft.Text("游戏签到", size=16, weight=ft.FontWeight.BOLD),
                    ft.Row(games_cards, wrap=True, spacing=10),
                    ft.Container(height=20),
                    ft.Text("今日签到记录", size=16, weight=ft.FontWeight.BOLD),
                    self._create_today_logs_view(today_logs),
                ],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        
        self.page.update()
    
    def _create_game_card(self, game_key: str, game_name: str, enabled: bool, account: Account):
        """创建游戏卡片"""
        today_logs = self.log_manager.get_today_logs(account.id)
        signed = any(log.game == game_key and log.success for log in today_logs)
        
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.VIDEOGAME_ASSET,
                                    color=ft.Colors.GREEN if signed else ft.Colors.BLUE,
                                ),
                                ft.Text(game_name, weight=ft.FontWeight.W_500),
                            ],
                        ),
                        ft.Text(
                            "已签到 ✓" if signed else ("已启用" if enabled else "未启用"),
                            color=ft.Colors.GREEN if signed else (ft.Colors.GREY_600 if enabled else ft.Colors.GREY_400),
                            size=12,
                        ),
                        ft.Container(height=5),
                        ft.OutlinedButton(
                            "签到" if not signed else "已完成",
                            disabled=signed or not enabled,
                            on_click=lambda _, gk=game_key: self._do_sign_single(account, gk),
                        ),
                    ],
                    spacing=5,
                ),
                padding=15,
                width=150,
            ),
        )
    
    def _create_today_logs_view(self, logs):
        """创建今日日志视图"""
        if not logs:
            return ft.Container(
                content=ft.Text("今日暂无签到记录", color=ft.Colors.GREY_500),
                padding=10,
            )
        
        return ft.Column(
            [
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.CHECK_CIRCLE if log.success else ft.Icons.ERROR,
                        color=ft.Colors.GREEN if log.success else ft.Colors.RED,
                    ),
                    title=ft.Text(f"{log.game_name}"),
                    subtitle=ft.Text(log.message, size=12),
                    trailing=ft.Text(
                        datetime.fromisoformat(log.timestamp).strftime("%H:%M"),
                        size=12,
                        color=ft.Colors.GREY_500,
                    ),
                )
                for log in logs[:5]
            ],
        )
    
    def _do_sign_all(self, account: Account):
        """执行全部签到"""
        def sign_thread():
            self.page.run_thread(lambda: self._show_loading("正在签到..."))
            
            try:
                service = CheckinService(account.cookie)
                results = service.sign_all(account.enabled_games)
                
                # 记录日志
                for game_key, result in results.items():
                    self.log_manager.add_log(
                        account_id=account.id,
                        account_name=account.name,
                        game=game_key,
                        game_name=result.get("game_name", ""),
                        success=result.get("success", False),
                        message=result.get("message", ""),
                        role_info=result.get("role_info")
                    )
                
                # 更新最后签到时间
                self.account_manager.update_last_sign_time(account.id)
                
                self.page.run_thread(self._hide_loading)
                self.page.run_thread(lambda: self._show_sign_results(results))
                self.page.run_thread(self._refresh_home)
            except Exception as e:
                self.page.run_thread(self._hide_loading)
                self.page.run_thread(lambda: self._show_error(str(e)))
        
        threading.Thread(target=sign_thread, daemon=True).start()
    
    def _do_sign_single(self, account: Account, game_key: str):
        """执行单个游戏签到"""
        def sign_thread():
            self.page.run_thread(lambda: self._show_loading(f"正在签到 {GAMES[game_key]['name']}..."))
            
            try:
                service = CheckinService(account.cookie)
                success, message, role_info = service.sign(game_key)
                
                # 记录日志
                self.log_manager.add_log(
                    account_id=account.id,
                    account_name=account.name,
                    game=game_key,
                    game_name=GAMES[game_key]["name"],
                    success=success,
                    message=message,
                    role_info=role_info
                )
                
                self.page.run_thread(self._hide_loading)
                self.page.run_thread(lambda: self._show_snackbar(
                    f"{'✓' if success else '✗'} {GAMES[game_key]['name']}: {message}",
                    success
                ))
                self.page.run_thread(self._refresh_home)
            except Exception as e:
                self.page.run_thread(self._hide_loading)
                self.page.run_thread(lambda: self._show_error(str(e)))
        
        threading.Thread(target=sign_thread, daemon=True).start()
    
    def _show_sign_results(self, results: dict):
        """显示签到结果"""
        content = ft.Column(
            [
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.CHECK_CIRCLE if r["success"] else ft.Icons.ERROR,
                        color=ft.Colors.GREEN if r["success"] else ft.Colors.RED,
                    ),
                    title=ft.Text(r["game_name"]),
                    subtitle=ft.Text(r["message"]),
                )
                for r in results.values()
            ],
            scroll=ft.ScrollMode.AUTO,
        )
        
        dialog = ft.AlertDialog(
            title=ft.Text("签到结果"),
            content=ft.Container(content=content, width=400, height=300),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self._close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    # ==================== 账户管理 ====================
    def _show_accounts(self):
        """显示账户管理页面"""
        accounts = self.account_manager.get_all_accounts()
        current_id = self.account_manager.config.current_account_id
        
        account_cards = []
        for acc in accounts:
            is_current = acc.id == current_id
            account_cards.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.CircleAvatar(
                                    content=ft.Text(acc.name[0] if acc.name else "?"),
                                    bgcolor=ft.Colors.BLUE_400 if is_current else ft.Colors.GREY_400,
                                ),
                                ft.Column(
                                    [
                                        ft.Row([
                                            ft.Text(acc.name, weight=ft.FontWeight.BOLD),
                                            ft.Container(
                                                content=ft.Text("当前", size=10, color=ft.Colors.WHITE),
                                                bgcolor=ft.Colors.BLUE,
                                                border_radius=10,
                                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                            ) if is_current else ft.Container(),
                                        ]),
                                        ft.Text(f"UID: {acc.id}", size=12, color=ft.Colors.GREY_600),
                                    ],
                                    spacing=2,
                                ),
                                ft.Container(expand=True),
                                ft.IconButton(
                                    ft.Icons.CHECK_CIRCLE if is_current else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                    tooltip="设为当前账户",
                                    on_click=lambda _, aid=acc.id: self._set_current_account(aid),
                                ),
                                ft.IconButton(
                                    ft.Icons.EDIT,
                                    tooltip="编辑",
                                    on_click=lambda _, aid=acc.id: self._show_edit_account_dialog(aid),
                                ),
                                ft.IconButton(
                                    ft.Icons.DELETE,
                                    tooltip="删除",
                                    on_click=lambda _, aid=acc.id: self._confirm_delete_account(aid),
                                ),
                            ],
                        ),
                        padding=15,
                    ),
                )
            )
        
        self.content_area.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("账户管理", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "添加账户",
                            icon=ft.Icons.ADD,
                            on_click=lambda _: self._show_add_account_dialog(),
                        ),
                    ],
                ),
                ft.Divider(),
                ft.Column(
                    account_cards if account_cards else [
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Icon(ft.Icons.ACCOUNT_CIRCLE_OUTLINED, size=60, color=ft.Colors.GREY_400),
                                    ft.Text("暂无账户", color=ft.Colors.GREY_500),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                            padding=50,
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ],
            expand=True,
        )
        self.page.update()
    
    def _show_add_account_dialog(self):
        """显示添加账户对话框"""
        self.qr_login = QRLogin()
        qr_url, ticket = self.qr_login.get_qr_url()
        
        if not qr_url:
            self._show_error("获取二维码失败，请重试")
            return
        
        self.current_qr_url = qr_url
        
        # 生成二维码图片
        qr_image = self._generate_qr_image(qr_url)
        
        status_text = ft.Text("请使用米游社 APP 扫描二维码登录", text_align=ft.TextAlign.CENTER)
        
        dialog = ft.AlertDialog(
            title=ft.Text("添加账户"),
            content=ft.Container(
                content=ft.Column(
                    [
                        qr_image,
                        status_text,
                        ft.TextButton(
                            "刷新二维码",
                            icon=ft.Icons.REFRESH,
                            on_click=lambda _: self._refresh_qr_code(dialog, status_text),
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15,
                ),
                width=300,
                height=350,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._cancel_login(dialog)),
            ],
        )
        
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
        
        # 开始监听登录状态
        threading.Thread(
            target=self._wait_for_login,
            args=(ticket, dialog, status_text),
            daemon=True
        ).start()
    
    def _generate_qr_image(self, url: str):
        """生成二维码图片"""
        if HAS_QRCODE:
            qr = qrcode.QRCode(version=1, box_size=8, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            img_base64 = base64.b64encode(buffer.read()).decode()
            
            return ft.Image(src=f"data:image/png;base64,{img_base64}", width=200, height=200)
        else:
            return ft.Column(
                [
                    ft.Text("请访问以下链接查看二维码:", size=12),
                    ft.Text(
                        f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}",
                        size=10,
                        selectable=True,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
    
    def _refresh_qr_code(self, dialog: ft.AlertDialog, status_text: ft.Text):
        """刷新二维码"""
        if self.qr_login:
            self.qr_login.stop()
        
        self.qr_login = QRLogin()
        qr_url, ticket = self.qr_login.get_qr_url()
        
        if qr_url:
            self.current_qr_url = qr_url
            status_text.value = "请使用米游社 APP 扫描二维码登录"
            
            # 更新二维码图片
            qr_image = self._generate_qr_image(qr_url)
            dialog.content.content.controls[0] = qr_image
            self.page.update()
            
            # 重新开始监听
            threading.Thread(
                target=self._wait_for_login,
                args=(ticket, dialog, status_text),
                daemon=True
            ).start()
        else:
            status_text.value = "获取二维码失败，请重试"
            self.page.update()
    
    def _wait_for_login(self, ticket: str, dialog: ft.AlertDialog, status_text: ft.Text):
        """等待登录完成"""
        def update_status(msg: str):
            status_text.value = msg
            self.page.update()
        
        uid, game_token = self.qr_login.check_login(ticket, update_status)
        
        if uid and game_token:
            # 获取完整 Cookie
            mid, stoken = self.qr_login.get_stoken(uid, game_token)
            if stoken:
                cookie_token = self.qr_login.get_cookie_token(uid, stoken, mid)
                ltoken = self.qr_login.get_ltoken(uid, stoken, mid)
                
                # 构建 Cookie
                cookie_parts = [
                    f"stuid={uid}", f"ltuid={uid}", f"ltuid_v2={uid}",
                    f"account_id={uid}", f"account_id_v2={uid}",
                    f"stoken={stoken}", f"mid={mid}", f"ltmid_v2={mid}",
                ]
                if cookie_token:
                    cookie_parts.extend([
                        f"cookie_token={cookie_token}",
                        f"cookie_token_v2={cookie_token}",
                        f"account_mid_v2={mid}",
                    ])
                if ltoken:
                    cookie_parts.extend([f"ltoken={ltoken}", f"ltoken_v2={ltoken}"])
                
                cookie = "; ".join(cookie_parts)
                
                # 获取用户昵称
                service = CheckinService(cookie)
                user_info = service.get_user_info()
                nickname = f"账户_{uid}"
                if user_info:
                    for game_data in user_info.values():
                        roles = game_data.get("roles", [])
                        if roles:
                            nickname = roles[0].get("nickname", nickname)
                            break
                
                # 添加账户
                if not self.account_manager.account_exists(uid):
                    self.account_manager.add_account(uid, nickname, cookie)
                    self.page.run_thread(lambda: self._show_snackbar(f"账户 {nickname} 添加成功!", True))
                else:
                    self.account_manager.update_account(uid, cookie=cookie, name=nickname)
                    self.page.run_thread(lambda: self._show_snackbar(f"账户 {nickname} 更新成功!", True))
                
                self.page.run_thread(lambda: self._close_dialog(dialog))
                self.page.run_thread(self._show_accounts)
    
    def _cancel_login(self, dialog: ft.AlertDialog):
        """取消登录"""
        if self.qr_login:
            self.qr_login.stop()
        self._close_dialog(dialog)
    
    def _set_current_account(self, account_id: str):
        """设置当前账户"""
        self.account_manager.set_current_account(account_id)
        self._show_accounts()
        self._show_snackbar("已切换当前账户", True)
    
    def _show_edit_account_dialog(self, account_id: str):
        """显示编辑账户对话框"""
        account = self.account_manager.get_account(account_id)
        if not account:
            return
        
        name_field = ft.TextField(value=account.name, label="账户名称")
        
        game_switches = {}
        for game_key, game_info in GAMES.items():
            enabled = game_key in (account.enabled_games or [])
            game_switches[game_key] = ft.Switch(value=enabled, label=game_info["name"])
        
        dialog = ft.AlertDialog(
            title=ft.Text("编辑账户"),
            content=ft.Container(
                content=ft.Column(
                    [
                        name_field,
                        ft.Text("启用的游戏:", weight=ft.FontWeight.BOLD),
                        *game_switches.values(),
                    ],
                    spacing=10,
                ),
                width=300,
            ),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton(
                    "保存",
                    on_click=lambda _: self._save_account_edit(
                        dialog, account_id, name_field, game_switches
                    ),
                ),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _save_account_edit(self, dialog, account_id, name_field, game_switches):
        """保存账户编辑"""
        enabled_games = [k for k, v in game_switches.items() if v.value]
        self.account_manager.update_account(
            account_id,
            name=name_field.value,
            enabled_games=enabled_games
        )
        self._close_dialog(dialog)
        self._show_accounts()
        self._show_snackbar("账户已更新", True)
    
    def _confirm_delete_account(self, account_id: str):
        """确认删除账户"""
        account = self.account_manager.get_account(account_id)
        if not account:
            return
        
        dialog = ft.AlertDialog(
            title=ft.Text("确认删除"),
            content=ft.Text(f"确定要删除账户 \"{account.name}\" 吗？此操作不可撤销。"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton(
                    "删除",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.RED,
                    on_click=lambda _: self._delete_account(dialog, account_id),
                ),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _delete_account(self, dialog, account_id):
        """删除账户"""
        self.account_manager.remove_account(account_id)
        self._close_dialog(dialog)
        self._show_accounts()
        self._show_snackbar("账户已删除", True)
    
    # ==================== 定时设置 ====================
    def _show_schedule(self):
        """显示定时设置页面"""
        config = self.account_manager.get_config()
        status = self.scheduler_manager.get_status()
        
        schedule_switch = ft.Switch(
            value=config.schedule_enabled,
            label="启用定时签到",
            on_change=lambda e: self._toggle_schedule(e, time_picker),
        )
        
        # 解析时间
        hour, minute = map(int, config.schedule_time.split(":"))
        
        def on_time_change(e):
            self._update_schedule_time(e)
        
        time_picker = ft.TimePicker(
            value=datetime(2000, 1, 1, hour, minute).time(),
            on_change=on_time_change,
        )
        
        # 将 TimePicker 添加到 overlay
        self.page.overlay.append(time_picker)
        
        def open_time_picker(_):
            time_picker.open = True
            self.page.update()
        
        time_button = ft.ElevatedButton(
            f"签到时间: {config.schedule_time}",
            icon=ft.Icons.ACCESS_TIME,
            on_click=open_time_picker,
        )
        
        next_run_text = ft.Text(
            f"下次签到: {status.get('next_run', '未启用')}" if status.get('next_run') else "定时签到未启用",
            color=ft.Colors.GREY_600,
        )
        
        self.content_area.content = ft.Column(
            [
                ft.Text("定时设置", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                schedule_switch,
                                ft.Container(height=10),
                                time_button,
                                ft.Container(height=10),
                                next_run_text,
                            ],
                        ),
                        padding=20,
                    ),
                ),
                ft.Container(height=20),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("说明", weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    "• 启用定时签到后，程序将在每天指定时间自动为所有激活的账户执行签到\n"
                                    "• 请确保程序在后台运行\n"
                                    "• 如需开机自动运行，请在设置中启用开机自启动",
                                    color=ft.Colors.GREY_600,
                                ),
                            ],
                        ),
                        padding=20,
                    ),
                ),
            ],
            expand=True,
        )
        self.page.update()
    
    def _toggle_schedule(self, e, time_picker):
        """切换定时状态"""
        enabled = e.control.value
        self.scheduler_manager.update_schedule(enabled)
        self._show_schedule()
        self._show_snackbar(f"定时签到已{'启用' if enabled else '禁用'}", True)
    
    def _update_schedule_time(self, e):
        """更新定时时间"""
        if e.control.value:
            time_str = e.control.value.strftime("%H:%M")
            self.scheduler_manager.update_schedule(
                self.account_manager.config.schedule_enabled,
                time_str
            )
            self._show_schedule()
            self._show_snackbar(f"签到时间已设置为 {time_str}", True)
    
    # ==================== 日志页面 ====================
    def _show_logs(self):
        """显示日志页面"""
        logs = self.log_manager.get_logs(limit=100)
        
        log_items = []
        for log in logs:
            log_items.append(
                ft.ListTile(
                    leading=ft.Icon(
                        ft.Icons.CHECK_CIRCLE if log.success else ft.Icons.ERROR,
                        color=ft.Colors.GREEN if log.success else ft.Colors.RED,
                    ),
                    title=ft.Text(f"{log.account_name} - {log.game_name}"),
                    subtitle=ft.Text(log.message, size=12),
                    trailing=ft.Text(
                        datetime.fromisoformat(log.timestamp).strftime("%m-%d %H:%M"),
                        size=12,
                        color=ft.Colors.GREY_500,
                    ),
                )
            )
        
        self.content_area.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("签到日志", size=24, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.OutlinedButton(
                            "清空日志",
                            icon=ft.Icons.DELETE_SWEEP,
                            on_click=lambda _: self._confirm_clear_logs(),
                        ),
                    ],
                ),
                ft.Divider(),
                ft.Column(
                    log_items if log_items else [
                        ft.Container(
                            content=ft.Text("暂无日志记录", color=ft.Colors.GREY_500),
                            padding=50,
                        )
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ],
            expand=True,
        )
        self.page.update()
    
    def _confirm_clear_logs(self):
        """确认清空日志"""
        dialog = ft.AlertDialog(
            title=ft.Text("确认清空"),
            content=ft.Text("确定要清空所有日志吗？此操作不可撤销。"),
            actions=[
                ft.TextButton("取消", on_click=lambda _: self._close_dialog(dialog)),
                ft.ElevatedButton(
                    "清空",
                    color=ft.Colors.WHITE,
                    bgcolor=ft.Colors.RED,
                    on_click=lambda _: self._clear_logs(dialog),
                ),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _clear_logs(self, dialog):
        """清空日志"""
        self.log_manager.clear_logs()
        self._close_dialog(dialog)
        self._show_logs()
        self._show_snackbar("日志已清空", True)
    
    # ==================== 设置页面 ====================
    def _show_settings(self):
        """显示设置页面"""
        config = self.account_manager.get_config()
        
        auto_start_switch = ft.Switch(
            value=AutoStart.is_enabled(),
            label="开机自启动",
            on_change=self._toggle_auto_start,
        )
        
        minimize_switch = ft.Switch(
            value=config.minimize_to_tray,
            label="最小化到系统托盘",
            on_change=lambda e: self._update_setting("minimize_to_tray", e.control.value),
        )
        
        notification_switch = ft.Switch(
            value=config.notification_enabled,
            label="启用通知",
            on_change=lambda e: self._update_setting("notification_enabled", e.control.value),
        )
        
        def on_theme_select(e):
            self._change_theme(e)
        
        theme_dropdown = ft.Dropdown(
            value=config.theme,
            label="主题",
            options=[
                ft.dropdown.Option("system", "跟随系统"),
                ft.dropdown.Option("light", "浅色"),
                ft.dropdown.Option("dark", "深色"),
            ],
            width=200,
        )
        theme_dropdown.on_change = on_theme_select
        
        self.content_area.content = ft.Column(
            [
                ft.Text("设置", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("常规设置", weight=ft.FontWeight.BOLD),
                                auto_start_switch,
                                minimize_switch,
                                notification_switch,
                                ft.Container(height=10),
                                theme_dropdown,
                            ],
                        ),
                        padding=20,
                    ),
                ),
                ft.Container(height=20),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("关于", weight=ft.FontWeight.BOLD),
                                ft.Text("米哈游自动签到工具 v2.0"),
                                ft.Text("支持: 原神 | 崩坏：星穹铁道 | 绝区零", color=ft.Colors.GREY_600),
                                ft.Container(height=10),
                                ft.Text(
                                    "使用 WinUI3 风格界面 (Flet)",
                                    color=ft.Colors.GREY_500,
                                    size=12,
                                ),
                            ],
                        ),
                        padding=20,
                    ),
                ),
            ],
            expand=True,
            scroll=ft.ScrollMode.AUTO,
        )
        self.page.update()
    
    def _toggle_auto_start(self, e):
        """切换自启动"""
        enabled = e.control.value
        success = AutoStart.set_enabled(enabled)
        if success:
            self._show_snackbar(f"开机自启动已{'启用' if enabled else '禁用'}", True)
        else:
            e.control.value = not enabled
            self.page.update()
            self._show_error("设置自启动失败，请尝试以管理员身份运行")
    
    def _update_setting(self, key: str, value):
        """更新设置"""
        self.account_manager.update_config(**{key: value})
    
    def _change_theme(self, e):
        """切换主题"""
        theme = e.control.value
        self.account_manager.update_config(theme=theme)
        
        if theme == "light":
            self.page.theme_mode = ft.ThemeMode.LIGHT
        elif theme == "dark":
            self.page.theme_mode = ft.ThemeMode.DARK
        else:
            self.page.theme_mode = ft.ThemeMode.SYSTEM
        
        self.page.update()
        self._show_snackbar("主题已更改", True)
    
    # ==================== 辅助方法 ====================
    def _show_loading(self, message: str = "加载中..."):
        """显示加载提示"""
        self.loading_dialog = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.ProgressRing(width=24, height=24, stroke_width=3),
                        ft.Text(message),
                    ],
                    spacing=15,
                ),
                padding=20,
            ),
        )
        self.page.overlay.append(self.loading_dialog)
        self.loading_dialog.open = True
        self.page.update()
    
    def _hide_loading(self):
        """隐藏加载提示"""
        if hasattr(self, 'loading_dialog') and self.loading_dialog:
            self.loading_dialog.open = False
            self.page.update()
    
    def _show_snackbar(self, message: str, success: bool = True):
        """显示 Snackbar 提示"""
        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(message),
            bgcolor=ft.Colors.GREEN_700 if success else ft.Colors.RED_700,
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _show_error(self, message: str):
        """显示错误提示"""
        dialog = ft.AlertDialog(
            title=ft.Text("错误"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("确定", on_click=lambda _: self._close_dialog(dialog)),
            ],
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
    
    def _close_dialog(self, dialog):
        """关闭对话框"""
        dialog.open = False
        self.page.update()


def main(page: ft.Page):
    """应用入口"""
    app = MihoyoCheckinApp(page)


if __name__ == "__main__":
    ft.app(target=main)
