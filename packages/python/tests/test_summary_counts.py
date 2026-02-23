#!/usr/bin/env python
"""Test script to verify summary counts include filtered data and table row limits"""

import json
import zipfile
import io
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock
import pytest

# Mock the js module before importing port modules
sys.modules['js'] = MagicMock()

# Add the port package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from port.script import extract_data, MAX_TABLE_ROWS


def create_test_zip_with_mixed_dates():
    """Create a test zip with Instagram data from various time periods"""
    base_date = datetime.now()

    # Create posts data (old format)
    posts_data = [
        {
            "media": [
                # Recent posts (past 6 months)
                {"creation_timestamp": int((base_date - timedelta(days=30)).timestamp())},
                {"creation_timestamp": int((base_date - timedelta(days=60)).timestamp())},
                # Old posts (more than 6 months)
                {"creation_timestamp": int((base_date - timedelta(days=200)).timestamp())},
            ]
        }
    ]

    # Create stories data
    stories_data = {
        "ig_stories": [
            # Recent stories (past 6 months)
            {"creation_timestamp": int((base_date - timedelta(days=15)).timestamp())},
            {"creation_timestamp": int((base_date - timedelta(days=45)).timestamp())},
            # Old stories (more than 6 months)
            {"creation_timestamp": int((base_date - timedelta(days=210)).timestamp())},
        ]
    }

    # Create comments data
    comments_data = [
        # Recent comments (past 6 months)
        {"string_map_data": {"Time": {"timestamp": int((base_date - timedelta(days=20)).timestamp())}}},
        {"string_map_data": {"Time": {"timestamp": int((base_date - timedelta(days=40)).timestamp())}}},
        # Old comments (more than 6 months)
        {"string_map_data": {"Time": {"timestamp": int((base_date - timedelta(days=220)).timestamp())}}},
    ]

    # Create messages data
    messages_data = {
        "participants": [
            {"name": "friend"},
            {"name": "testuser"}  # Last participant is the donating user
        ],
        "messages": [
            # Recent messages (past 6 months)
            {"sender_name": "testuser", "timestamp_ms": int((base_date - timedelta(days=5)).timestamp() * 1000)},
            {"sender_name": "friend", "timestamp_ms": int((base_date - timedelta(days=10)).timestamp() * 1000)},
            {"sender_name": "testuser", "timestamp_ms": int((base_date - timedelta(days=15)).timestamp() * 1000)},
            # Old messages (more than 6 months)
            {"sender_name": "testuser", "timestamp_ms": int((base_date - timedelta(days=230)).timestamp() * 1000)},
            {"sender_name": "friend", "timestamp_ms": int((base_date - timedelta(days=240)).timestamp() * 1000)},
        ]
    }

    # Create followers data
    followers_data = [
        {"string_list_data": [{"value": "follower1"}, {"value": "follower2"}]}
    ]

    # Create following data
    following_data = {
        "relationships_following": [
            {"string_list_data": [{"value": "following1"}]}
        ]
    }

    # Create ads viewed data
    ads_data = {
        "impressions_history_ads_seen": [
            {"string_map_data": {"Time": {"timestamp": int((base_date - timedelta(days=1)).timestamp())}}}
        ]
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Posts
        zf.writestr("instagram/content/posts_1.json", json.dumps(posts_data))
        # Stories
        zf.writestr("instagram/content/stories.json", json.dumps(stories_data))
        # Comments
        zf.writestr("instagram/comments/post_comments_1.json", json.dumps(comments_data))
        # Messages
        zf.writestr("instagram/messages/inbox/chat1/message_1.json", json.dumps(messages_data))
        # Followers
        zf.writestr("instagram/followers_and_following/followers_1.json", json.dumps(followers_data))
        # Following
        zf.writestr("instagram/followers_and_following/following.json", json.dumps(following_data))
        # Ads
        zf.writestr("instagram/ads_and_topics/ads_viewed.json", json.dumps(ads_data))

    zip_buffer.seek(0)
    return zip_buffer


def test_summary_includes_filtered_counts():
    """Test that summary table includes filtered counts for past 6 months"""
    test_zip = create_test_zip_with_mixed_dates()
    meta_data = []
    results = extract_data(test_zip, "en", meta_data)

    summary = next((r for r in results if r.id == "instagram_summary"), None)
    assert summary is not None

    df = summary.data_frame

    # Check that we have the expected rows (8 total + 5 recent = 13)
    assert len(df) == 13, f"Expected 13 rows in summary, got {len(df)}"

    # Verify total counts
    posts_total = df[df["Description"] == "Posts published"]["Number"].iloc[0]
    assert posts_total == 3, f"Expected 3 total posts, got {posts_total}"

    stories_total = df[df["Description"] == "Stories published"]["Number"].iloc[0]
    assert stories_total == 3, f"Expected 3 total stories, got {stories_total}"

    comments_total = df[df["Description"] == "Comments published"]["Number"].iloc[0]
    assert comments_total == 3, f"Expected 3 total comments, got {comments_total}"

    messages_sent_total = df[df["Description"] == "Messages sent"]["Number"].iloc[0]
    assert messages_sent_total == 3, f"Expected 3 total messages sent, got {messages_sent_total}"

    messages_received_total = df[df["Description"] == "Messages received"]["Number"].iloc[0]
    assert messages_received_total == 2, f"Expected 2 total messages received, got {messages_received_total}"

    # Verify filtered counts (past 6 months)
    posts_recent = df[df["Description"] == "Posts published (past 6 months)"]["Number"].iloc[0]
    assert posts_recent == 2, f"Expected 2 recent posts, got {posts_recent}"

    stories_recent = df[df["Description"] == "Stories published (past 6 months)"]["Number"].iloc[0]
    assert stories_recent == 2, f"Expected 2 recent stories, got {stories_recent}"

    comments_recent = df[df["Description"] == "Comments published (past 6 months)"]["Number"].iloc[0]
    assert comments_recent == 2, f"Expected 2 recent comments, got {comments_recent}"

    messages_sent_recent = df[df["Description"] == "Messages sent (past 6 months)"]["Number"].iloc[0]
    assert messages_sent_recent == 2, f"Expected 2 recent messages sent, got {messages_sent_recent}"

    messages_received_recent = df[df["Description"] == "Messages received (past 6 months)"]["Number"].iloc[0]
    assert messages_received_recent == 1, f"Expected 1 recent message received, got {messages_received_recent}"


def test_summary_with_locale():
    """Test that summary filtered counts work with different locales"""
    test_zip = create_test_zip_with_mixed_dates()

    # Test with German locale
    results_de = extract_data(test_zip, "de")
    summary_de = next((r for r in results_de if r.id == "instagram_summary"), None)
    assert summary_de is not None

    # Check that German translations are used
    df_de = summary_de.data_frame
    assert "Veröffentlichte Beiträge (letzte 6 Monate)" in df_de["Description"].values
    assert "Veröffentlichte Stories (letzte 6 Monate)" in df_de["Description"].values

    # Test with Dutch locale
    results_nl = extract_data(test_zip, "nl")
    summary_nl = next((r for r in results_nl if r.id == "instagram_summary"), None)
    assert summary_nl is not None

    # Check that Dutch translations are used
    df_nl = summary_nl.data_frame
    assert "Gepubliceerde berichten (afgelopen 6 maanden)" in df_nl["Description"].values
    assert "Gepubliceerde verhalen (afgelopen 6 maanden)" in df_nl["Description"].values


def test_summary_empty_data():
    """Test that summary works with empty/minimal data"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Create minimal structure with empty data
        zf.writestr("instagram/content/posts_1.json", json.dumps([]))
        zf.writestr("instagram/content/stories.json", json.dumps({"ig_stories": []}))

    zip_buffer.seek(0)

    results = extract_data(zip_buffer, "en")
    summary = next((r for r in results if r.id == "instagram_summary"), None)
    assert summary is not None

    # Should have 13 rows with mostly zeros
    df = summary.data_frame
    assert len(df) == 13


def test_table_row_limiting():
    """Test that tables are limited to MAX_TABLE_ROWS"""
    base_date = datetime.now()

    # Create more messages than MAX_TABLE_ROWS
    num_messages = MAX_TABLE_ROWS + 100
    messages = []
    for i in range(num_messages):
        messages.append({
            "sender_name": "testuser" if i % 2 == 0 else "friend",
            "timestamp_ms": int((base_date - timedelta(minutes=i)).timestamp() * 1000)
        })

    messages_data = {
        "participants": [
            {"name": "friend"},
            {"name": "testuser"}
        ],
        "messages": messages
    }

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("instagram/messages/inbox/chat1/message_1.json", json.dumps(messages_data))
        # Add minimal required files
        zf.writestr("instagram/content/posts_1.json", json.dumps([]))
        zf.writestr("instagram/content/stories.json", json.dumps({"ig_stories": []}))

    zip_buffer.seek(0)

    meta_data = []
    results = extract_data(zip_buffer, "en", meta_data)

    # Find direct message activity table
    dm_table = next((r for r in results if r.id == "instagram_direct_message_activity"), None)
    assert dm_table is not None

    # Check that table is limited
    assert len(dm_table.data_frame) == MAX_TABLE_ROWS, \
        f"Expected {MAX_TABLE_ROWS} rows, got {len(dm_table.data_frame)}"

    # Check that meta_data contains truncation info
    truncation_msgs = [m for m in meta_data if "Limited to" in str(m)]
    assert len(truncation_msgs) > 0, "Expected truncation message in meta_data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
