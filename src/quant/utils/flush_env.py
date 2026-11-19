#!/usr/bin/env python

# -*- coding: utf-8 -*-
# @Time    : 2026/11/19 17:44
# @Author  : daniel
# @File    : flush_env.py
# @Project : daniel_quant

"""
Description: 刷新当前的env环境变量
             刷新环境变量其实没啥用处, 比如说requests这些框架, 直接读取系统的代理, 并不是读取环境变量的
             所以需要解决问题, 还是需要从系统级别直接关闭代理
             所以:
                我在clash verge中关闭: 系统代理, tun模式代理
                               然后clash verge打开的时候, 7897端口工作状态, 直接在浏览器中设置proxy: http 127.0.0.1:7897, 使得浏览器可以使用代理, 其他均不能使用代理
            这样就能防止代码中总是使用错误的代理造成的问题了
"""
# import os
# import subprocess
#
# def env_proxy_flush(use_proxy=False):
#     result = subprocess.run(
#         ["nc", "-z", "127.0.0.1", "7897"],
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL
#     )
#
#     # 设置代理环境变量
#     proxy_keys = [
#         "http_proxy", "https_proxy", "all_proxy",
#         "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"
#     ]
#
#     if result.returncode == 0 and use_proxy:
#         os.environ["http_proxy"] = "http://127.0.0.1:7897"
#         os.environ["https_proxy"] = "http://127.0.0.1:7897"
#         os.environ["all_proxy"] = "socks5://127.0.0.1:7897"
#         print("-----------------------在走7897代理-----------------------")
#     else:
#         for key in proxy_keys:
#             os.environ.pop(key, None)
#         print("-----------------------代理不可用/不使用代理, 移除相关环境变量-----------------------")
#
#     # 打印当前环境变量
#     print("=" * 50)
#     print("当前 Python 代理环境变量")
#
#     for key in proxy_keys:
#         print(f"{key}: {os.environ.get(key, '未设置')}")
#
#     print("=" * 50)
# # ==========================================默认不连接代理. 注意🔥: 这里要优先处理, requests引用要放在后面==========================================
# env_proxy_flush(False)

import requests

import urllib.request
print("系统代理:", urllib.request.getproxies())

s = requests.Session()
settings = s.merge_environment_settings("https://www.google.com", {}, None, None, None)
print("requests 实际会用的 proxies:", settings["proxies"])


def connection_request():
    urls = [
        "https://www.google.com/",
        "https://chatgpt.com/",
        "https://www.baidu.com/",
    ]
    for url in urls:
        status_code = None
        try:
            response = requests.get(url, timeout=1)
            status_code = response.status_code
        except Exception as e:
            print(e)
            status_code = "-1"
        finally:
            print(f"url为: {url}, 连接状态: {status_code}")

def ip_request():
    urls = {
        "httpbin": "https://httpbin.org/ip",
        "ipip": "https://myip.ipip.net",
        # 不挂代理后续连个大概无法访问
        "ipify": "https://api.ipify.org?format=json",
        "ip.sb": "https://api.ip.sb/json",
    }
    for name, url in urls.items():
        try:
            response = requests.get(url, timeout=1)
            response.raise_for_status()
            try:
                result = response.json()
            except ValueError:
                result = response.text.strip()
            print(f"{name}: {result}")
        except Exception as e:
            print(f"{name}: 请求失败 - {e}")


connection_request()
ip_request()

def flush_env_done():
    print("flush env done")


