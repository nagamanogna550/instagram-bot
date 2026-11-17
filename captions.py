"""Caption drafting, hashtag building and comment selection."""
import random
import re

MAX_CAPTION_LENGTH = 2200
MAX_HASHTAGS = 30

OPENERS = {
    "friendly": ["Happy to share this with you:", "Today's little highlight:", "Something I really enjoy:"],
    "professional": ["Sharing a quick update:", "Here is something worth your attention:", "A brief note on"],
    "playful": ["Okay, this one made my day:", "Plot twist:", "Not gonna lie, I love this:"],
}
CALLS_TO_ACTION = [
    "What do you think? Let me know below.",
    "Tag someone who needs to see this.",
    "Save this for later and share your thoughts.",
]
# Plain text only: emoji can fail to type through WebDriver.
COMMENTS = [
    "Love this!", "Great shot, thanks for sharing.", "This is really well done.",
    "Such a nice post.", "Really inspiring, keep it up!", "Beautiful work.",
    "This made my day.", "Great content!",
]


def clean_hashtag(text):
    """'Street Food!' -> '#streetfood'. Returns '' if nothing usable is left."""
    body = re.sub(r"[^0-9a-z_]", "", text.lower())
    return f"#{body}" if body else ""


def build_hashtags(keywords, limit=15):
    tags = []
    for word in keywords:
        tag = clean_hashtag(word)
        if tag and tag not in tags:
            tags.append(tag)
    return tags[: min(limit, MAX_HASHTAGS)]


def validate_caption(text):
    if not text.strip():
        raise ValueError("Caption cannot be empty.")
    if len(text) > MAX_CAPTION_LENGTH:
        raise ValueError(f"Caption is {len(text)} characters; the limit is {MAX_CAPTION_LENGTH}.")
    if len(re.findall(r"#\w+", text)) > MAX_HASHTAGS:
        raise ValueError(f"Too many hashtags (max {MAX_HASHTAGS}).")
    return text


def draft_caption(topic, tone="friendly", keywords=None, call_to_action=True, rng=None):
    rng = rng or random.Random()
    if not topic.strip():
        raise ValueError("Topic cannot be empty.")
    if tone not in OPENERS:
        raise ValueError(f"Tone must be one of {sorted(OPENERS)}.")
    body = f"{rng.choice(OPENERS[tone])} {topic.strip().rstrip('.!?')}."
    if call_to_action:
        body += " " + rng.choice(CALLS_TO_ACTION)
    tags = build_hashtags(keywords if keywords else topic.split())
    caption = body + ("\n\n" + " ".join(tags) if tags else "")
    return validate_caption(caption)


def pick_comment(used, rng=None):
    """Return a comment not yet used in this session, or None if all are used."""
    rng = rng or random.Random()
    options = [c for c in COMMENTS if c not in used]
    return rng.choice(options) if options else None
