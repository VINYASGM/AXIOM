"""
Cloud Model Providers

Implements cloud LLM providers for multi-tier model routing.
Each provider wraps the respective API (OpenAI, Anthropic, Google, DeepSeek).
"""
import os
import asyncio
import time
from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Import base types from router
import sys
sys.path.append('..')
from router import LLMProvider, ChatRequest, ChatResponse, ChatMessage


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider (Haiku, Sonnet, Opus)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None
    
    @property
    def name(self) -> str:
        return "anthropic"
    
    @property
    def models(self) -> List[str]:
        return [
            "claude-3-5-haiku-latest",
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514"
        ]
    
    async def _get_client(self):
        if self._client is None and self.api_key:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Run: pip install anthropic")
        return self._client
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        client = await self._get_client()
        if not client:
            raise ValueError("Anthropic API key not configured")
        
        start = time.time()
        
        # Convert messages (separate system from user/assistant)
        system_msg = ""
        messages = []
        for msg in request.messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})
        
        response = await client.messages.create(
            model=request.model,
            max_tokens=request.max_tokens,
            system=system_msg if system_msg else None,
            messages=messages
        )
        
        latency = (time.time() - start) * 1000
        
        return ChatResponse(
            content=response.content[0].text if response.content else "",
            model=request.model,
            provider=self.name,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            },
            latency_ms=latency,
            finish_reason=response.stop_reason or "stop"
        )
    
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream response tokens."""
        client = await self._get_client()
        if not client:
            raise ValueError("Anthropic API key not configured")
        
        system_msg = ""
        messages = []
        for msg in request.messages:
            if msg.role == "system":
                system_msg = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})
        
        async with client.messages.stream(
            model=request.model,
            max_tokens=request.max_tokens,
            system=system_msg if system_msg else None,
            messages=messages
        ) as stream:
            async for text in stream.text_stream:
                yield text
    
    async def health_check(self) -> bool:
        return self.api_key is not None


class GoogleProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self._client = None
    
    @property
    def name(self) -> str:
        return "google"
    
    @property
    def models(self) -> List[str]:
        return [
            "gemini-2.0-flash",
            "gemini-2.5-pro-preview-05-06"
        ]
    
    async def _get_client(self):
        if self._client is None and self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai
            except ImportError:
                raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        return self._client
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        client = await self._get_client()
        if not client:
            raise ValueError("Google API key not configured")
        
        start = time.time()
        
        # Combine messages into conversation
        model = client.GenerativeModel(request.model)
        
        history = []
        last_user_msg = ""
        for msg in request.messages:
            if msg.role == "system":
                # Gemini handles system as preamble
                history.append({"role": "user", "parts": [f"System instructions: {msg.content}"]})
                history.append({"role": "model", "parts": ["Understood. I'll follow these instructions."]})
            elif msg.role == "user":
                last_user_msg = msg.content
            elif msg.role == "assistant":
                if last_user_msg:
                    history.append({"role": "user", "parts": [last_user_msg]})
                    last_user_msg = ""
                history.append({"role": "model", "parts": [msg.content]})
        
        chat = model.start_chat(history=history)
        response = await asyncio.to_thread(chat.send_message, last_user_msg)
        
        latency = (time.time() - start) * 1000
        
        # Estimate tokens (Gemini doesn't always return usage)
        usage = {
            "input_tokens": len(last_user_msg) // 4,
            "output_tokens": len(response.text) // 4
        }
        
        return ChatResponse(
            content=response.text,
            model=request.model,
            provider=self.name,
            usage=usage,
            latency_ms=latency
        )
    
    async def health_check(self) -> bool:
        return self.api_key is not None


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider (V3, Coder)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = "https://api.deepseek.com"
    
    @property
    def name(self) -> str:
        return "deepseek"
    
    @property
    def models(self) -> List[str]:
        return ["deepseek-chat", "deepseek-coder"]
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")
        
        start = time.time()
        
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx package not installed. Run: pip install httpx")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": request.model,
                    "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": False
                },
                timeout=120.0
            )
            response.raise_for_status()
            data = response.json()
        
        latency = (time.time() - start) * 1000
        
        choice = data["choices"][0]
        usage = data.get("usage", {})
        
        return ChatResponse(
            content=choice["message"]["content"],
            model=request.model,
            provider=self.name,
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0)
            },
            latency_ms=latency,
            finish_reason=choice.get("finish_reason", "stop")
        )
    
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream response tokens."""
        if not self.api_key:
            raise ValueError("DeepSeek API key not configured")
        
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx package not installed")
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": request.model,
                    "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": True
                },
                timeout=120.0
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            import json
                            chunk = json.loads(data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except:
                            continue
    
    async def health_check(self) -> bool:
        return self.api_key is not None


class OpenAIEnhancedProvider(LLMProvider):
    """Enhanced OpenAI provider with streaming and GPT-4o support."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def models(self) -> List[str]:
        return ["gpt-4o", "gpt-4o-mini", "o1", "gpt-4-turbo"]
    
    async def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package not installed. Run: pip install openai")
        return self._client
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        client = await self._get_client()
        if not client:
            raise ValueError("OpenAI API key not configured")
        
        start = time.time()
        
        response = await client.chat.completions.create(
            model=request.model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature if "o1" not in request.model else 1,  # o1 doesn't support temp
            max_tokens=request.max_tokens
        )
        
        latency = (time.time() - start) * 1000
        
        choice = response.choices[0]
        
        return ChatResponse(
            content=choice.message.content or "",
            model=request.model,
            provider=self.name,
            usage={
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0
            },
            latency_ms=latency,
            finish_reason=choice.finish_reason or "stop"
        )
    
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Stream response tokens."""
        client = await self._get_client()
        if not client:
            raise ValueError("OpenAI API key not configured")
        
        # o1 doesn't support streaming
        if "o1" in request.model:
            response = await self.chat(request)
            yield response.content
            return
        
        stream = await client.chat.completions.create(
            model=request.model,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def health_check(self) -> bool:
        return self.api_key is not None


# =============================================================================
# PROVIDER FACTORY
# =============================================================================

def create_provider(provider_name: str, **kwargs) -> Optional[LLMProvider]:
    """Create a provider instance by name."""
    providers = {
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "deepseek": DeepSeekProvider,
        "openai": OpenAIEnhancedProvider
    }
    
    provider_class = providers.get(provider_name)
    if provider_class:
        return provider_class(**kwargs)
    return None


def get_available_providers() -> Dict[str, bool]:
    """Check which providers have API keys configured."""
    return {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "google": bool(os.getenv("GOOGLE_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }
