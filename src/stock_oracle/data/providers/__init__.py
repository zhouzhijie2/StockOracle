"""数据源包。"""
from .base import DataProvider
from .sina_provider import SinaProvider
from .akshare_provider import AkShareProvider
from .efinance_provider import EFinanceProvider
from .composite_provider import CompositeProvider

PROVIDERS = {
    "composite": CompositeProvider(),
    "sina": SinaProvider(),
    "akshare": AkShareProvider(),
    "efinance": EFinanceProvider(),
}


def get_provider(name: str = "composite") -> DataProvider:
    return PROVIDERS.get(name) or PROVIDERS["composite"]


__all__ = ["DataProvider", "SinaProvider", "AkShareProvider", "EFinanceProvider",
           "CompositeProvider", "PROVIDERS", "get_provider"]
