"""
Server Validator

Validates MCP servers by checking NPM package availability and local installations.
Supports caching to reduce network calls and offline mode.
"""

import asyncio
import aiohttp
import json
import logging
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
from models.server import MCPServer, ValidationStatus
from utils.constants import CONFIG_DIR

logger = logging.getLogger(__name__)

# Validation cache file
CACHE_FILE = CONFIG_DIR / "cc-validation-cache.json"
CACHE_EXPIRY_HOURS = 24
NPM_REGISTRY_URL = "https://registry.npmjs.org"
NPM_TIMEOUT = 5  # seconds


class ServerValidator:
    """Validates MCP servers with caching support"""

    def __init__(self, skip_validation: bool = False):
        """
        Initialize server validator

        Args:
            skip_validation: Skip validation (offline mode)
        """
        self.skip_validation = skip_validation
        self.cache: Dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self):
        """Load validation cache from disk"""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                logger.info(f"Validation cache loaded: {len(self.cache)} entries")
            else:
                logger.info("No validation cache found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading validation cache: {e}")
            self.cache = {}

    def _save_cache(self):
        """Save validation cache to disk"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
            logger.debug("Validation cache saved")
        except Exception as e:
            logger.error(f"Error saving validation cache: {e}")

    def _get_cache_key(self, server: MCPServer) -> str:
        """Generate cache key for server"""
        if server.type == "stdio":
            # Use command + first arg (usually the package name)
            package = self.extract_package_name(server)
            return f"stdio:{package}"
        elif server.type == "http":
            return f"http:{server.url}"
        return f"unknown:{server.id}"

    def _is_cache_valid(self, cache_entry: dict) -> bool:
        """Check if cache entry is still valid"""
        try:
            last_checked = datetime.fromisoformat(cache_entry.get("last_checked", ""))
            age = datetime.now(timezone.utc) - last_checked
            return age < timedelta(hours=CACHE_EXPIRY_HOURS)
        except Exception:
            return False

    def extract_package_name(self, server: MCPServer) -> Optional[str]:
        """
        Extract NPM package name from server args

        Args:
            server: MCPServer instance

        Returns:
            Package name or None if not found
        """
        if server.type != "stdio" or not server.args:
            return None

        # Look for npx patterns: npx -y @scope/package or npx package-name
        args = server.args
        for i, arg in enumerate(args):
            if arg in ["npx", "-y"] and i + 1 < len(args):
                # Next arg after npx or -y is likely the package
                next_arg = args[i + 1]
                if next_arg not in ["-y", "--yes"]:
                    return next_arg

        # Fallback: last arg that looks like a package (@scope/name or package-name)
        for arg in reversed(args):
            if arg.startswith("@") or ("-" in arg and not arg.startswith("-")):
                return arg

        return None

    async def check_npm_package(self, package_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if NPM package exists in registry

        Args:
            package_name: Package name (e.g., '@modelcontextprotocol/server-filesystem')

        Returns:
            Tuple of (exists, version, error_message)
        """
        try:
            url = f"{NPM_REGISTRY_URL}/{package_name}"
            timeout = aiohttp.ClientTimeout(total=NPM_TIMEOUT)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        version = data.get("dist-tags", {}).get("latest", "unknown")
                        logger.debug(f"NPM package '{package_name}' found: {version}")
                        return True, version, None
                    elif response.status == 404:
                        logger.debug(f"NPM package '{package_name}' not found")
                        return False, None, "Package not found in NPM registry"
                    else:
                        error = f"NPM registry returned status {response.status}"
                        logger.warning(error)
                        return False, None, error

        except asyncio.TimeoutError:
            error = f"Timeout checking NPM package '{package_name}'"
            logger.warning(error)
            return False, None, error
        except Exception as e:
            error = f"Error checking NPM package '{package_name}': {e}"
            logger.error(error)
            return False, None, error

    def check_local_installation(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check if package is installed locally (global npm)

        Args:
            package_name: Package name

        Returns:
            Tuple of (installed, version)
        """
        try:
            if shutil.which("npm") is None:
                logger.warning("npm executable not found; skipping local check for '%s'", package_name)
                return False, None

            # Run: npm list -g <package> --depth=0 --json
            result = subprocess.run(
                ["npm", "list", "-g", package_name, "--depth=0", "--json"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                dependencies = data.get("dependencies", {})
                if package_name in dependencies:
                    version = dependencies[package_name].get("version", "unknown")
                    logger.debug(f"Package '{package_name}' installed locally: {version}")
                    return True, version

            logger.debug(f"Package '{package_name}' not installed locally")
            return False, None

        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking local installation of '{package_name}'")
            return False, None
        except FileNotFoundError:
            logger.warning("npm executable not found while checking '%s'", package_name)
            return False, None
        except Exception as e:
            logger.error(f"Error checking local installation of '{package_name}': {e}")
            return False, None

    async def validate_server(self, server: MCPServer, force_refresh: bool = False) -> MCPServer:
        """
        Validate a single server

        Args:
            server: MCPServer to validate
            force_refresh: Bypass cache and force fresh validation

        Returns:
            MCPServer with updated validation status
        """
        # Skip validation if in offline mode
        if self.skip_validation and not force_refresh:
            logger.debug(f"Skipping validation for '{server.id}' (offline mode)")
            return server

        # Check cache
        cache_key = self._get_cache_key(server)
        if not force_refresh and cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry):
                logger.debug(f"Using cached validation for '{server.id}'")
                server.validation = ValidationStatus.from_dict(cache_entry)
                server.validation.cached = True
                return server

        # Perform validation
        validation = ValidationStatus()
        validation.last_checked = datetime.now(timezone.utc)
        validation.cached = False

        if server.type == "stdio":
            package_name = self.extract_package_name(server)
            if package_name:
                # Check NPM registry
                npm_available, npm_version, error = await self.check_npm_package(package_name)
                validation.npm_available = npm_available
                validation.npm_version = npm_version
                validation.error_message = error

                # Check local installation
                locally_installed, local_version = self.check_local_installation(package_name)
                validation.locally_installed = locally_installed
                validation.local_version = local_version

                logger.info(f"Validated '{server.id}': NPM={npm_available}, Local={locally_installed}")
            else:
                validation.error_message = "Could not extract package name from server args"
                logger.warning(f"Could not extract package name for '{server.id}'")

        elif server.type == "http":
            # For HTTP servers, just check if URL is reachable (optional, can be expensive)
            # For now, mark as valid if URL exists
            if server.url:
                validation.npm_available = True  # Not NPM, but use field to indicate "valid"
                logger.info(f"HTTP server '{server.id}' validated (URL present)")
            else:
                validation.error_message = "No URL specified"

        # Update server
        server.validation = validation

        # Cache result
        self.cache[cache_key] = validation.to_dict()
        self._save_cache()

        return server

    async def validate_all_servers(self, servers: Dict[str, MCPServer],
                                    force_refresh: bool = False) -> Dict[str, MCPServer]:
        """
        Validate all servers in parallel

        Args:
            servers: Dictionary of server_id -> MCPServer
            force_refresh: Bypass cache for all servers

        Returns:
            Updated dictionary of servers with validation status
        """
        logger.info(f"Validating {len(servers)} servers...")

        # Create validation tasks
        tasks = [
            self.validate_server(server, force_refresh)
            for server in servers.values()
        ]

        # Run in parallel
        validated_servers = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dict
        result = {}
        for i, server_or_exception in enumerate(validated_servers):
            if isinstance(server_or_exception, Exception):
                # Log error and use original server
                server_id = list(servers.keys())[i]
                logger.error(f"Error validating server '{server_id}': {server_or_exception}")
                result[server_id] = servers[server_id]
            else:
                result[server_or_exception.id] = server_or_exception

        logger.info(f"Validation complete: {len(result)} servers")
        return result

    def refresh_cache(self):
        """Clear validation cache to force fresh checks"""
        self.cache.clear()
        try:
            if CACHE_FILE.exists():
                CACHE_FILE.unlink()
            logger.info("Validation cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")