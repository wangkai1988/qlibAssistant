import sys
from pathlib import Path
import requests
from loguru import logger
from utils import (
    run_command,
    get_latest_trade_date_ak,
    get_local_data_date
)

class DataCLI:
    """
    Data management submodule: handles market data download, update and verification
    """
    def __init__(self, region: str, **kwargs):
        self.region = region
        self.kwargs = kwargs

    def need_update(self) -> bool:
        """Check if data needs to be updated"""
        latest_data = get_latest_trade_date_ak()
        local_data = get_local_data_date(self.kwargs["provider_uri"])
        logger.info(f"Latest data date: {latest_data}, Local data date: {local_data}")
        if str(latest_data) == str(local_data):
            return False
        return True

    def update(self, proxy = "B"):
        """
        Update market data for the specified region
        """
        logger.info(f"Updating [{self.region}] market data")
        if self.need_update():
            logger.info("Updating Qlib data...")
        else:
            logger.info("Qlib data is up to date")
            self.status()
            return

        proxy_a = "https://gh-proxy.org/"
        proxy_b = "https://hk.gh-proxy.org/"
        proxy_c = "https://cdn.gh-proxy.org/"
        proxy_d = "https://edgeone.gh-proxy.org/"
        url = "https://github.com/chenditc/investment_data/releases/latest/download/qlib_bin.tar.gz"

        proxy_map = {
            "A": proxy_a,
            "B": proxy_b,
            "C": proxy_c,
            "D": proxy_d
        }
        use_proxy = proxy_map.get(proxy.upper(), proxy)
        # 拼接完整下载地址，去除重复斜杠
        full_download_url = use_proxy.rstrip("/") + "/" + url
        tmp_file = Path("~/tmp/qlib_bin.tar.gz").expanduser()
        tmp_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"使用代理 [{proxy}] 下载数据包: {full_download_url}")

        # ----------纯Python下载，不调用shell wget/curl----------
        def _download_file(url: str, output_path: Path, timeout=120):
            resp = requests.get(url, stream=True, timeout=timeout, allow_redirects=True)
            resp.raise_for_status()  # 4xx/5xx HTTP错误直接抛异常
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)

        _download_file(full_download_url, tmp_file)

         # 文件大小校验，防止下载到错误html页面
        file_size = tmp_file.stat().st_size
        logger.info(f"下载文件大小: {file_size} bytes")
        if file_size < 1024 * 1024:
            raise RuntimeError("下载得到的文件过小，大概率代理限流429，请切换proxy参数(A/B/C/D)")
        # 确保目标目录存在，再解压
        target_dir = Path("~/.qlib/qlib_data/cn_data").expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        tar_cmd = f"tar -zxvf '{tmp_file}' -C '{target_dir}' --strip-components=1"
        ret = run_command(tar_cmd)
        exit_code = ret[0]
        if exit_code != 0:
            raise RuntimeError(f"解压失败，返回码:{exit_code}, stderr={ret[2]}")
        logger.info("数据更新完成。")
        self.status()

    def status(self) -> None:
        """Check local data update status"""
        logger.info(f"Checking local data status... {get_local_data_date(self.kwargs['provider_uri'])}")
