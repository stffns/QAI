#!/bin/bash
# Script para merge rápido de develop a main
# Uso: ./scripts/quick-merge.sh "mensaje de commit"

set -e

COMMIT_MSG="${1:-Merge develop to main}"
CURRENT_BRANCH=$(git branch --show-current)

echo "🔄 Quick merge script started..."
echo "📍 Current branch: $CURRENT_BRANCH"

# 1. Asegurar que estamos en develop
if [ "$CURRENT_BRANCH" != "develop" ]; then
    echo "⚠️  Switching to develop branch..."
    git checkout develop
fi

# 2. Pull latest changes
echo "📥 Pulling latest changes..."
git pull origin develop

# 3. Run quality checks
echo "🔍 Running quality checks..."
make qa-check || {
    echo "❌ Quality checks failed. Fix issues before merging."
    exit 1
}

# 4. Run tests
echo "🧪 Running tests..."
make test || {
    echo "❌ Tests failed. Fix issues before merging."
    exit 1
}

# 5. Switch to main and merge
echo "🔄 Switching to main..."
git checkout main
git pull origin main

echo "🔀 Merging develop into main..."
git merge develop --no-ff -m "$COMMIT_MSG"

# 6. Push to main
echo "📤 Pushing to main..."
git push origin main

# 7. Return to develop
echo "🔄 Returning to develop..."
git checkout develop

echo "✅ Merge completed successfully!"
echo "🎉 Changes are now in main branch"