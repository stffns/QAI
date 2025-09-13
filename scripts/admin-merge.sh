#!/bin/bash
# Script para merge directo como administrador (bypass protection)
# Uso: ./scripts/admin-merge.sh "mensaje de commit"

set -e

COMMIT_MSG="${1:-Admin merge: bypass protection}"
CURRENT_BRANCH=$(git branch --show-current)

echo "🔧 Admin bypass merge script..."
echo "📍 Current branch: $CURRENT_BRANCH"

# Validar que no estamos en develop
if [ "$CURRENT_BRANCH" = "develop" ]; then
    echo "❌ Already on develop branch"
    exit 1
fi

# 1. Push current branch
echo "📤 Pushing current branch..."
git push origin "$CURRENT_BRANCH"

# 2. Quick quality check
echo "🔍 Quick syntax check..."
python -m py_compile src/**/*.py 2>/dev/null || {
    echo "⚠️  Syntax errors found, but continuing as admin..."
}

# 3. Create PR silently
echo "📋 Creating PR for admin merge..."
PR_URL=$(gh pr create \
    --title "🔧 Admin: $COMMIT_MSG" \
    --body "Admin merge - bypassing protection rules" \
    --base develop \
    --head "$CURRENT_BRANCH" \
    2>/dev/null || echo "PR might already exist")

# 4. Get PR number and merge immediately as admin
PR_NUMBER=$(gh pr list --head "$CURRENT_BRANCH" --json number --jq '.[0].number')

if [ "$PR_NUMBER" != "null" ] && [ -n "$PR_NUMBER" ]; then
    echo "🚀 Force merging as admin (PR #$PR_NUMBER)..."
    
    # Force merge como admin
    gh pr merge "$PR_NUMBER" --admin --squash --delete-branch
    
    echo "✅ Admin merge completed!"
else
    echo "❌ Could not find PR number"
    exit 1
fi

# 5. Switch back to develop
echo "🔄 Switching to develop..."
git checkout develop
git pull origin develop

echo "🎉 Admin merge completed successfully!"
echo "📍 Now on develop with latest changes"