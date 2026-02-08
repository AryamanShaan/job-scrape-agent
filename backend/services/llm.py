"""
LLM factory — the single place where we create a LangChain chat model.

Supports 4 providers:
- ollama: free, runs locally (requires Ollama installed)
- gemini: Google's API
- claude: Anthropic's API
- openai: OpenAI's API

Every other file just calls `llm.invoke(prompt)` without caring which provider is active.
"""

from langchain_core.language_models import BaseChatModel

from backend.config import settings


def get_llm() -> BaseChatModel:
    """
    Create and return a LangChain chat model based on current settings.
    The returned object has an .invoke() method that accepts a string or messages.
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=settings.LLM_API_KEY,
        )

    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-20250514",
            anthropic_api_key=settings.LLM_API_KEY,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.LLM_API_KEY,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use ollama/gemini/claude/openai.")
