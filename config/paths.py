import os
import sys
from pathlib import Path
from dataclasses import dataclass, field


def get_default_google_drive_path() -> Path | None:
    """
    Detect the default Google Drive path based on the operating system.
    Returns the most likely path, or None if not found.
    Users should set OBSIDIAN_VAULT_PATH environment variable if auto-detection fails.
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
        # Return None - no Google Drive found on macOS
        return None
    
    elif sys.platform == "win32":  # Windows
        # Check for common Windows Google Drive mount points
        for drive_letter in ["G", "H", "I", "D", "E", "F"]:
            gdrive = Path(f"{drive_letter}:/My Drive")
            if gdrive.exists():
                return gdrive
        # Check for Google Drive in user's home directory
        home = Path.home()
        possible_paths = [
            home / "Google Drive",
            home / "GoogleDrive",
        ]
        for path in possible_paths:
            if path.exists():
                return path
        # Return None - no Google Drive found on Windows
        return None
    
    else:  # Linux and others
        home = Path.home()
        # Google Drive is typically accessed via third-party tools on Linux
        gdrive = home / "google-drive"
        if gdrive.exists():
            return gdrive
        old_gdrive = home / "Google Drive"
        if old_gdrive.exists():
            return old_gdrive
        # Return None - no Google Drive found
        return None


def get_path_from_env(env_var: str, default: Path | None) -> Path:
    """Get a path from environment variable or use default."""
    env_value = os.environ.get(env_var)
    if env_value:
        return Path(env_value)
    if default is None:
        raise ValueError(
            f"\n\n"
            f"ERROR: Could not auto-detect your Obsidian vault path.\n"
            f"Please set the {env_var} environment variable.\n\n"
            f"Options:\n"
            f"  1. Create a .env file with: {env_var}=/path/to/your/obsidian/vault\n"
            f"  2. Set the environment variable before running:\n"
            f"     Windows (PowerShell): $env:{env_var}=\"C:/path/to/vault\"\n"
            f"     Windows (CMD):        set {env_var}=C:/path/to/vault\n"
            f"     macOS/Linux:          export {env_var}=/path/to/vault\n\n"
            f"See env.example for more details.\n"
        )
    return default


def _get_vault_path() -> Path:
    """Get the vault path from environment or auto-detect."""
    gdrive_path = get_default_google_drive_path()
    default_vault = gdrive_path / "Obsidian" if gdrive_path else None
    return get_path_from_env("OBSIDIAN_VAULT_PATH", default_vault)


@dataclass
class Paths:
    # Base paths - can be overridden via environment variables
    vault_path: Path = field(default_factory=_get_vault_path)
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
