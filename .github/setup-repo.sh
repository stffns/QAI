#!/bin/bash
# 🚀 QAI Repository Setup Script
# Automatically configures branch protection and development workflow

set -e

echo "🔧 QAI Repository Configuration Script"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI (gh) is not installed. Please install it first."
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    print_error "GitHub CLI is not authenticated. Please run 'gh auth login' first."
    exit 1
fi

print_info "Starting repository configuration..."

# Get repository info
REPO_OWNER=$(gh repo view --json owner --jq '.owner.login')
REPO_NAME=$(gh repo view --json name --jq '.name')

print_info "Repository: $REPO_OWNER/$REPO_NAME"

# 1. Configure main branch protection
print_info "Configuring main branch protection..."

gh api repos/$REPO_OWNER/$REPO_NAME/branches/main/protection \
  --method PUT \
  --input - << 'EOF' && print_status "Main branch protection configured"
{
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "restrict_pushes_that_create_files": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# 2. Configure develop branch protection
print_info "Configuring develop branch protection..."

gh api repos/$REPO_OWNER/$REPO_NAME/branches/develop/protection \
  --method PUT \
  --input - << 'EOF' && print_status "Develop branch protection configured"
{
  "required_status_checks": {
    "strict": true,
    "contexts": []
  },
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

# 3. Create GitHub workflow for CI/CD
print_info "Creating GitHub Actions workflow..."

mkdir -p .github/workflows

cat > .github/workflows/ci.yml << 'EOF'
name: CI/CD Pipeline

on:
  push:
    branches: [ develop, main ]
  pull_request:
    branches: [ develop, main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run linting
      run: |
        make format-check
        make lint
    
    - name: Run type checking
      run: |
        make type-check
    
    - name: Run tests
      run: |
        make test
    
    - name: Run security scan
      run: |
        make security-check

  websocket-test:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.12
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Test WebSocket system
      run: |
        python -m pytest src/websocket/tests/ -v
    
    - name: Test QA Agent integration
      run: |
        python -c "from src.websocket.qa_agent_adapter import QAAgentAdapter; print('QA Agent adapter working')"

EOF

print_status "GitHub Actions workflow created"

# 4. Create pull request template
print_info "Creating pull request template..."

cat > .github/pull_request_template.md << 'EOF'
## 🎯 Pull Request Description

### What does this PR do?
<!-- Brief description of changes -->

### Type of change
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Configuration/infrastructure change
- [ ] 🧪 Test improvements

### Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] WebSocket tests pass (if applicable)
- [ ] Manual testing completed

### QA Intelligence Specific
- [ ] QA Agent functionality tested
- [ ] Configuration validation passed
- [ ] Memory system working (if applicable)
- [ ] WebSocket integration tested (if applicable)

### Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Documentation updated if needed
- [ ] No new warnings or errors introduced
- [ ] Branch is up to date with target branch

### Related Issues
<!-- Link any related issues -->
Closes #

### Screenshots (if applicable)
<!-- Add screenshots to help explain your changes -->

EOF

print_status "Pull request template created"

# 5. Create issue templates
print_info "Creating issue templates..."

mkdir -p .github/ISSUE_TEMPLATE

cat > .github/ISSUE_TEMPLATE/bug_report.yml << 'EOF'
name: 🐛 Bug Report
description: Report a bug in QA Intelligence
title: "[Bug]: "
labels: ["bug", "triage"]

body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report for QA Intelligence!

  - type: input
    id: component
    attributes:
      label: Component
      description: Which component is affected?
      placeholder: "e.g., QA Agent, WebSocket, Configuration, Memory"
    validations:
      required: true

  - type: textarea
    id: description
    attributes:
      label: Bug Description
      description: A clear and concise description of what the bug is.
    validations:
      required: true

  - type: textarea
    id: reproduction
    attributes:
      label: Steps to Reproduce
      description: Steps to reproduce the behavior
      placeholder: |
        1. Go to '...'
        2. Click on '....'
        3. Scroll down to '....'
        4. See error
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: What you expected to happen
    validations:
      required: true

  - type: textarea
    id: environment
    attributes:
      label: Environment
      description: |
        Please provide information about your environment:
      value: |
        - OS: [e.g. macOS, Windows, Linux]
        - Python version: [e.g. 3.11]
        - QAI version: [e.g. main branch, commit hash]
        - Agno version: [e.g. 1.8.1]
    validations:
      required: true

  - type: textarea
    id: logs
    attributes:
      label: Logs
      description: Please copy and paste any relevant log output
      render: shell

EOF

cat > .github/ISSUE_TEMPLATE/feature_request.yml << 'EOF'
name: ✨ Feature Request
description: Suggest a new feature for QA Intelligence
title: "[Feature]: "
labels: ["enhancement", "triage"]

body:
  - type: markdown
    attributes:
      value: |
        Thanks for suggesting a feature for QA Intelligence!

  - type: input
    id: component
    attributes:
      label: Component
      description: Which component would this feature affect?
      placeholder: "e.g., QA Agent, WebSocket, Configuration, Tools"
    validations:
      required: true

  - type: textarea
    id: problem
    attributes:
      label: Problem Description
      description: Is your feature request related to a problem? Please describe.
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: Proposed Solution
      description: Describe the solution you'd like
    validations:
      required: true

  - type: textarea
    id: alternatives
    attributes:
      label: Alternatives Considered
      description: Describe any alternative solutions or features you've considered

  - type: textarea
    id: context
    attributes:
      label: Additional Context
      description: Add any other context or screenshots about the feature request

EOF

print_status "Issue templates created"

# 6. Update repository settings
print_info "Updating repository settings..."

# Enable discussions, wiki, and projects
gh api repos/$REPO_OWNER/$REPO_NAME \
  --method PATCH \
  --field has_discussions=true \
  --field has_wiki=true \
  --field has_projects=true \
  --field delete_branch_on_merge=true \
  --field allow_squash_merge=true \
  --field allow_merge_commit=true \
  --field allow_rebase_merge=true

print_status "Repository settings updated"

# 7. Summary
echo ""
echo "🎉 Repository Configuration Complete!"
echo "====================================="
print_status "Main branch protection: Requires PR reviews and admin enforcement"
print_status "Develop branch protection: Basic protection against force pushes"
print_status "GitHub Actions: CI/CD pipeline configured"
print_status "Templates: PR and issue templates created"
print_status "Settings: Discussions, wiki, and projects enabled"

echo ""
print_info "Next steps:"
echo "1. Test the setup by creating a feature branch:"
echo "   git checkout -b feature/test-setup"
echo "   git push -u origin feature/test-setup"
echo ""
echo "2. Create a PR from feature branch to develop"
echo ""
echo "3. After review, merge to develop"
echo ""
echo "4. Create PR from develop to main for releases"

echo ""
print_warning "Remember: Always work from develop branch for new features!"
echo ""
EOF
