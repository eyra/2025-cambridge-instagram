"""Helpers that build Instagram export fixtures for tests.

Everything in here is fabricated data — no PII. The fixtures reproduce
the structural shape of real Instagram exports so the extraction code
can be exercised without needing a participant zip.

Two formats are covered:

- `make_legacy_format_zip` — the older shape, where list-of-events files
  are wrapped in a dict with a well-known key (e.g. `likes_media_likes`)
  and each event's timestamp lives under `string_list_data[0].timestamp`
  or `string_map_data.Time.timestamp`.

- `make_newer_format_zip` — the newer shape Instagram started exporting
  in 2026, where those same files are top-level lists and each entry
  carries `timestamp` directly at the root.

Both functions return the absolute path to a tempfile zip. Callers are
responsible for unlinking the file.
"""

import json
import os
import random
import tempfile
import zipfile


# Deterministic Unix timestamps so tests can assert counts and ranges.
# 2026-01-01 00:00:00 UTC == 1767225600
_BASE_TS = 1767225600

# Bogus name pools for randomized fixtures.
_FIRST_NAMES = [
    "Alex", "Bailey", "Casey", "Dakota", "Ellis", "Frankie", "Gray",
    "Harper", "Indigo", "Jules", "Kai", "Logan", "Morgan", "Nova",
    "Oakley", "Parker", "Quinn", "Reese", "Sage", "Taylor", "Unity",
    "Val", "Wren", "Xen", "Yuki", "Zephyr",
]
_LAST_NAMES = [
    "Ash", "Brook", "Cole", "Drew", "East", "Fern", "Glen",
    "Hale", "Isle", "Jade", "Knox", "Lark", "Moss", "North",
    "Orr", "Pine", "Quill", "Rook", "Sable", "Teal", "Vale",
    "Wade", "Yale", "Zane",
]


def _ts(offset_hours):
    return _BASE_TS + offset_hours * 3600


def _timestamp_list(count, start_offset_hours=0):
    """Return `count` ascending timestamps, one per hour."""
    return [_ts(start_offset_hours + i) for i in range(count)]


def _write_zip(files):
    """Write a dict of {path: json_value_or_str} to a new tempfile zip."""
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            if isinstance(content, (bytes, str)):
                zf.writestr(name, content)
            else:
                zf.writestr(name, json.dumps(content))
    return path


# ---------------------------------------------------------------------------
# Newer format (2026+)
# ---------------------------------------------------------------------------

def _newer_message_file(participant_names, message_count, start_offset_hours=0):
    """Build one message_1.json in the newer format.

    `participant_names[-1]` is the donating user (Instagram's convention).
    """
    timestamps_ms = [t * 1000 for t in _timestamp_list(message_count, start_offset_hours)]
    # Alternate senders so both participants get messages.
    messages = [
        {
            "sender_name": participant_names[i % len(participant_names)],
            "timestamp_ms": timestamps_ms[i],
        }
        for i in range(message_count)
    ]
    return {
        "participants": [{"name": n} for n in participant_names],
        "messages": messages,
        "title": participant_names[0],
        "is_still_participant": True,
        "thread_path": "inbox/conversation",
        "magic_words": [],
    }


def _newer_flat_event(ts):
    """A single entry in the newer top-level-list format."""
    return {"timestamp": ts, "media": [], "label_values": []}


def _newer_creation_event(ts):
    """A single content entry in the newer flat shape."""
    return {"creation_timestamp": ts}


