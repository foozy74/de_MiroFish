"""
LLM-Client-Konfiguration
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI



class LLMClient:
    """LLM-Client"""
    
    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        timeout: int = 120
    ):
        """
        Initialisiert den LLM-Client.

        Args:
            api_key: API-Schlüssel (optional, falls als Umgebungsvariable gesetzt)
            base_url: API-Basis-URL
            model: Modellname
            temperature: Temperaturparameter
            max_tokens: Maximale Token-Anzahl
            timeout: Timeout in Sekunden
        """
        # Lazy Import um Zirkelabhängigkeiten zu vermeiden
        from app.tenant.settings_override import TenantConfig
        
        cfg = TenantConfig()
        
        self.api_key = api_key or cfg.LLM_API_KEY
        self.base_url = base_url or cfg.LLM_BASE_URL
        self.model = model or cfg.LLM_MODEL_NAME
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY ist nicht konfiguriert")
            
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Sendet Chat-Anfrage
        
        Args:
            messages: Nachrichtenliste
            temperature: Temperaturparameter
            max_tokens: Maximale Token-Anzahl
            response_format: Antwortformat (z.B. JSON-Modus)
            
        Returns:
            Modell-Antworttext
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # Einige Modelle (wie MiniMax M2.5) enthalten思考内容 im content, die entfernt werden müssen
        content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
        return content
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Sendet eine Chat-Anfrage und gibt JSON zurück.

        Args:
            messages: Nachrichtenliste
            temperature: Temperaturparameter
            max_tokens: Maximale Token-Anzahl

        Returns:
            Analysiertes JSON-Objekt
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}
        )
        # Markdown-Codeblock-Marker bereinigen
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"Ungültiges JSON-Format vom LLM zurückgegeben: {cleaned_response}")
