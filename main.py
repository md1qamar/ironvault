#!/usr/bin/env python3
"""
IronVault – Secure Offline Desktop Password Manager
Main executable entrypoint.
"""

import sys
import os

# Add local directory to path for clean imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import IronVaultApp

def main():
    try:
        app = IronVaultApp()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error running IronVault: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
