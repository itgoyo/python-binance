# 币安实时价格监控器

这个项目使用 python-binance 库实时监控 BTC、ETH、BNB 的价格变化，并在终端中美化显示。

## 功能特点

- 实时监控 BTC/USDT、ETH/USDT、BNB/USDT 价格
- 通过 WebSocket 获取实时数据（非轮询）
- 显示24小时价格涨跌百分比
- 彩色终端界面，涨跌一目了然
- 自动刷新显示

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

```bash
python realtime_monitor.py
```

## 使用说明

1. 运行脚本后会自动连接到币安的 WebSocket
2. 程序会实时显示三种加密货币的价格
3. 绿色表示上涨，红色表示下跌
4. 按 `Ctrl+C` 可以安全退出程序

## 界面说明

- **交易对**: 显示币种和交易对
- **当前价格**: 实时更新的价格（USDT计价）
- **24小时涨跌**: 过去24小时的涨跌百分比
- **更新时间**: 最后一次价格更新的时间

## 注意事项

- 本程序使用币安公开API，无需API密钥
- 确保网络连接稳定
- 数据来源于币安官方WebSocket，延迟极低

## 技术栈

- `python-binance`: 币安API封装库
- `rich`: 终端美化库

## 参考项目

- [python-binance](https://github.com/sammchardy/python-binance)

