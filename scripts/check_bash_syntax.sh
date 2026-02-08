#!/bin/bash
# Проверка синтаксиса всех bash скриптов

echo "🔍 Проверка синтаксиса bash скриптов..."
echo ""

errors=0
checked=0

for script in scripts/*.sh; do
    if [ -f "$script" ]; then
        checked=$((checked + 1))
        if bash -n "$script" 2>/dev/null; then
            echo "✅ $script"
        else
            echo "❌ $script - ОШИБКА СИНТАКСИСА:"
            bash -n "$script" 2>&1 | sed 's/^/   /'
            errors=$((errors + 1))
        fi
    fi
done

echo ""
echo "═══════════════════════════════════════"
if [ $errors -eq 0 ]; then
    echo "✅ Все скрипты корректны ($checked проверено)"
    exit 0
else
    echo "❌ Найдено ошибок: $errors из $checked скриптов"
    exit 1
fi
