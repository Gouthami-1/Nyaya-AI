
from google import genai
from config import Config

class GeminiServiceError(Exception):
    """Raised when the Gemini service fails."""
    pass


SYSTEM_PROMPT = """
You are Nyaya AI, an Indian legal information assistant.

YOUR MAIN RESPONSIBILITY
Answer the user's legal question even if the local legal database returns
no matching records. Do not refuse to answer simply because a database
search returns no results.

SCOPE
Help with a broad range of Indian legal topics, including:
- Dowry demands, dowry harassment and domestic violence
- Marriage, divorce, maintenance and family disputes
- Harassment, stalking, threats and assault
- Theft, fraud, cheating and cybercrime
- Women's rights, children's rights and workplace harassment
- Consumer complaints, employment, property and tenant disputes
- Constitutional rights, criminal law and civil law
- Police complaints, FIRs and general legal procedures

HOW TO ANSWER
1. Understand the user's actual problem, even if it is written in simple,
   informal, misspelled or grammatically incorrect English.
2. Explain the relevant Indian laws in plain, understandable language.
3. Mention the name of an Act and its section number only when reasonably
   confident that the provision is relevant and accurate.
4. Never invent sections, punishments, legal quotations, court cases or URLs.
5. If you cannot confirm an exact section or current penalty, say so clearly
   and explain the general legal position instead.
6. Use the supplied legal database records as supporting context, not as the
   only possible source of an answer. If no records match, still help using
   your general legal knowledge and clearly identify uncertainty.
7. Distinguish general information from legal advice. Explain that the
   outcome depends on the facts and applicable law.
8. Do not claim that you checked an official source unless you actually did.
9. If the user provides insufficient details, give useful general information
   first, then ask one relevant follow-up question if necessary.
10. Respond in the language requested by the user. Supported response
    languages are English, Hindi and Telugu.

DOWRY QUESTIONS
For questions about dowry, explain that the Dowry Prohibition Act, 1961
is a key Indian law concerning giving, taking and demanding dowry.
Depending on the facts, the Protection of Women from Domestic Violence
Act, 2005 and relevant provisions of the Bharatiya Nyaya Sanhita, 2023
may also be relevant.

Explain possible options such as documenting incidents safely, seeking
legal aid, contacting the appropriate authorities and consulting a lawyer.
Do not imply that every marital dispute automatically constitutes a crime.
Do not blame or shame the person experiencing abuse.

SAFETY
If someone is in immediate danger in India, advise them to contact
emergency services at 112 when safe to do so. Avoid advice that could
increase danger to a person experiencing abuse.

RESPONSE FORMAT
Use this structure where appropriate:

1. What the law says
2. Relevant Act and sections, if known
3. How the law may apply to the situation
4. Practical next steps
5. Important limitations or safety considerations

For simple questions, answer naturally without forcing every heading.
"""


def _format_sources(sources):
    """Format retrieved legal records without requiring any matches."""
    if not sources:
        return (
            "No matching local database records were found. "
            "Answer the user's question anyway using your legal knowledge. "
            "Be transparent about any uncertainty."
        )

    formatted = []

    for source in sources:
        if not isinstance(source, dict):
            continue

        fields = [
            f"Act: {source.get('act_name', 'Not specified')}",
            f"Year: {source.get('act_year', 'Not specified')}",
            f"Section: {source.get('section_number', 'Not specified')}",
            f"Title: {source.get('section_title', 'Not specified')}",
            f"Legal text: {source.get('legal_text', 'Not provided')}",
            f"Explanation: {source.get('explanation', 'Not provided')}",
            f"Verification status: "
            f"{source.get('verification_status', 'Unknown')}",
        ]

        formatted.append("\n".join(fields))

    if not formatted:
        return (
            "No usable matching records were found. "
            "Answer the question anyway and identify uncertainty."
        )

    return "\n\n---\n\n".join(formatted)


def _format_history(history):
    """Keep recent conversation context."""
    if not isinstance(history, list):
        return ""

    messages = []

    for item in history[-8:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role", item.get("sender", ""))
        content = item.get("content", item.get("message", ""))

        if not isinstance(content, str) or not content.strip():
            continue

        if role in ("assistant", "ai", "bot"):
            role = "Nyaya AI"
        elif role in ("user", "human"):
            role = "User"
        else:
            continue

        messages.append(f"{role}: {content[:3000]}")

    return "\n".join(messages)


def answer_legal_question(
    question,
    language="English",
    sources=None,
    history=None,
):
    """
    Generate a legal information response using Gemini.

    Compatible with calls using:
    answer_legal_question(question, language, sources, history)
    """

    if not isinstance(question, str) or not question.strip():
        return "Please describe your legal question so I can help."

    question = question.strip()[:10000]

    supported_languages = {
        "english": "English",
        "hindi": "Hindi",
        "telugu": "Telugu",
    }

    language = supported_languages.get(
        str(language).strip().lower(),
        "English",
    )

    api_key = getattr(Config, "GEMINI_API_KEY", None)
    model = getattr(
        Config,
        "GEMINI_MODEL",
        "gemini-flash-lite-latest",
    )

    if not api_key:
        return (
            "The AI service is not configured correctly. "
            "Please check GEMINI_API_KEY in your .env configuration."
        )

    source_text = _format_sources(sources)
    history_text = _format_history(history)

    prompt = f"""
{SYSTEM_PROMPT}

RESPONSE LANGUAGE: {language}

RETRIEVED LEGAL DATABASE INFORMATION:
{source_text}

RECENT CONVERSATION:
{history_text if history_text else "No previous conversation."}

USER'S LEGAL QUESTION:
{question}

Answer the user's actual question now. Do not return an empty response.
If the database has no matching records, still provide a useful answer.
Do not invent statutory sections or claim that uncertain information
has been independently verified.
"""

    try:
        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        answer = getattr(response, "text", None)

        if answer and answer.strip():
            return answer.strip()

        return (
            "I couldn't generate a complete answer just now. "
            "Please try asking your question in a different way."
        )

    except Exception as error:
        print(f"Gemini API error: {type(error).__name__}: {error}")

        return (
            "I'm temporarily unable to generate an answer. "
            "Please check your internet connection and Gemini API "
            "configuration, then try again."
        )
