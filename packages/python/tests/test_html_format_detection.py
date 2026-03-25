import pytest
import json
import zipfile
import tempfile
import os
import sys

# Add the port package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'port'))

from script import is_html_format, extract_data, HtmlFormatError


class TestHtmlFormatDetection:
    """Test the HTML format detection functionality."""

    def create_test_zip_with_files(self, file_contents):
        """Helper method to create a zip file with specified files."""
        temp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(temp_dir, "test.zip")

        with zipfile.ZipFile(zip_path, 'w') as zf:
            for filename, content in file_contents.items():
                if isinstance(content, str):
                    zf.writestr(filename, content)
                else:
                    zf.writestr(filename, json.dumps(content))

        return zip_path

    def test_detects_html_format(self):
        """Test that HTML format is correctly detected."""
        # Create a zip with HTML files (typical Instagram HTML export structure)
        html_files = {
            "index.html": "<html><body>Instagram Export</body></html>",
            "followers.html": "<html><body>Followers list</body></html>",
            "media.html": "<html><body>Media files</body></html>",
            "messages/message_1.html": "<html><body>Messages</body></html>",
        }

        zip_path = self.create_test_zip_with_files(html_files)

        with zipfile.ZipFile(zip_path) as zipfile_obj:
            result = is_html_format(zipfile_obj)

        assert result is True

        # Clean up
        os.unlink(zip_path)

    def test_detects_json_format(self):
        """Test that JSON format is correctly detected (not HTML)."""
        # Create a zip with JSON files (typical Instagram JSON export structure)
        json_files = {
            "followers_and_following/followers_1.json": {
                "string_list_data": [
                    {"value": "user1", "timestamp": 1640995200}
                ]
            },
            "content/posts_1.json": [
                {"creation_timestamp": 1640995200, "media": []}
            ],
            "messages/inbox/chat_1/message_1.json": {
                "participants": [{"name": "user1"}],
                "messages": []
            }
        }

        zip_path = self.create_test_zip_with_files(json_files)

        with zipfile.ZipFile(zip_path) as zipfile_obj:
            result = is_html_format(zipfile_obj)

        assert result is False

        # Clean up
        os.unlink(zip_path)

    def test_mixed_format_with_json_data(self):
        """Test that mixed format with JSON data files is not detected as HTML."""
        # Create a zip with both HTML and JSON files, but with Instagram JSON data structure
        mixed_files = {
            "index.html": "<html><body>Instagram Export</body></html>",
            "readme.html": "<html><body>Instructions</body></html>",
            "messages/inbox/chat_1/message_1.json": {
                "participants": [{"name": "user1"}],
                "messages": [{"sender_name": "user1", "timestamp_ms": 1640995200000}]
            },
            "content/posts_1.json": [
                {"creation_timestamp": 1640995200}
            ]
        }

        zip_path = self.create_test_zip_with_files(mixed_files)

        with zipfile.ZipFile(zip_path) as zipfile_obj:
            result = is_html_format(zipfile_obj)

        assert result is False

        # Clean up
        os.unlink(zip_path)

    def test_html_format_without_relevant_json(self):
        """Test HTML format detection when there are HTML files but no relevant JSON data."""
        # Create a zip with HTML files and some unrelated JSON
        files = {
            "index.html": "<html><body>Instagram Export</body></html>",
            "followers.html": "<html><body>Followers</body></html>",
            "config.json": {"version": "1.0"},  # Not Instagram data structure
            "metadata.json": {"export_date": "2023-01-01"}  # Not Instagram data structure
        }

        zip_path = self.create_test_zip_with_files(files)

        with zipfile.ZipFile(zip_path) as zipfile_obj:
            result = is_html_format(zipfile_obj)

        assert result is True

        # Clean up
        os.unlink(zip_path)

    def test_extract_data_raises_html_format_error(self):
        """Test that extract_data raises HtmlFormatError for HTML format."""
        # Create a zip with HTML files
        html_files = {
            "index.html": "<html><body>Instagram Export</body></html>",
            "followers.html": "<html><body>Followers list</body></html>",
            "media.html": "<html><body>Media files</body></html>",
        }

        zip_path = self.create_test_zip_with_files(html_files)

        with pytest.raises(HtmlFormatError) as exc_info:
            extract_data(zip_path)

        assert "HTML format" in str(exc_info.value)
        assert "JSON format is required" in str(exc_info.value)

        # Clean up
        os.unlink(zip_path)

    def test_extract_data_works_with_json_format(self):
        """Test that extract_data works normally with JSON format."""
        # Create a minimal valid JSON Instagram export
        json_files = {
            "followers_and_following/followers_1.json": {
                "string_list_data": []
            },
            "followers_and_following/following.json": {
                "relationships_following": []
            },
            "content/posts_1.json": [],
            "content/stories.json": {
                "ig_stories": []
            },
            "comments/post_comments_1.json": [],
            "messages/inbox/chat_1/message_1.json": {
                "participants": [{"name": "test_user"}],
                "messages": []
            },
            "ads_and_topics/ads_viewed.json": {
                "impressions_history_ads_seen": []
            },
            "ads_and_topics/videos_watched.json": {
                "impressions_history_videos_watched": []
            },
            "ads_and_topics/posts_viewed.json": {
                "impressions_history_posts_seen": []
            },
            "likes/liked_comments.json": {
                "likes_comment_likes": []
            },
            "likes/liked_posts.json": {
                "likes_media_likes": []
            }
        }

        zip_path = self.create_test_zip_with_files(json_files)

        # This should not raise an exception
        try:
            result = extract_data(zip_path)
            # Verify we get the expected structure
            assert isinstance(result, list)
            assert len(result) == 5  # 5 extraction results
        except HtmlFormatError:
            pytest.fail("extract_data raised HtmlFormatError for valid JSON format")

        # Clean up
        os.unlink(zip_path)

    def test_edge_case_no_files(self):
        """Test edge case with empty zip file."""
        zip_path = self.create_test_zip_with_files({})

        with zipfile.ZipFile(zip_path) as zipfile_obj:
            result = is_html_format(zipfile_obj)

        # Empty zip should not be detected as HTML format
        assert result is False

        # Clean up
        os.unlink(zip_path)

    def test_edge_case_only_json_no_relevant_structure(self):
        """Test edge case with only JSON files but no Instagram structure."""
        json_files = {
            "random.json": {"data": "value"},
            "config.json": {"setting": "value"}
        }

        zip_path = self.create_test_zip_with_files(json_files)

        with zipfile.ZipFile(zip_path) as zipfile_obj:
            result = is_html_format(zipfile_obj)

        # Should not be detected as HTML since there are no HTML files
        assert result is False

        # Clean up
        os.unlink(zip_path)


if __name__ == "__main__":
    pytest.main([__file__])