def make_newer_format_zip():
    """Create a zip that mirrors the newer Instagram export shape.

    All source files the extractor reads are represented with their
    newer shape (top-level list, flat `timestamp` / `creation_timestamp`).

    Contents:
      - 2 message threads (5 + 3 = 8 messages)
      - ads_and_topics: 10 videos_watched, 5 posts_viewed, 2 ads_viewed
      - likes: 7 liked_posts, 4 liked_comments
      - content: 6 posts, 4 stories, 2 igtv_videos, 3 reels
      - 9 post_comments
      - 3 following + 4 followers
    """
    files = {
        "your_instagram_activity/messages/inbox/conv_a_1111/message_1.json":
            _newer_message_file(["Alice Test", "Donor User"], message_count=5,
                                start_offset_hours=0),
        "your_instagram_activity/messages/inbox/conv_b_2222/message_1.json":
            _newer_message_file(["Bob Test", "Donor User"], message_count=3,
                                start_offset_hours=10),

        # ads_and_topics — top-level list + flat `timestamp`
        "ads_information/ads_and_topics/videos_watched.json":
            [_newer_flat_event(t) for t in _timestamp_list(10, 100)],
        "ads_information/ads_and_topics/posts_viewed.json":
            [_newer_flat_event(t) for t in _timestamp_list(5, 200)],
        "ads_information/ads_and_topics/ads_viewed.json":
            [_newer_flat_event(t) for t in _timestamp_list(2, 300)],

        # likes — top-level list + flat `timestamp`
        "your_instagram_activity/likes/liked_posts.json":
            [_newer_flat_event(t) for t in _timestamp_list(7, 400)],
        "your_instagram_activity/likes/liked_comments.json":
            [_newer_flat_event(t) for t in _timestamp_list(4, 500)],

        # content — top-level list + flat `creation_timestamp`
        "your_instagram_activity/media/posts_1.json":
            [_newer_creation_event(t) for t in _timestamp_list(6, 600)],
        "your_instagram_activity/media/stories.json":
            [_newer_creation_event(t) for t in _timestamp_list(4, 700)],
        "your_instagram_activity/media/igtv_videos.json":
            [_newer_creation_event(t) for t in _timestamp_list(2, 800)],
        "your_instagram_activity/media/reels.json":
            [_newer_creation_event(t) for t in _timestamp_list(3, 900)],

        # comments — top-level list + flat `timestamp`
        "your_instagram_activity/comments/post_comments_1.json":
            [_newer_flat_event(t) for t in _timestamp_list(9, 1000)],

        # Followers/following — newer shape not yet observed in a real
        # export; keep the legacy shape here until we have evidence.
        "connections/followers_and_following/followers_1.json": {
            "string_list_data": [
                {"value": f"follower_{i}"} for i in range(4)
            ]
        },
        "connections/followers_and_following/following.json": {
            "relationships_following": [
                {"string_list_data": [{"value": f"following_{i}"}]}
                for i in range(3)
            ]
        },
    }
    return _write_zip(files)


# ---------------------------------------------------------------------------
# Legacy format — keep a helper too so regression tests can compare
# ---------------------------------------------------------------------------

def _legacy_string_list_entry(ts):
    return {"string_list_data": [{"timestamp": ts, "value": "x"}]}


def _legacy_string_map_entry(ts):
    return {"string_map_data": {"Time": {"timestamp": ts}}}


def make_legacy_format_zip():
    """Create a zip in the legacy (pre-2026) Instagram export shape."""
    files = {
        "test/messages/inbox/conv_a/message_1.json":
            _newer_message_file(["Alice Test", "Donor User"], message_count=5),

        "test/ads_and_topics/videos_watched.json": {
            "impressions_history_videos_watched":
                [_legacy_string_map_entry(t) for t in _timestamp_list(10, 100)],
        },
        "test/ads_and_topics/posts_viewed.json": {
            "impressions_history_posts_seen":
                [_legacy_string_map_entry(t) for t in _timestamp_list(5, 200)],
        },
        "test/ads_and_topics/ads_viewed.json": {
            "impressions_history_ads_seen":
                [_legacy_string_map_entry(t) for t in _timestamp_list(2, 300)],
        },

        "test/likes/liked_posts.json": {
            "likes_media_likes":
                [_legacy_string_list_entry(t) for t in _timestamp_list(7, 400)],
        },

        "test/followers_and_following/followers_1.json": {
            "string_list_data": [{"value": f"follower_{i}"} for i in range(4)],
        },
        "test/followers_and_following/following.json": {
            "relationships_following": [
                {"string_list_data": [{"value": f"following_{i}"}]}
                for i in range(3)
            ],
        },
    }
    return _write_zip(files)


