from services.gemini_service import SYSTEM_PROMPT

def test_prompt_forbids_fabricated_sections():
    assert 'Never invent laws, sections' in SYSTEM_PROMPT

def test_prompt_treats_user_statements_as_allegations():
    assert 'allegations, not established facts' in SYSTEM_PROMPT
