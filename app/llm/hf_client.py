from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline


class HuggingFaceLLMClient:
    def __init__(
        self,
        model: str,
        max_new_tokens: int = 1200,
        temperature: float = 0.2,
        device: str = "auto",
    ):
        self.model_name = model
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.device = device
        self._generator = None

    def _resolve_torch_dtype(self):
        if torch.cuda.is_available():
            return torch.float16
        return torch.float32

    def _resolve_device_map(self):
        if self.device == "auto":
            return "auto"
        if self.device in {"cpu", "mps", "cuda"}:
            return self.device
        return "auto"

    def _load_generator(self):
        if self._generator is not None:
            return self._generator

        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=self._resolve_torch_dtype(),
            device_map=self._resolve_device_map(),
        )

        self._generator = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
        )
        return self._generator

    def generate(self, prompt: str) -> str:
        generator = self._load_generator()

        messages = [
            {
                "role": "system",
                "content": "You are WeeklyREBOT, a concise weekly report assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ]

        tokenizer = generator.tokenizer

        if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
            model_input = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            model_input = prompt

        outputs = generator(
            model_input,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=self.temperature > 0,
            return_full_text=False,
        )

        if not outputs:
            return ""

        generated = outputs[0].get("generated_text", "")

        if isinstance(generated, list):
            # Some chat models return a list of chat messages.
            last = generated[-1] if generated else {}
            if isinstance(last, dict):
                return str(last.get("content", "")).strip()
            return str(last).strip()

        return str(generated).strip()