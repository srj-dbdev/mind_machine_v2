import re


def clean_text(text):
    """
    Clean text for Text-to-Speech.
    """

    if not text:
        return ""

    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"\*", "", text)
    text = re.sub(r"`", "", text)
    text = re.sub(r"#", "", text)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def build_narration(script):
    """
    Build narration from the structured script.
    """

    narration = []

    hook = clean_text(script.get("hook", ""))

    if hook:
        narration.append(hook)

    for scene in script.get("scenes", []):

        text = clean_text(scene.get("text", ""))

        if text:
            narration.append(text)

    cta = clean_text(script.get("cta", ""))

    if cta:
        narration.append(cta)

    return "\n\n".join(narration)