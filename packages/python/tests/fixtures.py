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
import tempfile
import zipfile


# Deterministic Unix timestamps so tests can assert counts and ranges.
# 2026-01-01 00:00:00 UTC == 1767225600
_BASE_TS = 1767225600


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


def make_newer_format_zip():
    """Create a zip that mirrors the newer Instagram export shape.

    Returns the absolute path to the zip. Callers must unlink it.

    Contents (all counts are small but non-trivial so tests can assert):
      - 2 message threads (5 + 3 messages = 8 total messages)
      - 10 videos_watched entries
      - 5 posts_viewed entries
      - 2 ads_viewed entries
      - 7 liked_posts entries
      - 3 following + 4 followers (summary counts)
    """
    files = {
        "your_instagram_activity/messages/inbox/conv_a_1111/message_1.json":
            _newer_message_file(["Alice Test", "Donor User"], message_count=5,
                                start_offset_hours=0),
        "your_instagram_activity/messages/inbox/conv_b_2222/message_1.json":
            _newer_message_file(["Bob Test", "Donor User"], message_count=3,
                                start_offset_hours=10),

        "ads_information/ads_and_topics/videos_watched.json":
            [_newer_flat_event(t) for t in _timestamp_list(10, 100)],
        "ads_information/ads_and_topics/posts_viewed.json":
            [_newer_flat_event(t) for t in _timestamp_list(5, 200)],
        "ads_information/ads_and_topics/ads_viewed.json":
            [_newer_flat_event(t) for t in _timestamp_list(2, 300)],

        "your_instagram_activity/likes/liked_posts.json":
            [_newer_flat_event(t) for t in _timestamp_list(7, 400)],

        # Summary inputs — followers/following are still counted, so we
        # need something the existing counter understands. The newer
        # shape for these has not been observed yet; using legacy shape
        # here until a participant zip clarifies it.
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
