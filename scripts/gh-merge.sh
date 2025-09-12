#!/bin/bash
# Script para crear PR y hacer merge usando GitHub CLI
# Uso: ./scripts/gh-merge.sh "título del PR" "descripción opcional"

set -e

TITLE="${1:-Automated merge from current branch}"
DESCRIPTION="${2:-Automated merge via GitHub CLI}"
CURRENT_BRANCH=$(git branch --show-current)

echo "🔄 GitHub CLI merge script started..."
echo "📍 Current branch: $CURRENT_BRANCH"

# Validar que no estamos en develop
if [ "$CURRENT_BRANCH" = "develop" ]; then
    echo "❌ Cannot create PR from develop to develop"
    echo "💡 Switch to a feature branch first: git checkout -b feature/your-feature"
    exit 1
fi

# 1. Push current branch
echo "📤 Pushing current branch..."
git push origin "$CURRENT_BRANCH" || {
    echo "📤 Setting upstream and pushing..."
    git push -u origin "$CURRENT_BRANCH"
}

# 2. Run quality checks
echo "🔍 Running quality checks..."
make qa-check || {
    echo "❌ Quality checks failed. Fix issues before creating PR."
    exit 1
}

# 3. Run tests
echo "🧪 Running tests..."
make test || {
    echo "❌ Tests failed. Fix issues before creating PR."
    exit 1
}

# 4. Create PR using GitHub CLI
echo "📋 Creating Pull Request..."
PR_URL=$(gh pr create \
    --title "$TITLE" \
    --body "$DESCRIPTION" \
    --base develop \
    --head "$CURRENT_BRANCH")

echo "✅ PR created: $PR_URL"

# 5. Como admin, hacer merge automáticamente
echo "🔀 Auto-merging as admin..."
PR_NUMBER=$(gh pr view --json number --jq .number)

# Enable auto-merge (requiere que el PR pase checks si los hay)
gh pr merge "$PR_NUMBER" --auto --squash --delete-branch

echo "✅ Auto-merge enabled!"
echo "🎉 PR will be merged automatically once all checks pass"
echo "🔗 View PR: $PR_URL"

# Opcional: volver a develop
echo "🔄 Switching back to develop..."
git checkout develop
git pull origin develop

echo "✅ Merge process completed!"