#!/usr/bin/env python3
"""Проверка синтаксиса всех Python файлов"""

import py_compile
import sys
from pathlib import Path

def check_syntax(file_path: Path) -> bool:
    """Проверить синтаксис одного файла"""
    try:
        py_compile.compile(file_path, doraise=True)
        return True
    except py_compile.PyCompileError as e:
        print(f"❌ {file_path}: {e}")
        return False
    except Exception as e:
        print(f"❌ {file_path}: {e}")
        return False

def main():
    """Проверить все Python файлы"""
    project_root = Path(__file__).parent.parent
    
    # Директории для проверки
    check_dirs = [
        project_root / "src",
        project_root / "tests",
        project_root / "scripts"
    ]
    
    all_files = []
    for directory in check_dirs:
        if directory.exists():
            all_files.extend(directory.rglob("*.py"))
    
    print(f"Проверка {len(all_files)} Python файлов...\n")
    
    errors = []
    for file_path in sorted(all_files):
        relative_path = file_path.relative_to(project_root)
        if check_syntax(file_path):
            print(f"✅ {relative_path}")
        else:
            errors.append(relative_path)
    
    print(f"\n{'='*60}")
    if errors:
        print(f"❌ Найдено ошибок: {len(errors)}")
        for err in errors:
            print(f"   - {err}")
        return 1
    else:
        print(f"✅ Все файлы скомпилированы успешно ({len(all_files)} файлов)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
