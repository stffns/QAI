# Branch Protection Strategy - QA Intelligence

## 🌟 Branching Strategy

### Protected Branches

#### `main` (Production Branch)
- **🔒 PROTECTED**: No direct pushes allowed
- **🔄 Pull Request Required**: All changes must go through PR review
- **✅ Status Checks**: All CI/CD checks must pass
- **👥 Code Review**: At least 1 approving review required
- **🚫 Force Push**: Disabled
- **🗑️ Branch Deletion**: Disabled

#### `develop` (Integration Branch)  
- **🔄 Pull Request Recommended**: For major features and releases
- **✅ Status Checks**: All tests must pass
- **🔄 Merge Strategy**: Squash and merge preferred

### Workflow Strategy

```
main (protected)
 ↑
 └── develop (integration)
      ↑
      ├── feature/websocket-enhancements
      ├── feature/qa-agent-improvements
      ├── bugfix/config-validation
      └── hotfix/security-patch (emergency only)
```

## 🔄 Development Workflow

### 1. Feature Development
```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/new-feature-name

# Work on feature...
# Commit changes...

# Push feature branch
git push -u origin feature/new-feature-name

# Create PR: feature/new-feature-name → develop
```

### 2. Release Process
```bash
# Create release branch from develop
git checkout develop
git checkout -b release/v1.1.0

# Finalize release (version bumps, changelog, etc.)
# Test release...

# Create PRs:
# release/v1.1.0 → main (production release)
# release/v1.1.0 → develop (merge back any release fixes)
```

### 3. Hotfix Process
```bash
# Emergency fix directly from main
git checkout main
git checkout -b hotfix/critical-security-fix

# Fix the issue...
# Test thoroughly...

# Create PRs:
# hotfix/critical-security-fix → main (immediate fix)
# hotfix/critical-security-fix → develop (keep in sync)
```

## 📋 Branch Naming Conventions

- **Features**: `feature/description-of-feature`
- **Bug Fixes**: `bugfix/description-of-bug`
- **Hotfixes**: `hotfix/description-of-critical-fix`
- **Releases**: `release/version-number`
- **Experiments**: `experiment/description-of-experiment`

## ✅ Commit Message Standards

```
type(scope): description

feat(websocket): add real-time QA agent integration
fix(config): resolve API key case sensitivity issue
docs(readme): update installation instructions
refactor(auth): improve JWT token validation
test(websocket): add comprehensive integration tests
chore(deps): update Agno framework to 1.8.1
```

## 🛡️ Protection Rules to Configure on GitHub

### For `main` branch:
1. **Require pull request reviews before merging**
   - Required approving reviews: 1
   - Dismiss stale reviews when new commits are pushed
   - Require review from code owners

2. **Require status checks to pass before merging**
   - Require branches to be up to date before merging
   - Status checks: CI/CD pipeline, tests, linting

3. **Restrict pushes that create files**
   - Restrict pushes that create files larger than 100MB

4. **Restrictions**
   - Include administrators: Yes (even admins need PRs)

### For `develop` branch:
1. **Require status checks to pass before merging**
   - All tests must pass
   - Code quality checks must pass

## 🚀 Ready for Team Collaboration

This branching strategy ensures:
- **🔒 Production Stability**: Main branch is always stable
- **🔄 Continuous Integration**: Develop branch for ongoing work
- **👥 Code Quality**: All changes reviewed before merging
- **📈 Scalability**: Easy to add team members and features
- **🛡️ Safety**: Protected branches prevent accidental damage

## 📞 Quick Commands Reference

```bash
# Check current branch
git branch

# Switch to develop for new work
git checkout develop
git pull origin develop

# Create new feature
git checkout -b feature/my-new-feature

# Push and create PR
git push -u origin feature/my-new-feature
# Then create PR on GitHub: feature/my-new-feature → develop
```
