#!/usr/bin/env python3
"""
Arquivo alias para resetar contatos.
Use: python reset_contatos.py
Ou diretamente com: python main.py reset
"""

import sys
import subprocess

if __name__ == "__main__":
    subprocess.run([sys.executable, "main.py", "reset"])
