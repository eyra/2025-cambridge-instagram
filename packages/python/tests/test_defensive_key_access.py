"""Tests covering defensive access patterns in extraction helpers.

These tests exercise each unsafe subscript in script.py with real-world
zipfile fixtures that are missing keys, have empty lists, or have the
wrong shape. Each helper is expected to skip malformed records rather
than raising KeyError / IndexError / TypeError.

Issue 9804937176 — Defensive key access in extraction helpers.
"""

import json
import os
import sys
import tempfile
import zipfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "port"))

from script import (  # noqa: E402
    count_items,
    count_messages,
    flatten_media,
    get_content_posts_timestamps,
    get_creation_timestamps,
    get_donating_user,
    get_string_list_timestamps,
    get_string_map_timestamps,
    get_video_posts_timestamps,
    stories_timestamps,
)


def make_zip(files):
    """Create a tempfile zip containing the given {name: data} mapping.

    Values can be a string (written verbatim) or JSON-serializable.
    Returns the absolute path; caller is responsible for cleanup.
    """
    fd, path = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            if isinstance(content, str):
                zf.writestr(name, content)
            else:
                zf.writestr(name, json.dumps(content))
    return path


# ---------------------------------------------------------------------------
# count_items
# ---------------------------------------------------------------------------

class TestCountItems:
    """count_items(zipfile, pattern, key) should tolerate a missing top-level key."""

    def test_missing_key_in_dict_form(self):
        # Real-world failure: ads_viewed.json exists but has no
        # impressions_history_ads_seen key.
        path = make_zip({
            "test/ads_and_topics/ads_viewed.json": {"some_other_key": []},
        })
        try:
            with zipfile.ZipFile(path) as zf:
                assert count_items(zf, "*/test/ads_and_topics/ads_viewed.json",
                                   "impressions_history_ads_seen") == 0
        finally:
            os.unlink(path)

    def test_missing_key_in_list_form(self):
        # Same file shape but represented as a list of one dict.
        path = make_zip({
            "test/ads_and_topics/ads_viewed.json": [{"some_other_key": []}],
        })
        try:
            with zipfile.ZipFile(path) as zf:
                assert count_items(zf, "*/test/ads_and_topics/ads_viewed.json",
                                   "impressions_history_ads_seen") == 0
        finally:
            os.unlink(path)

    def test_partial_missing_across_files(self):
        # One file has the key, one doesn't — the missing one must not poison the count.
        path = make_zip({
            "test/ads_and_topics/ads_viewed_1.json":
                {"impressions_history_ads_seen": [1, 2, 3]},
            "test/ads_and_topics/ads_viewed_2.json":
                {"some_other_key": []},
        })
        try:
            with zipfile.ZipFile(path) as zf:
                assert count_items(zf, "*/ads_and_topics/ads_viewed_*.json",
                                   "impressions_history_ads_seen") == 3
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# get_donating_user
# ---------------------------------------------------------------------------

class TestGetDonatingUser:
    """get_donating_user must not raise on malformed participants arrays."""

    def test_missing_participants_key(self):
        assert get_donating_user({"messages": []}) is None

    def test_empty_participants_list(self):
        assert get_donating_user({"participants": [], "messages": []}) is None

    def test_participant_missing_name(self):
        assert get_donating_user({
            "participants": [{"id": 1}],
            "messages": [],
        }) is None


# ---------------------------------------------------------------------------
# get_string_map_timestamps
# ---------------------------------------------------------------------------

class TestGetStringMapTimestampsDefensive:
    """Malformed string_map_data items should be skipped, not crash."""

    def test_item_missing_string_map_data(self):
        data = [{"not_what_we_expect": True}]
        path = make_zip({"test/comments/post_comments_1.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_map_timestamps(
                    zf, "*/comments/post_comments_*.json"))
            assert result == []
        finally:
            os.unlink(path)

    def test_item_missing_time_subkey(self):
        data = [{"string_map_data": {"Comment": {"value": "hi"}}}]
        path = make_zip({"test/comments/post_comments_1.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_map_timestamps(
                    zf, "*/comments/post_comments_*.json"))
            assert result == []
        finally:
            os.unlink(path)

    def test_mixed_valid_and_malformed(self):
        data = [
            {"string_map_data": {"Time": {"timestamp": 1640995200}}},
            {"not_what_we_expect": True},
            {"string_map_data": {"Time": {"timestamp": 1641081600}}},
        ]
        path = make_zip({"test/comments/post_comments_1.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_map_timestamps(
                    zf, "*/comments/post_comments_*.json"))
            assert len(result) == 2
        finally:
            os.unlink(path)

    def test_missing_nested_key_with_key_param(self):
        # When the top-level key named by `key` is missing, nothing is yielded.
        data = {"wrong_nested_key": []}
        path = make_zip({"test/comments/post_comments_1.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_map_timestamps(
                    zf, "*/comments/post_comments_*.json",
                    key="expected_key"))
            assert result == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# get_string_list_timestamps
# ---------------------------------------------------------------------------

