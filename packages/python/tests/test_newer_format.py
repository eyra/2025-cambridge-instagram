"""End-to-end tests that extract_data handles both export shapes.

Legacy shape: top-level dict with a well-known key (likes_media_likes,
impressions_history_*, ig_stories, ig_igtv_media, ig_reels_media,
relationships_following) where each event wraps the timestamp under
`string_list_data[0].timestamp`, `string_map_data.Time.timestamp`,
or `media[].creation_timestamp`.

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
    """After the shape-detection fix these must all pass."""

    def test_comments_and_likes_populated(self):
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

    def test_summary_ads_viewed_counted(self):
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            assert _summary_row(tables, "Ads viewed") == 2  # make_newer uses 2
        finally:
            os.unlink(path)

    def test_dm_activity_still_works(self):
        path = make_newer_format_zip()
        try:
            tables = _run(path)
            # Newer fixture: 5 + 3 = 8 messages
            assert len(tables["instagram_direct_message_activity"]) == 8
        finally:
            os.unlink(path)


class TestLegacyFormatNoRegression:
    """Legacy extraction must continue to behave as before the shape fix."""

    def test_all_tables_populated(self):
        path = make_legacy_format_zip()
        try:
            tables = _run(path)
            # make_legacy_format_zip produces these exact counts today.
            # Any drift means we broke backwards compatibility.
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
