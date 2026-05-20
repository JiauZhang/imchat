# imchat

A Python async IM middleware — one unified API to connect multiple instant messaging platforms.

Currently supports WeChat, with more platforms (QQ, Telegram, etc.) coming.

## Features

- **Unified abstraction** — consistent send/receive interfaces across different IM platforms
- **Async-native** — built on `asyncio` and `httpx` for high-concurrency scenarios
- **Rich message types** — text, image, video, file, voice and more
- **Long-polling** — built-in message polling loop, easy to integrate into any async application
- **Pluggable architecture** — add a new platform by implementing its adapter

## Install

```shell
pip install imchat
```

## Sponsor

<table align="center">
    <thead>
        <tr>
            <th colspan="2">公众号</th>
        </tr>
    </thead>
    <tbody align="center" valign="center">
        <tr>
            <td colspan="2"><img src="https://jiauzhang.github.io/ghstatic/images/ofa_m.png" style="height: 196px" alt="AliPay.png"></td>
        </tr>
    </tbody>
    <thead>
        <tr>
            <th>AliPay</th>
            <th>WeChatPay</th>
        </tr>
    </thead>
    <tbody align="center" valign="center">
        <tr>
            <td><img src="https://jiauzhang.github.io/AliPay.png" style="width: 196px; height: 196px" alt="AliPay.png"></td>
            <td><img src="https://jiauzhang.github.io/WeChatPay.png" style="width: 196px; height: 196px" alt="WeChatPay.png"></td>
        </tr>
    </tbody>
</table>
