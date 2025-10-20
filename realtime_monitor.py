#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安实时价格监控器
实时监控多个交易对的价格变化，支持动态添加交易对和价格排序
"""

import os
import time
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from binance import Client
from rich.console import Console, Group
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from dotenv import load_dotenv

@dataclass
class CryptoConfig:
    """加密货币配置类"""
    symbol: str
    display_name: str
    usdt_pair: str
    buy_price: float = 0
    buy_amount: float = 0
    alert_high: float = 0
    alert_low: float = 0
    last_alert_price: float = 0  # 用于记录上次提醒时的价格
    last_price: float = 0  # 用于记录上次价格，计算趋势

    def __post_init__(self):
        if not self.usdt_pair:
            self.usdt_pair = f"{self.symbol}USDT"

@dataclass
class FuturesConfig:
    """合约配置类"""
    symbol: str
    display_name: str
    usdt_pair: str
    buy_price: float = 0
    buy_amount: float = 0
    leverage: int = 1  # 杠杆倍数
    position_side: str = "LONG"  # LONG 或 SHORT
    last_price: float = 0

    def __post_init__(self):
        if not self.usdt_pair:
            self.usdt_pair = f"{self.symbol}USDT"

def get_trend_arrow(current_price: float, last_price: float) -> Tuple[str, str]:
    """获取趋势箭头和描述"""
    if last_price == 0:
        return "➡️", "持平"
    
    percent = ((current_price - last_price) / last_price) * 100
    if percent > 1:
        return "⬆️⬆️", f"强势上涨 (+{percent:.2f}%)"
    elif percent > 0:
        return "⬆️", f"上涨 (+{percent:.2f}%)"
    elif percent < -1:
        return "⬇️⬇️", f"大幅下跌 ({percent:.2f}%)"
    elif percent < 0:
        return "⬇️", f"下跌 ({percent:.2f}%)"
    else:
        return "➡️", "持平"

def send_notification(title: str, message: str, subtitle: str = ""):
    """发送 macOS 通知"""
    try:
        # 使用带子标题的通知
        apple_script = f'''
        display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Glass"
        '''
        subprocess.run(['osascript', '-e', apple_script], capture_output=True)
    except Exception:
        pass

class PriceMonitor:
    """价格监控类"""
    
    def __init__(self):
        # 加载.env文件
        load_dotenv()
        
        # 配置代理（如果需要）
        proxies = {
            'http': os.getenv('HTTP_PROXY', ''),
            'https': os.getenv('HTTPS_PROXY', '')
        }
        
        # 配置现货交易对信息
        self.CRYPTO_PAIRS = [
            CryptoConfig(
                "BTC", "比特币", "BTCUSDT",
                float(os.getenv('BTC_PRICE', 0)),
                float(os.getenv('BTC_AMOUNT', 0)),
                float(os.getenv('BTC_ALERT_HIGH', 0)),
                float(os.getenv('BTC_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "ETH", "以太坊", "ETHUSDT",
                float(os.getenv('ETH_PRICE', 0)),
                float(os.getenv('ETH_AMOUNT', 0)),
                float(os.getenv('ETH_ALERT_HIGH', 0)),
                float(os.getenv('ETH_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "BNB", "币安币", "BNBUSDT",
                float(os.getenv('BNB_PRICE', 0)),
                float(os.getenv('BNB_AMOUNT', 0)),
                float(os.getenv('BNB_ALERT_HIGH', 0)),
                float(os.getenv('BNB_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "SOL", "索拉纳", "SOLUSDT",
                float(os.getenv('SOL_PRICE', 0)),
                float(os.getenv('SOL_AMOUNT', 0)),
                float(os.getenv('SOL_ALERT_HIGH', 0)),
                float(os.getenv('SOL_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "TON", "TON", "TONUSDT",
                float(os.getenv('TON_PRICE', 0)),
                float(os.getenv('TON_AMOUNT', 0)),
                float(os.getenv('TON_ALERT_HIGH', 0)),
                float(os.getenv('TON_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "DOGE", "狗狗币", "DOGEUSDT",
                float(os.getenv('DOGE_PRICE', 0)),
                float(os.getenv('DOGE_AMOUNT', 0)),
                float(os.getenv('DOGE_ALERT_HIGH', 0)),
                float(os.getenv('DOGE_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "SUI", "SUI", "SUIUSDT",
                float(os.getenv('SUI_PRICE', 0)),
                float(os.getenv('SUI_AMOUNT', 0)),
                float(os.getenv('SUI_ALERT_HIGH', 0)),
                float(os.getenv('SUI_ALERT_LOW', 0))
            ),
            CryptoConfig(
                "ASTER", "ASTER", "ASTERUSDT",
                float(os.getenv('ASTER_PRICE', 0)),
                float(os.getenv('ASTER_AMOUNT', 0)),
                float(os.getenv('ASTER_ALERT_HIGH', 0)),
                float(os.getenv('ASTER_ALERT_LOW', 0))
            ),
        ]
        
        # 配置合约交易对信息
        self.FUTURES_PAIRS = [
            FuturesConfig(
                "BTC", "比特币合约", "BTCUSDT",
                float(os.getenv('FUTURES_BTC_PRICE', 0)),
                float(os.getenv('FUTURES_BTC_AMOUNT', 0)),
                int(os.getenv('FUTURES_BTC_LEVERAGE', 1)),
                os.getenv('FUTURES_BTC_SIDE', 'LONG')
            ),
            FuturesConfig(
                "ETH", "以太坊合约", "ETHUSDT",
                float(os.getenv('FUTURES_ETH_PRICE', 0)),
                float(os.getenv('FUTURES_ETH_AMOUNT', 0)),
                int(os.getenv('FUTURES_ETH_LEVERAGE', 1)),
                os.getenv('FUTURES_ETH_SIDE', 'LONG')
            ),
            FuturesConfig(
                "BNB", "币安币合约", "BNBUSDT",
                float(os.getenv('FUTURES_BNB_PRICE', 0)),
                float(os.getenv('FUTURES_BNB_AMOUNT', 0)),
                int(os.getenv('FUTURES_BNB_LEVERAGE', 1)),
                os.getenv('FUTURES_BNB_SIDE', 'LONG')
            ),
            FuturesConfig(
                "SOL", "索拉纳合约", "SOLUSDT",
                float(os.getenv('FUTURES_SOL_PRICE', 0)),
                float(os.getenv('FUTURES_SOL_AMOUNT', 0)),
                int(os.getenv('FUTURES_SOL_LEVERAGE', 1)),
                os.getenv('FUTURES_SOL_SIDE', 'LONG')
            ),
        ]
        
        self.console = Console()
        # 初始化Client，如果设置了代理则使用代理
        if proxies['http'] or proxies['https']:
            self.client = Client(
                requests_params={'proxies': proxies, 'timeout': 10}
            )
        else:
            self.client = Client()
        
        self.price_data = {}
        self.futures_data = {}
        self.last_update_time = ''
        self.last_futures_update_time = ''
        self.initialize_price_data()
        self.initialize_futures_data()
        
        # 计算总投资
        self.total_investment = sum(crypto.buy_amount for crypto in self.CRYPTO_PAIRS)
        self.total_futures_investment = sum(futures.buy_amount for futures in self.FUTURES_PAIRS)

    def initialize_price_data(self):
        """初始化价格数据结构"""
        for crypto in self.CRYPTO_PAIRS:
            self.price_data[crypto.usdt_pair] = {
                'price': 0,
                'last_price': 0,  # 添加上次价格记录
                'change_24h': 0,
                'change_5m': 0,
                'change_1m': 0,
                'display_name': crypto.display_name,
                'buy_price': crypto.buy_price,
                'buy_amount': crypto.buy_amount,
                'profit_usdt': 0,
                'profit_percent': 0,
                'alert_high': crypto.alert_high,
                'alert_low': crypto.alert_low,
                'last_alert_price': 0
            }
    
    def initialize_futures_data(self):
        """初始化合约数据结构"""
        for futures in self.FUTURES_PAIRS:
            self.futures_data[futures.usdt_pair] = {
                'price': 0,
                'last_price': 0,
                'change_24h': 0,
                'funding_rate': 0,  # 资金费率
                'display_name': futures.display_name,
                'buy_price': futures.buy_price,
                'buy_amount': futures.buy_amount,
                'leverage': futures.leverage,
                'position_side': futures.position_side,
                'profit_usdt': 0,
                'profit_percent': 0,
                'liquidation_price': 0  # 爆仓价格
            }

    def check_price_alerts(self, symbol: str, current_price: float) -> None:
        """检查价格是否触发提醒"""
        data = self.price_data[symbol]
        alert_high = data['alert_high']
        alert_low = data['alert_low']
        last_alert_price = data['last_alert_price']
        last_price = data['last_price']
        display_name = data['display_name']

        # 获取趋势箭头和描述
        trend_arrow, trend_desc = get_trend_arrow(current_price, last_price)
        
        # 构建通知标题和消息
        def build_alert_message(price_type: str, threshold: float) -> tuple:
            change_percent = ((current_price - last_price) / last_price * 100) if last_price > 0 else 0
            title = f"{display_name} {trend_arrow} {price_type}"
            subtitle = trend_desc
            message = (
                f"当前价格: {current_price:.2f} USDT\n"
                f"目标价位: {threshold:.2f} USDT\n"
                f"价格变化: {change_percent:+.2f}%"
            )
            return title, subtitle, message

        # 避免重复提醒：只在价格首次超过阈值或回落后再次超过时提醒
        if alert_high > 0 and current_price >= alert_high and (last_alert_price == 0 or last_alert_price < alert_high):
            title, subtitle, message = build_alert_message("价格突破上限", alert_high)
            send_notification(title, message, subtitle)
            data['last_alert_price'] = current_price
        
        elif alert_low > 0 and current_price <= alert_low and (last_alert_price == 0 or last_alert_price > alert_low):
            title, subtitle, message = build_alert_message("价格跌破下限", alert_low)
            send_notification(title, message, subtitle)
            data['last_alert_price'] = current_price

        # 更新上次价格
        data['last_price'] = current_price

    def calculate_change_percent(self, current_price: float, old_price: float) -> float:
        """计算价格变化百分比"""
        if old_price == 0:
            return 0
        return ((current_price - old_price) / old_price) * 100

    def calculate_profit(self, symbol: str, current_price: float) -> tuple:
        """计算现货收益"""
        data = self.price_data[symbol]
        buy_price = data['buy_price']
        buy_amount = data['buy_amount']
        
        if buy_price == 0 or buy_amount == 0:
            return 0, 0
            
        # 计算买入时的币数量
        coin_amount = buy_amount / buy_price
        
        # 计算当前市值
        current_value = coin_amount * current_price
        
        # 计算收益（USDT）
        profit_usdt = current_value - buy_amount
        
        # 计算收益率
        profit_percent = (profit_usdt / buy_amount) * 100 if buy_amount > 0 else 0
        
        return profit_usdt, profit_percent
    
    def calculate_futures_profit(self, symbol: str, current_price: float) -> tuple:
        """计算合约收益"""
        data = self.futures_data[symbol]
        buy_price = data['buy_price']
        buy_amount = data['buy_amount']
        leverage = data['leverage']
        position_side = data['position_side']
        
        if buy_price == 0 or buy_amount == 0:
            return 0, 0, 0
        
        # 计算价格变化百分比
        price_change_percent = ((current_price - buy_price) / buy_price) * 100
        
        # 根据持仓方向计算收益
        if position_side == "SHORT":
            price_change_percent = -price_change_percent
        
        # 计算收益（带杠杆）
        profit_percent = price_change_percent * leverage
        profit_usdt = buy_amount * profit_percent / 100
        
        # 计算爆仓价格
        if position_side == "LONG":
            # 做多爆仓价格 = 开仓价格 * (1 - 1/杠杆)
            liquidation_price = buy_price * (1 - 0.9 / leverage)
        else:
            # 做空爆仓价格 = 开仓价格 * (1 + 1/杠杆)
            liquidation_price = buy_price * (1 + 0.9 / leverage)
        
        return profit_usdt, profit_percent, liquidation_price

    def get_klines_change(self, symbol: str) -> None:
        """获取K线数据并计算涨跌幅"""
        try:
            # 1分钟K线
            klines_1m = self.client.get_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_1MINUTE,
                limit=2
            )
            if klines_1m:
                open_price_1m = float(klines_1m[0][1])
                current_price_1m = float(klines_1m[-1][4])
                self.price_data[symbol]['change_1m'] = self.calculate_change_percent(
                    current_price_1m, open_price_1m
                )

            # 5分钟K线
            klines_5m = self.client.get_klines(
                symbol=symbol,
                interval=Client.KLINE_INTERVAL_5MINUTE,
                limit=2
            )
            if klines_5m:
                open_price_5m = float(klines_5m[0][1])
                current_price_5m = float(klines_5m[-1][4])
                self.price_data[symbol]['change_5m'] = self.calculate_change_percent(
                    current_price_5m, open_price_5m
                )
        except Exception:
            pass

    def update_price_data(self) -> None:
        """更新价格数据"""
        try:
            # 记录本次更新的时间戳
            update_time = datetime.now()
            self.last_update_time = update_time.strftime('%H:%M:%S.%f')[:-4]

            # 批量获取所有交易对的ticker数据
            all_tickers = {t['symbol']: t for t in self.client.get_ticker()}
            
            # 更新每个交易对的数据
            total_profit = 0
            for symbol in self.price_data.keys():
                if symbol in all_tickers:
                    ticker = all_tickers[symbol]
                    current_price = float(ticker['lastPrice'])
                    
                    # 检查价格提醒
                    self.check_price_alerts(symbol, current_price)
                    
                    # 计算收益
                    profit_usdt, profit_percent = self.calculate_profit(symbol, current_price)
                    total_profit += profit_usdt
                    
                    self.price_data[symbol].update({
                        'price': current_price,
                        'change_24h': float(ticker['priceChangePercent']),
                        'profit_usdt': profit_usdt,
                        'profit_percent': profit_percent
                    })
                    # 同步更新K线数据
                    self.get_klines_change(symbol)
            
            # 更新总收益率
            self.total_profit = total_profit
            self.total_profit_percent = (total_profit / self.total_investment * 100) if self.total_investment > 0 else 0
            
        except Exception as e:
            self.console.print(f"[red]获取数据时发生错误: {str(e)}[/red]")
    
    def update_futures_data(self) -> None:
        """更新合约数据"""
        try:
            # 记录本次更新的时间戳
            update_time = datetime.now()
            self.last_futures_update_time = update_time.strftime('%H:%M:%S.%f')[:-4]

            # 获取合约ticker数据
            futures_tickers = self.client.futures_symbol_ticker()
            futures_tickers_dict = {t['symbol']: t for t in futures_tickers}
            
            # 获取24h统计数据
            futures_24h = self.client.futures_ticker()
            futures_24h_dict = {t['symbol']: t for t in futures_24h}
            
            # 更新每个合约交易对的数据
            total_futures_profit = 0
            for symbol in self.futures_data.keys():
                if symbol in futures_tickers_dict and symbol in futures_24h_dict:
                    current_price = float(futures_tickers_dict[symbol]['price'])
                    change_24h = float(futures_24h_dict[symbol]['priceChangePercent'])
                    
                    # 计算合约收益
                    profit_usdt, profit_percent, liquidation_price = self.calculate_futures_profit(symbol, current_price)
                    total_futures_profit += profit_usdt
                    
                    self.futures_data[symbol].update({
                        'price': current_price,
                        'change_24h': change_24h,
                        'profit_usdt': profit_usdt,
                        'profit_percent': profit_percent,
                        'liquidation_price': liquidation_price
                    })
            
            # 更新总收益率
            self.total_futures_profit = total_futures_profit
            self.total_futures_profit_percent = (total_futures_profit / self.total_futures_investment * 100) if self.total_futures_investment > 0 else 0
            
        except Exception as e:
            self.console.print(f"[red]获取合约数据时发生错误: {str(e)}[/red]")

    def get_sorted_symbols(self) -> List[str]:
        """获取按价格排序的交易对列表"""
        return sorted(
            self.price_data.keys(),
            key=lambda x: self.price_data[x]['price'],
            reverse=True
        )

    def format_price(self, price: float) -> str:
        """格式化价格显示"""
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:.4f}"
        else:
            return f"{price:.8f}"

    def format_change(self, change: float) -> str:
        """格式化涨跌幅显示"""
        if change > 0:
            return f"[green]+{change:.2f}%[/green]"
        elif change < 0:
            return f"[red]{change:.2f}%[/red]"
        return f"[white]{change:.2f}%[/white]"

    def format_profit(self, profit: float, percent: float) -> str:
        """格式化收益显示"""
        if profit > 0:
            return f"[green]+{profit:.2f}U ({percent:+.2f}%)[/green]"
        elif profit < 0:
            return f"[red]{profit:.2f}U ({percent:+.2f}%)[/red]"
        return f"[white]{profit:.2f}U ({percent:+.2f}%)[/white]"

    def generate_table(self) -> Panel:
        """生成价格表格"""
        table = Table(
            show_header=True,
            header_style="bold magenta",
            title=f"币安实时价格监控 (更新时间: {self.last_update_time})",
            title_style="bold cyan"
        )
        
        # 添加表格列
        table.add_column("排名", style="blue", justify="center", width=6)
        table.add_column("币种", style="cyan", justify="left", width=15)
        table.add_column("现货价格", style="yellow", justify="right", width=16)
        table.add_column("24h涨跌", justify="right", width=12)
        table.add_column("5m涨跌", justify="right", width=12)
        table.add_column("1m涨跌", justify="right", width=12)
        table.add_column("持仓收益", justify="right", width=25)

        # 获取排序后的交易对
        sorted_symbols = self.get_sorted_symbols()
        
        # 添加行数据
        for rank, symbol in enumerate(sorted_symbols, 1):
            data = self.price_data[symbol]
            price = data['price']
            
            # 设置价格颜色
            if data['change_24h'] > 0:
                price_color = "green"
            elif data['change_24h'] < 0:
                price_color = "red"
            else:
                price_color = "white"
            
            price_str = f"[{price_color}]{self.format_price(price)}[/{price_color}]"
            
            table.add_row(
                f"#{rank}",
                f"{data['display_name']} ({symbol[:-4]})",
                price_str if price > 0 else "[dim]等待数据...[/dim]",
                self.format_change(data['change_24h']),
                self.format_change(data['change_5m']),
                self.format_change(data['change_1m']),
                self.format_profit(data['profit_usdt'], data['profit_percent'])
            )
        
        # 添加总收益行
        table.add_row(
            "",
            "[bold]总计",
            "",
            "",
            "",
            "",
            self.format_profit(self.total_profit, self.total_profit_percent)
        )
        
        # 添加底部信息
        info_text = Text()
        info_text.append("\n所有数据每秒更新 | ", style="dim green")
        info_text.append("按价格降序排列 | ", style="dim yellow")
        info_text.append(f"总投资: {self.total_investment:.2f}U | ", style="dim cyan")
        
        # 根据收益情况显示不同颜色
        if self.total_profit > 0:
            info_text.append(f"总收益: +{self.total_profit:.2f}U | ", style="bold green")
            info_text.append(f"收益率: +{self.total_profit_percent:.2f}%", style="bold green")
        elif self.total_profit < 0:
            info_text.append(f"总收益: {self.total_profit:.2f}U | ", style="bold red")
            info_text.append(f"收益率: {self.total_profit_percent:.2f}%", style="bold red")
        else:
            info_text.append(f"总收益: {self.total_profit:.2f}U | ", style="bold white")
            info_text.append(f"收益率: {self.total_profit_percent:.2f}%", style="bold white")
        
        return Panel(
            table,
            border_style="green",
            subtitle=info_text,
            subtitle_align="center"
        )
    
    def generate_futures_table(self) -> Panel:
        """生成合约价格表格"""
        table = Table(
            show_header=True,
            header_style="bold magenta",
            title=f"币安合约实时监控 (更新时间: {self.last_futures_update_time})",
            title_style="bold yellow"
        )
        
        # 添加表格列
        table.add_column("排名", style="blue", justify="center", width=6)
        table.add_column("币种", style="cyan", justify="left", width=12)
        table.add_column("开仓价格", style="white", justify="right", width=13)
        table.add_column("当前价格", style="yellow", justify="right", width=13)
        table.add_column("24h涨跌", justify="right", width=10)
        table.add_column("杠杆", justify="center", width=6)
        table.add_column("方向", justify="center", width=8)
        table.add_column("爆仓价格", justify="right", width=13)
        table.add_column("持仓收益", justify="right", width=22)

        # 获取按价格排序的合约交易对
        sorted_futures = sorted(
            self.futures_data.keys(),
            key=lambda x: self.futures_data[x]['price'],
            reverse=True
        )
        
        # 添加行数据
        for rank, symbol in enumerate(sorted_futures, 1):
            data = self.futures_data[symbol]
            price = data['price']
            
            # 只显示有持仓的合约
            if data['buy_amount'] == 0:
                continue
            
            # 设置价格颜色
            if data['change_24h'] > 0:
                price_color = "green"
            elif data['change_24h'] < 0:
                price_color = "red"
            else:
                price_color = "white"
            
            price_str = f"[{price_color}]{self.format_price(price)}[/{price_color}]"
            
            # 开仓价格显示
            buy_price_str = f"[white]{self.format_price(data['buy_price'])}[/white]"
            
            # 方向显示
            side_str = "[green]做多[/green]" if data['position_side'] == "LONG" else "[red]做空[/red]"
            
            # 爆仓价格显示
            liquidation_str = f"[red]{self.format_price(data['liquidation_price'])}[/red]"
            
            table.add_row(
                f"#{rank}",
                f"{symbol[:-4]}",
                buy_price_str,
                price_str if price > 0 else "[dim]等待数据...[/dim]",
                self.format_change(data['change_24h']),
                f"{data['leverage']}x",
                side_str,
                liquidation_str,
                self.format_profit(data['profit_usdt'], data['profit_percent'])
            )
        
        # 添加总收益行
        table.add_row(
            "",
            "[bold]总计",
            "",
            "",
            "",
            "",
            "",
            "",
            self.format_profit(self.total_futures_profit, self.total_futures_profit_percent)
        )
        
        # 添加底部信息
        info_text = Text()
        info_text.append("\n合约数据每2秒更新 | ", style="dim green")
        info_text.append("按价格降序排列 | ", style="dim yellow")
        info_text.append(f"总开仓金额(保证金): {self.total_futures_investment:.2f}U | ", style="dim cyan")
        
        # 根据收益情况显示不同颜色
        if self.total_futures_profit > 0:
            info_text.append(f"总收益: +{self.total_futures_profit:.2f}U | ", style="bold green")
            info_text.append(f"收益率: +{self.total_futures_profit_percent:.2f}%", style="bold green")
        elif self.total_futures_profit < 0:
            info_text.append(f"总收益: {self.total_futures_profit:.2f}U | ", style="bold red")
            info_text.append(f"收益率: {self.total_futures_profit_percent:.2f}%", style="bold red")
        else:
            info_text.append(f"总收益: {self.total_futures_profit:.2f}U | ", style="bold white")
            info_text.append(f"收益率: {self.total_futures_profit_percent:.2f}%", style="bold white")
        
        return Panel(
            table,
            border_style="yellow",
            subtitle=info_text,
            subtitle_align="center"
        )

    def generate_combined_display(self) -> Group:
        """生成组合显示（现货+合约）"""
        spot_panel = self.generate_table()
        futures_panel = self.generate_futures_table()
        return Group(spot_panel, futures_panel)

    def run(self):
        """运行监控程序"""
        self.console.clear()
        self.console.print("[bold green]正在启动币安实时价格监控器...[/bold green]")
        
        try:
            # 获取初始数据
            self.console.print("[yellow]正在获取现货初始数据...[/yellow]")
            self.update_price_data()
            self.console.print("[green]现货数据获取成功！[/green]")
            
            self.console.print("[yellow]正在获取合约初始数据...[/yellow]")
            self.update_futures_data()
            self.console.print("[green]合约数据获取成功！开始实时监控...[/green]\n")
            
            # 合约更新计数器
            futures_update_counter = 0
            
            # 使用Rich Live显示实时更新的表格
            with Live(self.generate_combined_display(), refresh_per_second=2, console=self.console) as live:
                while True:
                    start_time = time.time()
                    
                    # 每秒更新现货数据
                    self.update_price_data()
                    
                    # 每2秒更新合约数据
                    futures_update_counter += 1
                    if futures_update_counter >= 2:
                        self.update_futures_data()
                        futures_update_counter = 0
                    
                    # 更新显示
                    live.update(self.generate_combined_display())
                    
                    # 精确控制更新间隔为1秒
                    elapsed = time.time() - start_time
                    if elapsed < 1:
                        time.sleep(1 - elapsed)
        
        except KeyboardInterrupt:
            self.console.print("\n[yellow]正在停止监控...[/yellow]")
            self.console.print("[green]已安全退出[/green]")
        except Exception as e:
            self.console.print(f"\n[red]发生错误: {str(e)}[/red]")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    monitor = PriceMonitor()
    monitor.run()

if __name__ == "__main__":
    main()