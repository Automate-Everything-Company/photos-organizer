import logging
import os
import re
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

import streamlit as st
from pillow_heif import register_heif_opener

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
register_heif_opener()

class Photos(Enum):
    FIRST_PHOTOS = 5

@dataclass
class ProcessStats:
    total_photos: int = 0
    processed_folders: int = 0
    processed_files: int = 0
    skipped_files: int = 0
    errors: int = 0

class SortingType(Enum):
    YEARLY = "By Year (2024)"
    MONTHLY = "By Month (2024-03)"
    DAILY = "By Day (2024-03-24)"
    SEASON = "By Season (2024-Winter)"


class StatusManager:
    @staticmethod
    def show_preview_stats(photos_count: int, folders_count: int) -> None:
        st.success("✨ Preview generated successfully!")
        st.write(f"Found {photos_count} photos to organize into {folders_count} folders")

    @staticmethod
    def show_progress(stats: ProcessStats) -> None:
        st.write(f"Processing files: {stats.processed_files}/{stats.total_photos}")
        if stats.skipped_files:
            st.warning(f"Skipped {stats.skipped_files} files due to errors")
        if stats.errors:
            st.error(f"Encountered {stats.errors} errors")

@dataclass
class PhotoFile:
    path: Path
    date_taken: datetime


class SeasonMapper:
    @staticmethod
    def get_season(date: datetime) -> str:
        month = date.month
        if month in (12, 1, 2):
            return "Winter"
        if month in (3, 4, 5):
            return "Spring"
        if month in (6, 7, 8):
            return "Summer"
        return "Fall"


class DateExtractor:
    def __init__(self, photo_path: Path):
        self.photo_path = photo_path

    def extract_from_heic(self) -> datetime | None:
        from pillow_heif import HeifImageFile

        with HeifImageFile(self.photo_path) as heif_img:
            exif = heif_img.getexif()
            if not exif:
                return None

            for tag in [306, 36867, 36868]:
                if tag in exif:
                    try:
                        return datetime.strptime(exif[tag], "%Y:%m:%d %H:%M:%S")
                    except (ValueError, TypeError):
                        continue
        return None

    def extract_from_jpeg(self) -> datetime | None:
        from exif import Image as ExifImage

        with open(self.photo_path, "rb") as image_file:
            image = ExifImage(image_file)
            if not image.has_exif:
                return None

            for attr in ["datetime_original", "datetime", "datetime_digitized"]:
                if hasattr(image, attr):
                    try:
                        return datetime.strptime(
                            getattr(image, attr), "%Y:%m:%d %H:%M:%S",
                        )
                    except (ValueError, TypeError):
                        continue
        return None

    def extract_from_filename(self) -> datetime | None:
        patterns = [
            (r"\d{8}", "%Y%m%d"),
            (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
            (r"\d{4}_\d{2}_\d{2}", "%Y_%m_%d"),
            (r"IMG-\d{8}", "%Y%m%d"),
            (r"IMG_\d{8}", "%Y%m%d"),
            (r"WA\d{8}", "%Y%m%d"),
            (r"IMG_E\d{8}", "%Y%m%d"),
        ]

        filename = self.photo_path.stem
        for pattern, date_format in patterns:
            match = re.search(pattern, filename)
            if match:
                date_str = match.group(0)
                for prefix in ["IMG-", "IMG_", "IMG_E", "WA"]:
                    if date_str.startswith(prefix):
                        date_str = date_str[len(prefix) :]
                try:
                    return datetime.strptime(date_str, date_format)
                except ValueError:
                    continue
        return None

    def get_date(self) -> datetime:
        if self.photo_path.suffix.lower() == ".heic":
            date = self.extract_from_heic()
        elif self.photo_path.suffix.lower() in [".jpg", ".jpeg"]:
            date = self.extract_from_jpeg()
        else:
            date = None

        if not date:
            date = self.extract_from_filename()

        return date or datetime.fromtimestamp(os.path.getmtime(self.photo_path))


class PhotoOrganizer:
    def __init__(self, source_dir: Path) -> None:
        self.source_dir = source_dir
        self.supported_extensions = {".jpg", ".jpeg", ".png", ".heic"}

    def scan_photos(self) -> list[PhotoFile]:
        photo_files = []
        for file_path in self.source_dir.rglob("*"):
            if file_path.name.startswith("._"):
                continue
            if file_path.suffix.lower() in self.supported_extensions:
                try:
                    date_taken = DateExtractor(file_path).get_date()
                    photo_files.append(PhotoFile(file_path, date_taken))
                except Exception as e:
                    st.error(f"Error processing {file_path}: {e!s}")
        return photo_files

    def organize_photos(
        self, photos: list[PhotoFile], sort_type: SortingType, create_year_parent: bool,
    ) -> dict[str, list[PhotoFile]]:
        organized = {}
        for photo in photos:
            category = self._get_category(photo, sort_type, create_year_parent)
            if category not in organized:
                organized[category] = []
            organized[category].append(photo)
        return organized

    def _get_category(
        self, photo: PhotoFile, sort_type: SortingType, create_year_parent: bool,
    ) -> str:
        year = photo.date_taken.strftime("%Y")
        if sort_type == SortingType.YEARLY:
            return f"{year}_Photos"

        category_formats = {
            SortingType.MONTHLY: lambda dt: f"{dt.strftime('%Y-%m')}_Photos",
            SortingType.DAILY: lambda dt: f"{dt.strftime('%Y-%m-%d')}_Photos",
            SortingType.SEASON: lambda dt: f"{dt.strftime('%Y')}_{SeasonMapper.get_season(dt)}_Photos",
        }

        category = category_formats[sort_type](photo.date_taken)
        return f"{year}/{category}" if create_year_parent else category

    def move_photos(
        self,
        organized_photos: dict[str, list[PhotoFile]],
        target_dir: Path,
        delete_original: bool,
    ) -> None:
        for category, photos in organized_photos.items():
            category_dir = target_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)

            for photo in photos:
                new_path = category_dir / photo.path.name
                try:
                    if delete_original:
                        shutil.move(str(photo.path), str(new_path))
                    else:
                        shutil.copy2(str(photo.path), str(new_path))
                except Exception as e:
                    st.error(f"Error processing {photo.path}: {e!s}")