class TestGetStringListTimestampsDefensive:
    """Malformed string_list_data items should be skipped."""

    def test_item_missing_string_list_data(self):
        data = {"likes_media_likes": [{"unrelated": "field"}]}
        path = make_zip({"test/likes/liked_posts.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_list_timestamps(
                    zf, "*/likes/liked_posts.json", "likes_media_likes"))
            assert result == []
        finally:
            os.unlink(path)

    def test_item_with_empty_string_list_data(self):
        # IndexError hazard: item["string_list_data"][0]
        data = {"likes_media_likes": [{"string_list_data": []}]}
        path = make_zip({"test/likes/liked_posts.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_list_timestamps(
                    zf, "*/likes/liked_posts.json", "likes_media_likes"))
            assert result == []
        finally:
            os.unlink(path)

    def test_item_missing_timestamp_in_string_list_entry(self):
        data = {"likes_media_likes": [
            {"string_list_data": [{"value": "user1"}]}
        ]}
        path = make_zip({"test/likes/liked_posts.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_list_timestamps(
                    zf, "*/likes/liked_posts.json", "likes_media_likes"))
            assert result == []
        finally:
            os.unlink(path)

    def test_missing_top_level_key(self):
        data = {"wrong_key": []}
        path = make_zip({"test/likes/liked_posts.json": data})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_string_list_timestamps(
                    zf, "*/likes/liked_posts.json", "likes_media_likes"))
            assert result == []
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# flatten_media
# ---------------------------------------------------------------------------

class TestFlattenMediaDefensive:
    def test_list_item_missing_media_key(self):
        result = list(flatten_media([{"not_media": []}]))
        assert result == []

    def test_list_mixed_valid_and_missing(self):
        result = list(flatten_media([
            {"media": [{"creation_timestamp": 1640995200}]},
            {"not_media": []},
            {"media": [{"creation_timestamp": 1641081600}]},
        ]))
        assert len(result) == 2


# ---------------------------------------------------------------------------
# get_creation_timestamps
# ---------------------------------------------------------------------------

class TestGetCreationTimestampsDefensive:
    def test_item_missing_creation_timestamp(self):
        items = [
            {"creation_timestamp": 1640995200},
            {"title": "no timestamp here"},
        ]
        result = list(get_creation_timestamps(items))
        assert len(result) == 1


# ---------------------------------------------------------------------------
# get_content_posts_timestamps — new format
# ---------------------------------------------------------------------------

class TestGetContentPostsTimestampsDefensive:
    def test_new_format_post_missing_media(self):
        data = [
            {"media": [{"creation_timestamp": 1640995200}]},
            {"not_media": []},
        ]
        path = make_zip({
            "your_instagram_activity/media/posts_1.json": data,
        })
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_content_posts_timestamps(zf))
            assert len(result) == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# stories_timestamps
# ---------------------------------------------------------------------------

class TestStoriesTimestampsDefensive:
    def test_stories_missing_ig_stories_key_old_format(self):
        path = make_zip({"test/content/stories.json": {"different_key": []}})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(stories_timestamps(zf))
            assert result == []
        finally:
            os.unlink(path)

    def test_stories_missing_ig_stories_key_new_format(self):
        path = make_zip({
            "your_instagram_activity/media/stories.json":
                {"different_key": []},
        })
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(stories_timestamps(zf))
            assert result == []
        finally:
            os.unlink(path)

    def test_story_item_missing_creation_timestamp(self):
        path = make_zip({
            "test/content/stories.json": {"ig_stories": [
                {"creation_timestamp": 1640995200},
                {"title": "no timestamp"},
            ]},
        })
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(stories_timestamps(zf))
            assert len(result) == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# count_messages (already has try/except, verify it still tolerates oddness)
# ---------------------------------------------------------------------------

class TestCountMessagesDefensive:
    def test_conversation_missing_participants(self):
        path = make_zip({
            "test/messages/inbox/chat/message_1.json":
                {"messages": [{"sender_name": "u1"}]},
        })
        try:
            with zipfile.ZipFile(path) as zf:
                counts = count_messages(zf)
            assert counts == {"sent": 0, "received": 0}
        finally:
            os.unlink(path)

    def test_conversation_missing_messages(self):
        path = make_zip({
            "test/messages/inbox/chat/message_1.json":
                {"participants": [{"name": "u1"}]},
        })
        try:
            with zipfile.ZipFile(path) as zf:
                counts = count_messages(zf)
            assert counts == {"sent": 0, "received": 0}
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# get_video_posts_timestamps — integration: post with no media list
# ---------------------------------------------------------------------------

class TestGetVideoPostsTimestampsDefensive:
    def test_igtv_missing_key(self):
        path = make_zip({"test/content/igtv_videos.json": {"wrong_key": []}})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_video_posts_timestamps(zf))
            assert result == []
        finally:
            os.unlink(path)

    def test_reels_missing_key(self):
        path = make_zip({"test/content/reels.json": {"wrong_key": []}})
        try:
            with zipfile.ZipFile(path) as zf:
                result = list(get_video_posts_timestamps(zf))
            assert result == []
        finally:
            os.unlink(path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
