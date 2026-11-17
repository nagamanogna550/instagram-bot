"""One engagement session: search a hashtag, then like / comment / follow."""
import random

from captions import pick_comment


def run_session(bot, hashtag, likes=5, comments=2, follows=2, rng=None):
    rng = rng or random.Random()
    summary = {"like": 0, "comment": 0, "follow": 0}
    posts = bot.search_hashtag(hashtag, max_posts=max(likes, comments, follows))
    comment_at = set(rng.sample(range(len(posts)), min(comments, len(posts))))
    follow_at = set(rng.sample(range(len(posts)), min(follows, len(posts))))
    used_comments = set()

    for i, url in enumerate(posts):
        actions = []
        if i < likes:
            actions.append("like")
        if i in comment_at:
            actions.append("comment")
        if i in follow_at:
            actions.append("follow")
        rng.shuffle(actions)                       # vary the order of actions

        for action in actions:
            if action == "like":
                done = bot.like_post(url)
            elif action == "comment":
                text = pick_comment(used_comments, rng)
                done = bool(text) and bot.comment_post(url, text)
                if done:
                    used_comments.add(text)
            else:
                done = bot.follow_user(bot.get_post_author(url))
            summary[action] += int(bool(done))
    return summary
