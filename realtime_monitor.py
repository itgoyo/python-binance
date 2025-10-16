#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
币安实时价格监控器
实时监控多个交易对的价格变化，支持动态添加交易对和价格排序
"""

import time
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass
from binance import Client
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

@dataclass
class CryptoConfig:
    """加密货币配置类"""
    symbol: str
    display_name: str
    usdt_pair: str

    def __post_init__(self):
        if not self.usdt_pair:
            self.usdt_pair = f"{self.symbol}USDT"

class PriceMonitor:
    """价格监控类"""
    
    # 配置交易对信息
    CRYPTO_PAIRS = [
        CryptoConfig("BTC", "比特币", "BTCUSDT"),
        CryptoConfig("ETH", "以太坊", "ETHUSDT"),
        CryptoConfig("BNB", "币安币", "BNBUSDT"),
        CryptoConfig("SOL", "索拉纳", "SOLUSDT"),
        CryptoConfig("TON", "TON", "TONUSDT"),
        CryptoConfig("DOGE", "狗狗币", "DOGEUSDT"),
        CryptoConfig("SUI", "SUI", "SUIUSDT"),
        CryptoConfig("ASTER", "ASTER", "ASTERUSDT"),
    ]

    def __init__(self):
        self.console = Console()
        self.client = Client()
        self.price_data = {}
        self.last_update_time = ''
        self.initialize_price_data()

    def initialize_price_data(self):
        """初始化价格数据结构"""
        for crypto in self.CRYPTO_PAIRS:
            self.price_data[crypto.usdt_pair] = {
                'price': 0,
                'change_24h': 0,
                'change_5m': 0,
                'change_1m': 0,
                'display_name': crypto.display_name
            }

    def calculate_change_percent(self, current_price: float, old_price: float) -> float:
        """计算价格变化百分比"""
        if old_price == 0:
            return 0
        return ((current_price - old_price) / old_price) * 100

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
            for symbol in self.price_data.keys():
                if symbol in all_tickers:
                    ticker = all_tickers[symbol]
                    self.price_data[symbol].update({
                        'price': float(ticker['lastPrice']),
                        'change_24h': float(ticker['priceChangePercent'])
                    })
                    # 同步更新K线数据
                    self.get_klines_change(symbol)
            
        except Exception as e:
            self.console.print(f"[red]获取数据时发生错误: {str(e)}[/red]")

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
                self.format_change(data['change_1m'])
            )
        
        # 添加底部信息
        info_text = Text()
        info_text.append("\n所有数据每秒更新 | ", style="dim green")
        info_text.append("按价格降序排列", style="dim yellow")
        
        return Panel(
            table,
            border_style="green",
            subtitle=info_text,
            subtitle_align="center"
        )

    def run(self):
        """运行监控程序"""
        self.console.clear()
        self.console.print("[bold green]正在启动币安实时价格监控器...[/bold green]")
        
        try:
            # 获取初始数据
            self.console.print("[yellow]正在获取初始数据...[/yellow]")
            self.update_price_data()
            self.console.print("[green]数据获取成功！开始实时监控...[/green]\n")
            
            # 使用Rich Live显示实时更新的表格
            with Live(self.generate_table(), refresh_per_second=2, console=self.console) as live:
                while True:
                    start_time = time.time()
                    self.update_price_data()
                    live.update(self.generate_table())
                    
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