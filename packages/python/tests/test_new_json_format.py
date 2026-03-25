import pytest
import json
import zipfile
import tempfile
import os
import sys

# Add the port package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'port'))

from script import get_string_map_timestamps, parse_datetime

# Test timestamps (Unix epoch seconds)
TIMESTAMP_VIDEO_1 = 1770820980
TIMESTAMP_VIDEO_2 = 1770821079
TIMESTAMP_POST_1 = 1770821059
TIMESTAMP_POST_2 = 1770821100
TIMESTAMP_OLD_1 = 1640995200
TIMESTAMP_OLD_2 = 1641081600
TIMESTAMP_OLD_3 = 1640998800


class TestTimestampFormats:
    """Test handling of different Instagram JSON timestamp formats.

    Flat timestamp format (2026+):
    - Top-level 'timestamp' fields directly on each entry
    - 'label_values' instead of 'string_map_data'
    - No wrapper key like 'impressions_history_videos_watched'

    Nested timestamp format (legacy):
    - A top-level key like 'impressions_history_videos_watched'
    - Each entry has 'string_map_data' containing 'Time': {'timestamp': ...}
    """

    def create_test_zip(self, videos_data, posts_data):
        """Create a test zip with videos_watched.json and posts_viewed.json."""
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "test.zip")

        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr(
                "your_instagram_activity/ads_and_topics/videos_watched.json",
                json.dumps(videos_data)
            )
            zf.writestr(
                "your_instagram_activity/ads_and_topics/posts_viewed.json",
                json.dumps(posts_data)
            )

        return zip_path

    def test_flat_timestamp_format_extracts_timestamps(self):
        """
        Test that the flat timestamp format with top-level timestamps works correctly.

        This format has top-level 'timestamp' fields and 'label_values'
        instead of wrapper keys with nested 'string_map_data' entries.
        """
        flat_format_videos = [
            {
                "timestamp": TIMESTAMP_VIDEO_1,
                "media": [],
                "label_values": [
                    {
                        "label": "URL",
                        "value": "https://www.instagram.com/reel/FAKE_REEL_1/",
                        "href": "https://www.instagram.com/reel/FAKE_REEL_1/"
                    },
                    {
                        "dict": [
                            {
                                "dict": [
                                    {"label": "URL", "value": ""},
                                    {"label": "Name", "value": "Test Account"},
                                    {"label": "Benutzername", "value": "test_user_1"}
                                ],
                                "title": ""
                            }
                        ],
                        "title": "Eigentümer"
                    }
                ],
                "fbid": "fake_fbid_1"
            },
            {
                "timestamp": TIMESTAMP_VIDEO_2,
                "media": [],
                "label_values": [
                    {
                        "label": "URL",
                        "value": "https://www.instagram.com/reel/FAKE_REEL_2/",
                        "href": "https://www.instagram.com/reel/FAKE_REEL_2/"
                    }
                ],
                "fbid": "fake_fbid_2"
            }
        ]

        flat_format_posts = [
            {
                "timestamp": TIMESTAMP_POST_1,
                "media": [],
                "label_values": [
                    {
                        "label": "URL",
                        "value": "https://www.instagram.com/p/FAKE_POST_1/",
                        "href": "https://www.instagram.com/p/FAKE_POST_1/"
                    }
                ],
                "fbid": "fake_fbid_3"
            }
        ]

        zip_path = self.create_test_zip(flat_format_videos, flat_format_posts)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                timestamps = list(get_string_map_timestamps(
                    zf,
                    "*/ads_and_topics/videos_watched.json",
                    "impressions_history_videos_watched"
                ))
                assert len(timestamps) == 2
                assert timestamps[0] == parse_datetime(TIMESTAMP_VIDEO_1)
                assert timestamps[1] == parse_datetime(TIMESTAMP_VIDEO_2)
        finally:
            os.unlink(zip_path)

    def test_flat_timestamp_format_posts_viewed(self):
        """Test that posts_viewed.json with flat timestamp format extracts timestamps."""
        flat_format_videos = []

        flat_format_posts = [
            {
                "timestamp": TIMESTAMP_POST_1,
                "media": [],
                "label_values": [{"label": "URL", "value": "https://example.com"}],
                "fbid": "fake_fbid_1"
            },
            {
                "timestamp": TIMESTAMP_POST_2,
                "media": [],
                "label_values": [{"label": "URL", "value": "https://example.com/2"}],
                "fbid": "fake_fbid_2"
            }
        ]

        zip_path = self.create_test_zip(flat_format_videos, flat_format_posts)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                timestamps = list(get_string_map_timestamps(
                    zf,
                    "*/ads_and_topics/posts_viewed.json",
                    "impressions_history_posts_seen"
                ))
                assert len(timestamps) == 2
                assert timestamps[0] == parse_datetime(TIMESTAMP_POST_1)
                assert timestamps[1] == parse_datetime(TIMESTAMP_POST_2)
        finally:
            os.unlink(zip_path)

    def test_nested_timestamp_format_still_works(self):
        """Test that the nested timestamp format with impressions_history_* keys still works."""
        nested_format_videos = {
            "impressions_history_videos_watched": [
                {
                    "string_map_data": {
                        "Time": {"timestamp": TIMESTAMP_OLD_1}
                    }
                },
                {
                    "string_map_data": {
                        "Time": {"timestamp": TIMESTAMP_OLD_2}
                    }
                }
            ]
        }

        nested_format_posts = {
            "impressions_history_posts_seen": [
                {
                    "string_map_data": {
                        "Time": {"timestamp": TIMESTAMP_OLD_3}
                    }
                }
            ]
        }

        zip_path = self.create_test_zip(nested_format_videos, nested_format_posts)

        try:
            with zipfile.ZipFile(zip_path) as zf:
                timestamps = list(get_string_map_timestamps(
                    zf,
                    "*/ads_and_topics/videos_watched.json",
                    "impressions_history_videos_watched"
                ))
                assert len(timestamps) == 2
                assert timestamps[0] == parse_datetime(TIMESTAMP_OLD_1)
                assert timestamps[1] == parse_datetime(TIMESTAMP_OLD_2)
        finally:
            os.unlink(zip_path)

    def test_empty_flat_format_returns_empty(self):
        """Test that empty list in flat timestamp format returns no timestamps."""
        zip_path = self.create_test_zip([], [])

        try:
            with zipfile.ZipFile(zip_path) as zf:
                timestamps = list(get_string_map_timestamps(
                    zf,
                    "*/ads_and_topics/videos_watched.json",
                    "impressions_history_videos_watched"
                ))
                assert len(timestamps) == 0
        finally:
            os.unlink(zip_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
