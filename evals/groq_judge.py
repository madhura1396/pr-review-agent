import os
from typing import Optional, Type

from deepeval.models.base_model import DeepEvalBaseLLM
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

from config import EVAL_JUDGE_MODEL as JUDGE_MODEL

load_dotenv()


class GroqJudge(DeepEvalBaseLLM):
    """
    DeepEval judge backed by Groq.

    DeepEval's metrics default to an OpenAI judge, and this project only carries
    a GROQ_API_KEY. Passing an instance of this class as a metric's `model`
    makes DeepEval treat it as a non-native model, so no OpenAI key is needed.

    DeepEval calls generate()/a_generate() with an optional `schema` (a pydantic
    model) when it wants structured output. Accepting that keeps GEval on its
    structured path; without it GEval falls back to scraping JSON out of raw
    text, which these models do not reliably produce.

    Structured output goes through json_schema, not LangChain's default
    function_calling mode: gpt-oss-120b returns the JSON as message content
    rather than calling the tool, so function_calling fails the whole request
    with `tool_use_failed` even though the generated JSON was valid.
    """

    # Overridable because model support varies; json_mode is the usual fallback.
    structured_method = os.getenv("EVAL_STRUCTURED_METHOD", "json_schema")

    def __init__(self, model: str = JUDGE_MODEL):
        super().__init__(model)

    def load_model(self) -> ChatGroq:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise PermissionError("GROQ_API_KEY is not set in environment / .env")
        # temperature=0 so a judge re-run on the same output scores the same way.
        return ChatGroq(model=self.model_name, api_key=api_key, temperature=0)

    def _structured(self, schema: Type[BaseModel]):
        return self.model.with_structured_output(schema, method=self.structured_method)

    def generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        if schema is None:
            return self.model.invoke(prompt).content
        try:
            return self._structured(schema).invoke(prompt)
        except Exception:
            # Not every Groq model honours json_schema; json_mode is broader.
            return self.model.with_structured_output(schema, method="json_mode").invoke(prompt)

    async def a_generate(self, prompt: str, schema: Optional[Type[BaseModel]] = None):
        if schema is None:
            response = await self.model.ainvoke(prompt)
            return response.content
        try:
            return await self._structured(schema).ainvoke(prompt)
        except Exception:
            structured = self.model.with_structured_output(schema, method="json_mode")
            return await structured.ainvoke(prompt)

    def get_model_name(self) -> str:
        return f"Groq ({self.model_name})"
