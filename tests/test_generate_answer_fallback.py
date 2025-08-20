import pytest
from agent.api.auto import _generate_answer


class DummyClient:
    class chat:
        class completions:
            @staticmethod
            def create(*args, **kwargs):
                raise Exception("LLM unavailable")


class DummySettings:
    llm_answer_model = "gpt-test"


def test_fallback_pronoun_conversion():
    candidates = [{"text": "I lost my keys"}]
    result = _generate_answer("Where are my keys?", candidates, "en", DummyClient(), DummySettings())
    assert result == "I found the following information:\n1. You lost your keys"


def test_fallback_multi_memory_aggregation():
    candidates = [{"text": "I like my cat"}, {"text": "My dog likes me"}]
    result = _generate_answer("Tell me about my pets", candidates, "en", DummyClient(), DummySettings())
    assert result == (
        "I found the following information:\n1. You like your cat\n2. Your dog likes you"
    )
