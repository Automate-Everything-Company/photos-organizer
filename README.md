# Photo Organizer 📸

A Streamlit application that helps you organize your photos into folders based on their creation date. 
The app supports various organization patterns and handles multiple image formats including JPEG, PNG, and HEIC.

## Features

- Organize photos by:
  - Year (e.g., 2024_Photos)
  - Season (e.g., 2024_Summer_Photos)
  - Month (e.g., 2024-03_Photos)
  - Day (e.g., 2024-03-24_Photos)

- Preview organization structure before applying changes
- Option to copy or move the files
- Support for JPEG, PNG, and HEIC formats

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/photo-organizer.git
cd photo-organizer
```

2. Create a virtual environment (optional but recommended):
```bash
uv venv .vev
source .venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install the required packages:
```bash
uv pip install -r requirements.txt
```

## Usage

1. Start the application:
```bash
streamlit run src/app.py
```

2. Enter the source directory path containing your photos

3. Choose organization settings:
   - Select organization type (Year/Season/Month/Day)
   - Choose whether to create year parent folders
   - Decide if you want to move or copy the files

4. Click "Start Organizing" to preview the organization

5. Review the preview and:
   - Click "Confirm Organization" to proceed
   - Click "Cancel" to make changes

## File Organization Examples

```
By Year:
└── 2024_Photos
    ├── photo1.jpg
    └── photo2.heic

By Month:
└── 2024-03_Photos
    ├── photo1.jpg
    └── photo2.heic

By Day:
└── 2024-03-24_Photos
    ├── photo1.jpg
    └── photo2.heic

With Year Parent:
└── 2024
    └── 2024-03_Photos
        ├── photo1.jpg
        └── photo2.heic
```

## Requirements

- Python 3.8+
- Streamlit
- Pillow
- pillow-heif
- exif

## Notes

- The app preserves original files by default
- HEIC files require the pillow-heif package
- Date extraction falls back to file modification date if no EXIF data is found