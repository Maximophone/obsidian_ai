import asyncio
import argparse
from config.paths import PATHS
from config.logging_config import set_default_log_level, setup_logger
from config import secrets # Necessary to load the dotenv file
from obsidian.obsidian_ai import process_file, needs_answer
from services.file_watcher import start_file_watcher

# Initialize logger for this module
logger = setup_logger(__name__)

async def run_obsidian_ai():
    """Starts the Obsidian file watcher."""
    logger.info("Starting Obsidian file watcher...")
    try:
        # Ensure the VAULT_PATH exists or handle appropriately if needed
        if not PATHS.vault_path.exists():
             logger.warning(f"Obsidian vault path not found: {PATHS.vault_path}. File watcher will not start.")
             return
        await start_file_watcher(PATHS.vault_path, process_file, needs_answer, use_polling=True)
        logger.info("Obsidian file watcher finished.")
    except Exception as e:
        logger.error(f"Error in Obsidian file watcher: {e}", exc_info=True)

async def main():
    """Main function to run the Obsidian AI file watcher."""
    try:
        if not PATHS.vault_path.exists():
             logger.info(f"Creating Obsidian vault directory (if needed): {PATHS.vault_path}")
             PATHS.vault_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
         logger.error(f"Error creating directories: {e}", exc_info=True)
         return

    logger.info("Starting Obsidian AI...")
    try:
        await run_obsidian_ai()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received.")
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
    finally:
        logger.info("Obsidian AI stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Obsidian AI File Watcher')
    parser.add_argument('--log-level',
                        type=str,
                        default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Set the default logging level (default: INFO)')
    args = parser.parse_args()

    set_default_log_level(args.log_level)
    logger.info(f"Logging level set to {args.log_level}")

    try:
        logger.info("Starting Obsidian AI Application...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Obsidian AI Application interrupted by user.")
    except Exception as e:
        logger.critical(f"Obsidian AI Application exited unexpectedly: {e}", exc_info=True)
    finally:
        logger.info("Obsidian AI Application stopped.")