def create_folder_map(path: Path, prefix: str = "") -> str:
    if not path.exists():
        return ""

    tree = []
    if prefix == "":
        tree.append(f"📂 **{path.name or path}**\n")
        prefix = ""

    items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    for i, item in enumerate(items):
        is_last_item = i == len(items) - 1
        current_prefix = prefix + ("└── " if is_last_item else "├── ")

        if item.is_dir():
            tree.append(f"{current_prefix}📁 **{item.name}**")
            next_prefix = prefix + ("    " if is_last_item else "│   ")
            try:
                sub_items = item.iterdir()
                if any(sub_items):
                    tree.append(create_folder_map(item, next_prefix))
            except PermissionError:
                tree.append(f"{next_prefix}└── (Permission Denied)")
        else:
            tree.append(f"{current_prefix}📄 {item.name}")

    return "\n".join(filter(None, tree))


def setup_page() -> None:
    st.set_page_config(page_title="Photos Organizer", page_icon="📸", layout="wide")
    st.title("📸 Photo Organizer")
    st.caption("Organize your photos by year, season, month, or day - you choose how!")


def select_sort_type() -> SortingType:
    selected = st.radio(
        "Sort photos by:",
        ["Year", "Season", "Month", "Day"],
        horizontal=True,
        format_func=lambda x: f"By {x}",
    )
    return {
        "Year": SortingType.YEARLY,
        "Season": SortingType.SEASON,
        "Month": SortingType.MONTHLY,
        "Day": SortingType.DAILY,
    }[selected]


def get_directory_paths() -> tuple[Path | None, Path | None]:
    source_dir = st.text_input("Source Directory Path")
    if not source_dir:
        return None, None

    source_path = Path(source_dir)
    if not source_path.exists():
        st.error("❌ Directory does not exist!")
        return None, None

    use_source_as_target = st.checkbox("Use source folder as target", value=True)
    if use_source_as_target:
        return source_path, source_path

    target_dir = st.text_input("Target Directory Path")
    if not target_dir:
        return source_path, None

    target_path = Path(target_dir)
    if not target_path.exists():
        st.error("❌ Directory does not exist!")
        return source_path, None

    return source_path, target_path


