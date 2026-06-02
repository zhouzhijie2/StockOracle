"""数据源包。"""
from .base import DataProvider
from .akshare_provider import AkShareProvider
from .efinance_provider import EFinanceProvider

PROVIDERS = {
    "akshare": AkShareProvider(),
    "efinance": EFinanceProvider(),
}


def get_provider(name: str = "akshare") -> DataProvider:
    return PROVIDERS.get(name) or PROVIDERS["akshare"]


__all__ = ["DataProvider", "AkShareProvider", "EFinanceProvider",
           "PROVIDERS", "get_provider"]
