"""End-to-end tests: extract_data handles both export shapes.

Legacy shape: top-level dict with a well-known key (likes_media_likes,
impressions_history_*, ig_stories, ig_igtv_media, ig_reels_media,
relationships_following, media[...]) where each event wraps the
timestamp under `string_list_data[0].timestamp`,
`string_map_data.Time.timestamp`, or `media[].creation_timestamp`.

Newer shape: top-level list where each event has `timestamp` or
`creation_timestamp` directly at the root.

Issue 9808995489 — Support newer Instagram export format.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "port"))
sys.path.insert(0, os.path.dirname(__file__))

from port.api.commands import FlushLogs  # noqa: E402
from script import extract_data  # noqa: E402
from fixtures import (  # noqa: E402
    make_legacy_format_zip,
    make_newer_format_zip,
)


def _run(zip_path):
    result = None
    for item in extract_data(zip_path, "en"):
        if item is not FlushLogs:
            result = item
    return {er.id: er.data_frame for er in result}


def _summary_row(tables, description):
    df = tables["instagram_summary"]
    matches = df[df["Description"] == description]
    assert not matches.empty, f"no summary row {description!r}"
    return int(matches.iloc[0]["Number"])


class TestNewerFormatExtraction:
    """Every data table must populate for a newer-shape zip."""

    def test_video_posts_populated(self):
        # 6 posts + 4 stories + 2 igtv + 3 reels = 15 events; grouped
        # per hour they collapse into a handful of rows but must be > 0.
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            assert len(tables["instagram_video_posts"]) > 0
        finally:
            os.unlink(path)

    def test_comments_and_likes_populated(self):
        # 9 comments + 7 liked posts + 4 liked comments = 20 events.
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            assert len(tables["instagram_comments_and_likes"]) > 0
        finally:
            os.unlink(path)

    def test_viewed_populated(self):
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            assert len(tables["instagram_viewed"]) > 0
        finally:
            os.unlink(path)

    def test_dm_activity_still_works(self):
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            assert len(tables["instagram_direct_message_activity"]) == 8
        finally:
            os.unlink(path)

    def test_summary_counts_reflect_newer_shape(self):
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            # count_posts sums posts + igtv + reels (all video content).
            # Fixture: 6 posts + 2 igtv + 3 reels = 11.
            assert _summary_row(tables, "Posts published") == 11
            assert _summary_row(tables, "Stories published") == 4
            assert _summary_row(tables, "Comments published") == 9
            assert _summary_row(tables, "Ads viewed") == 2
            assert _summary_row(tables, "Followers") == 4
            assert _summary_row(tables, "Following") == 3
        finally:
            os.unlink(path)


class TestLegacyFormatNoRegression:
    """Legacy extraction must continue to behave as before the shape fix."""

    def test_all_tables_populated(self):
        path = make_legacy_format_zip()
        try:
            tables = _run(path)
            # make_legacy_format_zip produces these exact counts today.
            assert len(tables["instagram_comments_and_likes"]) == 7
            assert len(tables["instagram_viewed"]) == 15
            assert len(tables["instagram_direct_message_activity"]) == 5
        finally:
            os.unlink(path)

    def test_summary_counts_preserved(self):
        path = make_legacy_format_zip()
        try:
            tables = _run(path)
            assert _summary_row(tables, "Ads viewed") == 2
            assert _summary_row(tables, "Followers") == 4
            assert _summary_row(tables, "Following") == 3
        finally:
            os.unlink(path)
