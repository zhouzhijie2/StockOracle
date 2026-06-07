"""大模型API调用模块。

支持的免费模型：
- 阿里通义千问 (qwen-turbo)
- 讯飞星火 (spark lite)
- 百度文心一言 (ernie-lite)

使用示例：
    from stock_oracle.llm import LLMClient
    client = LLMClient(
        provider="qwen",
        api_key="your-api-key"
    )
    response = client.explain_stock_selection(
        stock_name="平安银行",
        rule_name="均线金叉",
        reasons=["MA5上穿MA20"],
        kline_data=...
    )
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import requests
import json
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from stock_oracle.logger import log


@dataclass
class LLMResponse:
    success: bool
    text: str
    error: Optional[str] = None
    cost: float = 0.0
    duration: float = 0.0


class BaseLLMProvider:
    """LLM 提供者基类。"""

    def __init__(self, api_key: str, api_secret: Optional[str] = None,
                 proxy: Optional[Dict[str, str]] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.proxy = proxy or {}

    def explain_stock_selection(
        self,
        stock_name: str,
        stock_code: str,
        rule_name: str,
        reasons: list,
        extras: Dict[str, Any],
        kline_preview: str
    ) -> LLMResponse:
        """解释选股理由。"""
        raise NotImplementedError()


class QwenProvider(BaseLLMProvider):
    """阿里通义千问。"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self.url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model = "qwen-turbo"

    def explain_stock_selection(
        self,
        stock_name: str,
        stock_code: str,
        rule_name: str,
        reasons: list,
        extras: Dict[str, Any],
        kline_preview: str
    ) -> LLMResponse:
        start = time.time()
        try:
            prompt = f"""你是一位专业的股票分析师。请用简洁易懂的语言，解释为什么选出了这只股票。

【股票信息】
- 名称：{stock_name}
- 代码：{stock_code}

【选股规则】
- 规则名称：{rule_name}
- 命中原因：{', '.join(reasons)}

【附加数据】
- {extras}

【K线预览（最近10天）】
{kline_preview}

请从以下几个方面解释：
1. 技术面分析：解释为什么这个技术指标信号是重要的
2. 趋势判断：分析当前股价所处的位置
3. 风险提示：给出相应的风险提示

回答要求：
- 不超过300字
- 用中文口语化表达
- 重点突出关键信息
- 不要使用Markdown格式
"""

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500,
            }

            response = requests.post(
                self.url,
                headers=headers,
                json=data,
                proxies=self.proxy,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                text = result["choices"][0]["message"]["content"].strip()
                duration = time.time() - start
                return LLMResponse(success=True, text=text, duration=duration)
            else:
                return LLMResponse(
                    success=False,
                    text="",
                    error=f"API返回异常: {result}"
                )
        except Exception as e:
            duration = time.time() - start
            log.error(f"通义千问API调用失败: {e}")
            return LLMResponse(success=False, text="", error=str(e), duration=duration)


class SparkProvider(BaseLLMProvider):
    """讯飞星火。"""

    def __init__(self, api_key: str, api_secret: Optional[str] = None, **kwargs):
        super().__init__(api_key, api_secret, **kwargs)
        self.url = "https://spark-api-open.xf-yun.com/v1/chat/completions"
        self.model = "spark-lite"

    def explain_stock_selection(
        self,
        stock_name: str,
        stock_code: str,
        rule_name: str,
        reasons: list,
        extras: Dict[str, Any],
        kline_preview: str
    ) -> LLMResponse:
        start = time.time()
        try:
            prompt = f"""你是一位专业的股票分析师。请用简洁易懂的语言，解释为什么选出了这只股票。

【股票信息】
- 名称：{stock_name}
- 代码：{stock_code}

【选股规则】
- 规则名称：{rule_name}
- 命中原因：{', '.join(reasons)}

【附加数据】
- {extras}

【K线预览（最近10天）】
{kline_preview}

请从以下几个方面解释：
1. 技术面分析：解释为什么这个技术指标信号是重要的
2. 趋势判断：分析当前股价所处的位置
3. 风险提示：给出相应的风险提示

回答要求：
- 不超过300字
- 用中文口语化表达
- 重点突出关键信息
- 不要使用Markdown格式
"""

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}:{self.api_secret}",
            }
            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 500,
            }

            response = requests.post(
                self.url,
                headers=headers,
                json=data,
                proxies=self.proxy,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                text = result["choices"][0]["message"]["content"].strip()
                duration = time.time() - start
                return LLMResponse(success=True, text=text, duration=duration)
            else:
                return LLMResponse(
                    success=False,
                    text="",
                    error=f"API返回异常: {result}"
                )
        except Exception as e:
            duration = time.time() - start
            log.error(f"讯飞星火API调用失败: {e}")
            return LLMResponse(success=False, text="", error=str(e), duration=duration)


# 提供者映射
PROVIDERS = {
    "qwen": QwenProvider,
    "spark": SparkProvider,
}


class LLMClient:
    """LLM 客户端。"""

    def __init__(self, provider: str = "qwen",
                 api_key: str = "", api_secret: str = "",
                 proxy: Optional[Dict[str, str]] = None):
        provider_class = PROVIDERS.get(provider)
        if not provider_class:
            raise ValueError(f"不支持的LLM提供者: {provider}")
        self.provider = provider_class(api_key, api_secret=api_secret, proxy=proxy)

    def explain_stock_selection(
        self,
        stock_name: str,
        stock_code: str,
        rule_name: str,
        reasons: list,
        extras: Optional[Dict[str, Any]] = None,
        kline_df = None
    ) -> LLMResponse:
        """解释选股理由。"""
        # 准备K线预览
        kline_preview = ""
        if kline_df is not None and not kline_df.empty:
            recent = kline_df.tail(10).copy()
            for _, row in recent.iterrows():
                date = str(row.get("date", row.get("trade_date", "")))[:10]
                close = float(row.get("close", 0))
                open_p = float(row.get("open", 0))
                high = float(row.get("high", 0))
                low = float(row.get("low", 0))
                vol = int(row.get("volume", 0) or 0)
                kline_preview += f"{date} | 开:{open_p:.2f} 高:{high:.2f} 低:{low:.2f} 收:{close:.2f} 量:{vol}\n"

        return self.provider.explain_stock_selection(
            stock_name=stock_name,
            stock_code=stock_code,
            rule_name=rule_name,
            reasons=reasons,
            extras=extras or {},
            kline_preview=kline_preview
        )
