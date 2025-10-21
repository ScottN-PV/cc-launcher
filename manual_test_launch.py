"""Manual test script for terminal launch functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.terminal_manager import TerminalManager
from models.server import MCPServer

def test_launch():
    """Test the terminal launch command building."""

    print("=== Manual Terminal Launch Test ===\n")

    # Create terminal manager
    tm = TerminalManager()

    # Find available terminal
    terminal_type = tm.find_terminal()
    print(f"[OK] Found terminal: {terminal_type}")

    # Create a test project directory
    test_project = Path.cwd()
    print(f"[OK] Test project: {test_project}")

    # Create sample server
    test_servers = {
        "filesystem": MCPServer(
            id="filesystem",
            type="stdio",
            command="cmd",
            args=["/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", str(test_project)],
            enabled=True
        )
    }

    # Generate MCP config
    print("\n--- Generating MCP Config ---")
    try:
        config_path = tm.generate_mcp_config(test_servers, str(test_project))
        print(f"[OK] Config generated: {config_path}")

        # Read and display the config
        import json
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"[OK] Config contents:")
        print(json.dumps(config, indent=2))
    except Exception as e:
        print(f"[ERROR] Config generation failed: {e}")
        return False

    # Build launch command
    print("\n--- Building Launch Command ---")
    try:
        command = tm.build_launch_command(terminal_type, str(test_project), config_path)
        print(f"[OK] Command built:")
        print(f"  Command list: {command}")
        print(f"  Command string: {' '.join(command)}")
    except Exception as e:
        print(f"[ERROR] Command build failed: {e}")
        return False

    # Ask user if they want to actually launch
    print("\n--- Launch Options ---")
    print("WARNING: This will attempt to launch Claude Code!")
    print(f"Terminal: {terminal_type}")
    print(f"Project: {test_project}")
    print(f"Config: {config_path}")

    response = input("\nDo you want to proceed with launch? (yes/no): ").strip().lower()

    if response == 'yes':
        print("\n--- Launching Claude Code ---")
        try:
            success, message = tm.launch_claude_code(
                test_servers,
                str(test_project),
                allow_multiple=True
            )
            if success:
                print(f"[OK] Launch successful!")
                print(f"  {message}")
            else:
                print(f"[ERROR] Launch failed!")
                print(f"  {message}")
        except Exception as e:
            print(f"[ERROR] Launch exception: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("[OK] Skipping launch (user declined)")
        # Clean up temp config
        tm.cleanup_temp_config()

    print("\n=== Test Complete ===")
    return True

if __name__ == "__main__":
    try:
        test_launch()
    except KeyboardInterrupt:
        print("\n\n[ERROR] Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
