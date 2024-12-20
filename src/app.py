import streamlit as st
from pathlib import Path
from datetime import datetime
from PIL import Image
import shutil
from typing import Literal, List, Dict
from dataclasses import dataclass
import os
from enum import Enum


class SortingType(Enum):
    YEARLY = "Yearly"
    MONTHLY = "Monthly"
    DAILY = "Daily"


@dataclass
class PhotoFile:
    path: Path
    date_taken: datetime


class PhotoOrganizer:
    def __init__(self, source_dir: Path):
        """Initialize the photo organizer with source directory."""
        self.source_dir = source_dir
        self.supported_extensions = {'.jpg', '.jpeg', '.png', '.heic'}

    def get_photo_date(self, photo_path: Path) -> datetime:
        """Extract date from photo metadata or fall back to file modification date."""
        try:
            with Image.open(photo_path) as img:
                exif = img._getexif()
                if exif and 36867 in exif:  # 36867 is DateTimeOriginal
                    date_str = exif[36867]
                    return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except Exception:
            pass

        # Fallback to file modification time
        return datetime.fromtimestamp(os.path.getmtime(photo_path))

    def scan_photos(self) -> List[PhotoFile]:
        """Scan directory for photos and extract their dates."""
        photo_files = []

        for file_path in self.source_dir.rglob('*'):
            if file_path.suffix.lower() in self.supported_extensions:
                try:
                    date_taken = self.get_photo_date(file_path)
                    photo_files.append(PhotoFile(file_path, date_taken))
                except Exception as e:
                    st.error(f"Error processing {file_path}: {str(e)}")

        return photo_files

    def organize_photos(self, photos: List[PhotoFile], sort_type: SortingType) -> Dict[str, List[PhotoFile]]:
        """Organize photos into categories based on sorting type."""
        organized: Dict[str, List[PhotoFile]] = {}

        for photo in photos:
            if sort_type == SortingType.YEARLY:
                category = photo.date_taken.strftime('%Y')
            elif sort_type == SortingType.MONTHLY:
                category = photo.date_taken.strftime('%Y-%m')
            else:  # DAILY
                category = photo.date_taken.strftime('%Y-%m-%d')

            if category not in organized:
                organized[category] = []
            organized[category].append(photo)

        return organized

    def move_photos(self, organized_photos: Dict[str, List[PhotoFile]], target_dir: Path) -> None:
        """Move photos to their respective folders."""
        for category, photos in organized_photos.items():
            category_dir = target_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            for photo in photos:
                try:
                    new_path = category_dir / photo.path.name
                    shutil.copy2(photo.path, new_path)
                except Exception as e:
                    st.error(f"Error moving {photo.path}: {str(e)}")


def main():
    st.title("📸 Photo Organizer")

    # Sidebar settings
    st.sidebar.header("Settings")

    # Source directory selection
    source_dir = st.sidebar.text_input("Source Directory", "")
    if source_dir:
        source_path = Path(source_dir)
        if not source_path.exists():
            st.sidebar.error("Directory does not exist!")
            return

    # Sorting type selection
    sort_type = st.sidebar.selectbox(
        "Sort photos by",
        [SortingType.YEARLY, SortingType.MONTHLY, SortingType.DAILY],
        format_func=lambda x: x.value
    )

    # Target directory selection
    target_dir = st.sidebar.text_input("Target Directory (leave empty to use source directory)", "")
    if not target_dir:
        target_dir = source_dir

    if st.sidebar.button("Organize Photos") and source_dir:
        with st.spinner("Processing photos..."):
            try:
                organizer = PhotoOrganizer(Path(source_dir))
                photos = organizer.scan_photos()

                if not photos:
                    st.warning("No supported photos found in the selected directory.")
                    return

                st.info(f"Found {len(photos)} photos")

                organized = organizer.organize_photos(photos, sort_type)
                organizer.move_photos(organized, Path(target_dir))

                st.success("Photos organized successfully!")

                # Display folder structure
                st.subheader("Organized Folder Structure")
                for category in sorted(organized.keys()):
                    st.write(f"📁 {category} ({len(organized[category])} photos)")

            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

    # Display current folder structure
    if source_dir:
        st.subheader("Current Folder Contents")
        try:
            for item in sorted(Path(source_dir).glob('*')):
                if item.is_file():
                    st.write(f"📄 {item.name}")
                else:
                    st.write(f"📁 {item.name}")
        except Exception as e:
            st.error(f"Error reading directory: {str(e)}")


if __name__ == "__main__":
    main()