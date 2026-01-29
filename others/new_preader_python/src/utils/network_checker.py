"""
网络检测工具模块
提供网络连通性检测功能，支持递增退避策略
"""

import time
import socket
import urllib.request
from typing import Optional
from urllib.error import URLError, HTTPError

from src.utils.logger import get_logger

logger = get_logger(__name__)


class NetworkChecker:
    """网络检测器"""

    # 递增等待时间序列（秒）：3, 6, 12, 24, 48, ... 直到 5 分钟（300秒）
    # 超过 300 秒后回到 3、6、12、24 秒的循环
    RETRY_DELAYS = [3, 6, 12, 24, 48, 96, 192, 300, 3, 6, 12, 24, 48, 96, 192, 300]

    @staticmethod
    def check_network_connectivity(timeout: int = 5) -> bool:
        """
        检查网络连通性

        尝试多个可靠的公共 DNS/服务来检测网络连通性：
        1. TCP 连接到公共 DNS（8.8.8.8:53）
        2. 如果 TCP 连接失败，尝试 HTTP 请求（www.baidu.com）

        Args:
            timeout: 连接超时时间（秒）

        Returns:
            True: 网络通畅
            False: 网络不通
        """
        # 方法1: 尝试 TCP 连接到公共 DNS
        try:
            # 尝试连接 Google DNS (8.8.8.8) 的 53 端口
            # 这个方法不依赖 DNS 解析，直接使用 IP 地址
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
            logger.debug(f"网络检测通过 (TCP DNS 连接成功)")
            return True
        except (socket.timeout, socket.error) as e:
            logger.debug(f"TCP DNS 连接失败: {e}")

        # 方法2: 尝试 HTTP 请求到百度
        try:
            urllib.request.urlopen("http://www.baidu.com", timeout=timeout)
            logger.debug(f"网络检测通过 (HTTP 请求成功)")
            return True
        except (URLError, HTTPError, socket.timeout) as e:
            logger.warning(f"网络检测失败: {e}")
            return False

    @staticmethod
    def wait_for_network_forever() -> None:
        """
        无限等待网络恢复，使用递增退避策略
        直到人为停止或程序退出

        按照用户要求的策略：
        1. 3、6、12、24、48、96、192、300 秒递增
        2. 达到 300 秒（5 分钟）后，回到 3、6、12、24、48... 循环
        3. 每次检测通过后立即返回
        4. 持续循环检测，直到网络恢复或人为停止
        """
        delay_index = 0
        delay_count = 0

        logger.info("开始网络检测，等待网络恢复...")

        while True:
            # 获取当前延迟时间
            delay = NetworkChecker.RETRY_DELAYS[delay_index % len(NetworkChecker.RETRY_DELAYS)]

            # 检查网络
            if NetworkChecker.check_network_connectivity():
                logger.info(f"网络已恢复！共检测 {delay_count + 1} 次")
                return

            # 记录检测失败
            delay_count += 1
            logger.warning(f"第 {delay_count} 次网络检测失败，{delay} 秒后重试...")

            # 等待
            time.sleep(delay)
            delay_index += 1

    @staticmethod
    def check_with_retry() -> None:
        """
        检查网络，如果不通则等待恢复（带递增退避）
        持续循环检测，直到网络恢复或人为停止

        这是主要使用的接口方法，封装了检测+等待的逻辑
        """
        # 先进行快速检测
        if NetworkChecker.check_network_connectivity():
            return

        # 快速检测失败，启动等待恢复流程
        logger.warning("网络检测失败，开始递增退避等待...")
        NetworkChecker.wait_for_network_forever()