# ---------------------------------------------------------------------------
# Realistic-scale random fixture (written to a folder on disk)
# ---------------------------------------------------------------------------

_SCALES = {
    "small": dict(conversations=2, messages_per=5, videos=10, posts=5, ads=2,
                  likes=7, followers=4, following=3,
                  content_posts=3, stories=3, igtv=1, reels=2,
                  comments=5, liked_comments=3),
    "realistic": dict(conversations=11, messages_per=(20, 80), videos=800,
                      posts=250, ads=40, likes=40, followers=120,
                      following=160,
                      content_posts=20, stories=15, igtv=5, reels=10,
                      comments=50, liked_comments=30),
    "large": dict(conversations=50, messages_per=(50, 400), videos=5000,
                  posts=1500, ads=300, likes=400, followers=1200,
                  following=1500,
                  content_posts=200, stories=150, igtv=50, reels=100,
                  comments=500, liked_comments=300),
}


def _fake_name(rng):
    return f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"


def _random_timestamps(rng, count, span_days=180):
    """Return `count` ascending uniformly-random Unix timestamps."""
    span_seconds = span_days * 24 * 3600
    return sorted(rng.randint(_BASE_TS, _BASE_TS + span_seconds)
                  for _ in range(count))


def _resolve_messages_per(rng, spec):
    if isinstance(spec, tuple):
        lo, hi = spec
        return rng.randint(lo, hi)
    return spec