def process_organization(
    source_path: Path, sort_type: SortingType, create_year_parent: bool,
):
    organizer = PhotoOrganizer(source_path)
    photos = organizer.scan_photos()
    if not photos:
        st.warning("No supported photos found in the selected directory.")
        return None
    st.write(f"Found {len(photos)} photos")
    return organizer.organize_photos(photos, sort_type, create_year_parent)


def render_preview(organized_photos: dict) -> None:
    st.subheader("Preview of Photo Organization")
    for folder, photos in sorted(organized_photos.items()):
        st.markdown(f"### 📁 {folder}")
        st.write(f"Contains {len(photos)} photos")
        with st.expander("See photos"):
            for photo in photos[:Photos.FIRST_PHOTOS.value]:
                st.write(f"📄 {photo.path.name}")
            if len(photos) > Photos.FIRST_PHOTOS.value:
                st.write(f"... and {len(photos) - Photos.FIRST_PHOTOS.value} more photos")
        st.divider()


def render_directory_map(source_dir: Path, target_dir: Path) -> None:
    st.subheader("Directory Structure Map")
    if source_dir:
        st.markdown("### Source Directory Structure")
        st.code(create_folder_map(source_dir), language=None)
        if target_dir and target_dir != source_dir:
            st.markdown("### Target Directory Structure")
            st.code(create_folder_map(target_dir), language=None)
    else:
        st.write("Enter a source directory path to see its structure")


def main() -> None:
    setup_page()
    status_container = st.container()
    left_col, right_col = st.columns([3, 2], gap="large")

    with left_col:
        # Make configuration section always visible with st.empty()
        config_section = st.empty()
        with config_section.container():
            st.subheader("Configuration")
            source_path, target_path = get_directory_paths()

            if source_path:
                st.subheader("Organization Settings")
                sort_type = select_sort_type()

                create_year_parent = False
                if sort_type != SortingType.YEARLY:
                    create_year_parent = st.checkbox(
                        "Create year folder as parent",
                        help="Example: 2024/2024-03_Photos",
                    )

                delete_original = st.toggle(
                    "Delete original photos after organizing",
                    value=False,
                )
                if delete_original:
                    st.warning("⚠️ Original photos will be deleted after organization")

                # Add stats container
                stats_container = st.empty()

                if st.button("Preview organized photos", type="primary"):
                    with st.spinner("Scanning photos..."):
                        organized = process_organization(
                            source_path, sort_type, create_year_parent,
                        )
                        if organized:
                            photos_count = sum(len(photos) for photos in organized.values())
                            with status_container:
                                StatusManager.show_preview_stats(
                                    photos_count=photos_count,
                                    folders_count=len(organized)
                                )
                            st.session_state.organized_photos = organized
                            st.session_state.preview_shown = True
                            st.session_state.stats = ProcessStats(total_photos=photos_count)
                            st.rerun()

                if st.session_state.get("preview_shown", False):
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(
                                "Confirm Organization",
                                type="primary",
                                key="confirm_org",
                        ):
                            try:
                                with st.spinner("Organizing photos..."):
                                    organizer = PhotoOrganizer(source_path)
                                    stats = st.session_state.get("stats")

                                    with status_container:
                                        st.info("Starting photo organization...")
                                        organizer.move_photos(
                                            st.session_state.organized_photos,
                                            target_path,
                                            delete_original,
                                        )
                                        if delete_original:
                                            st.success("✨ Photos moved successfully!")
                                        else:
                                            st.success("✨ Photos copied successfully!")
                                        st.write(
                                            f"Processed {stats.processed_files}/{stats.total_photos} files "
                                            f"in {stats.processed_folders} folders"
                                        )

                                    time.sleep(2)
                                    st.session_state.preview_shown = False
                                    st.session_state.organization_done = True
                                    st.rerun()
                            except Exception as exc:
                                with status_container:
                                    st.error(f"❌ Failed to organize photos: {str(exc)}")
                                    import traceback
                                    st.error(f"Details: {traceback.format_exc()}")
                    with col2:
                        if st.button("Cancel", type="secondary", key="cancel_org"):
                            st.session_state.preview_shown = False
                            st.rerun()

    with right_col:
        if st.session_state.get("preview_shown", False):
            render_preview(st.session_state.organized_photos)
        else:
            render_directory_map(source_path, target_path)


if __name__ == "__main__":
    main()
