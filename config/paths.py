import os
import sys
from pathlib import Path
from dataclasses import dataclass, field


def get_default_google_drive_path() -> Path:
    """
    Detect the default Google Drive path based on the operating system.
    Returns the most likely path, which can be overridden by environment variables.
    """
    if sys.platform == "darwin":  # macOS
        home = Path.home()
        # Try newer Google Drive location first (Google Drive for Desktop)
        cloud_storage = home / "Library" / "CloudStorage"
        if cloud_storage.exists():
            # Look for any GoogleDrive-* folder
            gdrive_folders = list(cloud_storage.glob("GoogleDrive-*"))
            if gdrive_folders:
                return gdrive_folders[0] / "My Drive"
        # Try older Google Drive location
        old_gdrive = home / "Google Drive"
        if old_gdrive.exists():
            return old_gdrive
        # Default fallback for macOS
        return cloud_storage / "GoogleDrive" / "My Drive"
    
    elif sys.platform == "win32":  # Windows
        # Check for common Windows Google Drive mount points
        for drive_letter in ["G", "H", "I", "D", "E"]:
            gdrive = Path(f"{drive_letter}:/My Drive")
            if gdrive.exists():
                return gdrive
        # Default fallback for Windows
        return Path("G:/My Drive")
    
    else:  # Linux and others
        home = Path.home()
        # Google Drive is typically accessed via third-party tools on Linux
        gdrive = home / "google-drive"
        if gdrive.exists():
            return gdrive
        return home / "Google Drive"


def get_path_from_env(env_var: str, default: Path) -> Path:
    """Get a path from environment variable or use default."""
    env_value = os.environ.get(env_var)
    if env_value:
        return Path(env_value)
    return default


@dataclass
class Paths:
    # Base paths - can be overridden via environment variables
    vault_path: Path = field(default_factory=lambda: get_path_from_env(
        "OBSIDIAN_VAULT_PATH",
        get_default_google_drive_path() / "Obsidian"
    ))
    runtime_path: Path = field(default_factory=lambda: Path("."))
    
    def __post_init__(self):
        """Initialize derived paths after base paths are set."""
        self.vault_knowledgebot_path = self.vault_path / "KnowledgeBot"
        
        # Content paths used by AI tag replacements
        self.transcriptions = self.vault_knowledgebot_path / "Transcriptions"
        self.ideas = self.vault_knowledgebot_path / "Ideas"
        self.gdoc_path = self.vault_path / "gdoc"
        self.notion_path = self.vault_path / "notion"
        self.markdownload_path = self.vault_path / "MarkDownload"
        self.sources_path = self.vault_path / "Source"
        self.meetings = self.vault_path / "Meetings"
        self.conversations = self.vault_path / "Conversations"
        self.diary = self.vault_path / "Diary"
        self.people_path = self.vault_path / "People"
        
        # Scripts folder for <script!> tag
        self.scripts_folder = self.vault_path / "scripts"

        # Prompts library
        self.prompts_library = self.vault_path / "Prompts"

        # Data directory
        self.data = self.runtime_path / "data"


PATHS = Paths()