def write_newer_format_folder(out_dir, scale="realistic", seed=None):
    """Write a folder tree of bogus Instagram-newer-format files to disk.

    Args:
        out_dir: target directory. Created if missing. Existing contents
            are not cleared.
        scale: "small" / "realistic" / "large" — see _SCALES for counts.
        seed: int for reproducibility (None = truly random).

    Returns the absolute out_dir path.
    """
    if scale not in _SCALES:
        raise ValueError(f"unknown scale {scale!r}; expected one of {sorted(_SCALES)}")
    cfg = _SCALES[scale]
    rng = random.Random(seed)

    donor = _fake_name(rng)

    def _abspath(*parts):
        path = os.path.join(out_dir, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def _dump(path, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    # Message conversations (newer format: inbox/<slug>/message_1.json)
    for _ in range(cfg["conversations"]):
        other = _fake_name(rng)
        slug = f"{other.split()[0].lower()}_{rng.randrange(10**15, 10**16)}"
        msg_count = _resolve_messages_per(rng, cfg["messages_per"])
        timestamps = _random_timestamps(rng, msg_count, span_days=90)
        messages = [
            {
                "sender_name": rng.choice([other, donor]),
                "timestamp_ms": t * 1000,
            }
            for t in timestamps
        ]
        _dump(
            _abspath("your_instagram_activity", "messages", "inbox", slug,
                    "message_1.json"),
            {
                "participants": [{"name": other}, {"name": donor}],
                "messages": messages,
                "title": other,
                "is_still_participant": True,
                "thread_path": f"inbox/{slug}",
                "magic_words": [],
            },
        )

    # ads_and_topics — top-level list + flat `timestamp`
    for name, count in [
        ("videos_watched.json", cfg["videos"]),
        ("posts_viewed.json", cfg["posts"]),
        ("ads_viewed.json", cfg["ads"]),
    ]:
        _dump(
            _abspath("ads_information", "ads_and_topics", name),
            [_newer_flat_event(t) for t in _random_timestamps(rng, count)],
        )

    # likes — top-level list + flat `timestamp`
    _dump(
        _abspath("your_instagram_activity", "likes", "liked_posts.json"),
        [_newer_flat_event(t) for t in _random_timestamps(rng, cfg["likes"])],
    )
    _dump(
        _abspath("your_instagram_activity", "likes", "liked_comments.json"),
        [_newer_flat_event(t)
         for t in _random_timestamps(rng, cfg["liked_comments"])],
    )

    # content (posts / stories / igtv / reels) — top-level list +
    # flat `creation_timestamp`. Paths live under the newer
    # `your_instagram_activity/media/...` location.
    for name, count in [
        ("posts_1.json", cfg["content_posts"]),
        ("stories.json", cfg["stories"]),
        ("igtv_videos.json", cfg["igtv"]),
        ("reels.json", cfg["reels"]),
    ]:
        _dump(
            _abspath("your_instagram_activity", "media", name),
            [{"creation_timestamp": t}
             for t in _random_timestamps(rng, count)],
        )

    # comments — top-level list + flat `timestamp`
    _dump(
        _abspath("your_instagram_activity", "comments", "post_comments_1.json"),
        [_newer_flat_event(t) for t in _random_timestamps(rng, cfg["comments"])],
    )

    # Followers / following still use the legacy summary shape — the
    # newer shape for these is unconfirmed against a participant zip.
    _dump(
        _abspath("connections", "followers_and_following", "followers_1.json"),
        {
            "string_list_data": [
                {"value": f"user_{rng.randrange(10**9)}"}
                for _ in range(cfg["followers"])
            ],
        },
    )
    _dump(
        _abspath("connections", "followers_and_following", "following.json"),
        {
            "relationships_following": [
                {"string_list_data": [
                    {"value": f"user_{rng.randrange(10**9)}"}
                ]}
                for _ in range(cfg["following"])
            ],
        },
    )

    return os.path.abspath(out_dir)


def write_legacy_format_folder(out_dir, scale="realistic", seed=None):
    """Write a folder tree of bogus Instagram-legacy-format files to disk.

    The legacy format wraps each event-list in a dict keyed by a
    per-source well-known name (e.g. `likes_media_likes`) and hides
    timestamps under `string_list_data[0].timestamp` or
    `string_map_data.Time.timestamp`. Content posts / stories / reels
    are included too so extract_data has non-empty video_posts and
    comments_and_likes tables.

    Returns the absolute out_dir path.
    """
    if scale not in _SCALES:
        raise ValueError(f"unknown scale {scale!r}; expected one of {sorted(_SCALES)}")
    cfg = _SCALES[scale]
    rng = random.Random(seed)

    donor = _fake_name(rng)
    # Top-level prefix mirrors real exports like `instagram_username_YYYYMMDD/`.
    prefix = f"instagram_fixture_{rng.randrange(10**6):06d}"

    def _abspath(*parts):
        path = os.path.join(out_dir, prefix, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        return path

    def _dump(path, obj):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    # Message conversations (same shape as newer)
    for _ in range(cfg["conversations"]):
        other = _fake_name(rng)
        slug = f"{other.split()[0].lower()}_{rng.randrange(10**15, 10**16)}"
        msg_count = _resolve_messages_per(rng, cfg["messages_per"])
        timestamps = _random_timestamps(rng, msg_count, span_days=90)
        _dump(
            _abspath("messages", "inbox", slug, "message_1.json"),
            {
                "participants": [{"name": other}, {"name": donor}],
                "messages": [
                    {"sender_name": rng.choice([other, donor]),
                     "timestamp_ms": t * 1000}
                    for t in timestamps
                ],
                "title": other,
                "is_still_participant": True,
                "thread_path": f"inbox/{slug}",
            },
        )

    # ads_and_topics — dict wrapper + string_map_data nesting
    _dump(
        _abspath("ads_and_topics", "videos_watched.json"),
        {"impressions_history_videos_watched":
            [_legacy_string_map_entry(t)
             for t in _random_timestamps(rng, cfg["videos"])]},
    )
    _dump(
        _abspath("ads_and_topics", "posts_viewed.json"),
        {"impressions_history_posts_seen":
            [_legacy_string_map_entry(t)
             for t in _random_timestamps(rng, cfg["posts"])]},
    )
    _dump(
        _abspath("ads_and_topics", "ads_viewed.json"),
        {"impressions_history_ads_seen":
            [_legacy_string_map_entry(t)
             for t in _random_timestamps(rng, cfg["ads"])]},
    )

    # likes — dict wrapper + string_list_data nesting
    _dump(
        _abspath("likes", "liked_posts.json"),
        {"likes_media_likes":
            [_legacy_string_list_entry(t)
             for t in _random_timestamps(rng, cfg["likes"])]},
    )
    _dump(
        _abspath("likes", "liked_comments.json"),
        {"likes_comment_likes":
            [_legacy_string_list_entry(t)
             for t in _random_timestamps(rng, cfg["liked_comments"])]},
    )

    # comments (list of string_map entries)
    _dump(
        _abspath("comments", "post_comments_1.json"),
        [_legacy_string_map_entry(t)
         for t in _random_timestamps(rng, cfg["comments"])],
    )

    # content — posts, stories, igtv, reels (each have creation_timestamp)
    def _flat_ts_list(key, count):
        return [{"creation_timestamp": t}
                for t in _random_timestamps(rng, count)]

    _dump(
        _abspath("content", "posts_1.json"),
        [{"media": [{"creation_timestamp": t}]}
         for t in _random_timestamps(rng, cfg["content_posts"])],
    )
    _dump(
        _abspath("content", "stories.json"),
        {"ig_stories": _flat_ts_list("creation_timestamp", cfg["stories"])},
    )
    _dump(
        _abspath("content", "igtv_videos.json"),
        {"ig_igtv_media": _flat_ts_list("creation_timestamp", cfg["igtv"])},
    )
    _dump(
        _abspath("content", "reels.json"),
        {"ig_reels_media": _flat_ts_list("creation_timestamp", cfg["reels"])},
    )

    # followers / following — same shape as newer writer
    _dump(
        _abspath("followers_and_following", "followers_1.json"),
        {"string_list_data": [
            {"value": f"user_{rng.randrange(10**9)}"}
            for _ in range(cfg["followers"])]},
    )
    _dump(
        _abspath("followers_and_following", "following.json"),
        {"relationships_following": [
            {"string_list_data": [{"value": f"user_{rng.randrange(10**9)}"}]}
            for _ in range(cfg["following"])]},
    )

    return os.path.abspath(out_dir)


def _zip_folder(folder):
    """Zip `folder` to sibling `<folder>.zip`. Returns zip path."""
    zip_path = folder.rstrip("/") + ".zip"
    if os.path.exists(zip_path):
        os.unlink(zip_path)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(folder):
            for name in files:
                full = os.path.join(root, name)
                zf.write(full, os.path.relpath(full, folder))
    return zip_path


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate a bogus Instagram export folder "
                    "(newer or legacy format).",
    )
    parser.add_argument("out_dir", help="target folder (created if missing)")
    parser.add_argument("--format", default="newer",
                        choices=["newer", "legacy"],
                        help="which Instagram export shape to emit")
    parser.add_argument("--scale", default="realistic",
                        choices=sorted(_SCALES.keys()))
    parser.add_argument("--seed", type=int, default=None,
                        help="int seed for reproducibility (default: random)")
    parser.add_argument("--zip", action="store_true",
                        help="also emit <out_dir>.zip alongside the folder")
    args = parser.parse_args()
    writer = (write_newer_format_folder if args.format == "newer"
              else write_legacy_format_folder)
    path = writer(args.out_dir, scale=args.scale, seed=args.seed)
    print(f"Wrote {args.format} fixture to {path}")
    if args.zip:
        zip_path = _zip_folder(path)
        print(f"Zipped to {zip_path}")


if __name__ == "__main__":
    main()
