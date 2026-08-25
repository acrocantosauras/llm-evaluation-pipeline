"""LLM-as-a-judge evaluator — configurable provider-based evaluation.

Supports rubric-based evaluation with structured output.
Provider-agnostic: supports any OpenAI-compatible API.

Safety:
- Timeout on all external calls
- Retry limits
- JSON/schema validation on output
- Judge failures produce distinguishable error states
"""

import json
import logging
import os
import time

from .base import BaseEvaluator, EvaluationSample, MetricResult

logger = logging.getLogger(__name__)

DEFAULT_RUBRIC = """Rate the following answer on a scale of 1-5:
1 = completely incorrect or irrelevant
2 = mostly incorrect
3 = partially correct
4 = mostly correct and relevant
5 = fully correct, relevant, and well-supported

Question: {question}
Answer: {answer}
Context: {context}

Respond in JSON format:
{{"score": <1-5>, "reason": "<brief explanation>", "criteria": {{"correctness": <1-5>, "relevance": <1-5>, "groundedness": <1-5>}}}}"""


class LLMJudgeEvaluator(BaseEvaluator):
    name = "llm_judge"
    version = "1.0.0"

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 3,
        timeout: float = 30.0,
        rubric: str | None = None,
    ):
        self.provider = provider or os.getenv("JUDGE_PROVIDER", "openai")
        self.model = model or os.getenv("JUDGE_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout
        self.rubric = rubric or DEFAULT_RUBRIC

    def evaluate(self, sample: EvaluationSample) -> MetricResult:
        if not sample.answer:
            return self._make_result(0.0, passed=False, error="no_answer")

        prompt = self.rubric.format(
            question=sample.question,
            answer=sample.answer,
            context=" ".join(c.get("text", "") for c in sample.context)[:2000],
        )

        for attempt in range(self.max_retries):
            try:
                # Measure the actual judge operation (the LLM call) with a
                # monotonic clock so retries and parsing don't distort it.
                call_started = time.perf_counter()
                result = self._call_llm(prompt)
                latency_ms = round((time.perf_counter() - call_started) * 1000, 4)

                parsed = self._parse_response(result)
                if parsed is not None:
                    score = parsed.get("score", 0) / 5.0  # Normalize to 0-1
                    return self._make_result(
                        round(score, 4),
                        passed=score >= 0.6,
                        raw_score=parsed.get("score"),
                        reason=parsed.get("reason", ""),
                        criteria=parsed.get("criteria", {}),
                        provider=self.provider,
                        model=self.model,
                        latency_ms=latency_ms,
                    )
            except Exception as exc:
                logger.warning("Judge attempt %d failed: %s", attempt + 1, exc)
                if attempt == self.max_retries - 1:
                    return self._error_result(f"Judge failed after {self.max_retries} attempts: {exc}")

        return self._error_result("Judge failed: max retries exceeded")

    def _call_llm(self, prompt: str) -> str:
        """Call the LLM provider. Override for different providers."""
        if self.provider == "openai":
            return self._call_openai(prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unsupported judge provider: {self.provider}")

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI-compatible API."""
        import openai

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=500,
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API."""
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=api_key, timeout=self.timeout)
        response = client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
        )
        return response.content[0].text

    def _parse_response(self, text: str) -> dict | None:
        """Parse LLM output, handling malformed JSON."""
        try:
            # Try direct JSON parse
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        if "```json" in text:
            try:
                json_str = text.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                pass

        # Try to find any JSON object in the text
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            pass

        logger.warning("Failed to parse judge output: %s", text[:200])
        return None
