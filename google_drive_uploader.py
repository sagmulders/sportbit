"""Google Drive uploader for SportBit workout JSONs."""

import json
import tempfile
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class GoogleDriveUploader:
    """Upload workout JSON files to a shared Google Drive folder."""

    def __init__(self, folder_id):
        """
        Initialize uploader with folder ID.

        Args:
            folder_id: Google Drive folder ID (from URL: https://drive.google.com/drive/folders/{ID})
        """
        self.folder_id = folder_id
        self.service = build("drive", "v3")

    def file_exists(self, filename):
        """
        Check if a file already exists in the folder.

        Args:
            filename: Name of the file to check (e.g., "2026-09-08-84134.json")

        Returns:
            True if file exists, False otherwise
        """
        try:
            query = f"'{self.folder_id}' in parents and name='{filename}' and trashed=false"
            results = self.service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)",
                pageSize=1,
            ).execute()

            files = results.get("files", [])
            return len(files) > 0

        except HttpError as e:
            raise ValueError(f"Error checking file existence: {e}")

    def upload_workout_json(self, filename, workouts_array):
        """
        Upload workouts array as JSON file to Drive folder.

        Args:
            filename: Filename for the upload (e.g., "2026-09-08-84134.json")
            workouts_array: List of workout dictionaries to save

        Returns:
            File ID of uploaded file on success

        Raises:
            ValueError: If upload fails
        """
        # Create a temporary file with the JSON content
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(workouts_array, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            # Create file in Drive
            file_metadata = {
                "name": filename,
                "parents": [self.folder_id],
                "mimeType": "application/json",
            }

            media = MediaFileUpload(tmp_path, mimetype="application/json", resumable=False)

            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id",
            ).execute()

            return file.get("id")

        except HttpError as e:
            raise ValueError(f"Error uploading file: {e}")
        except Exception as e:
            raise ValueError(f"Error creating file: {e}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except:
                pass
