#!/bin/bash
# Setup script for FTreeKG development environment
# Usage: ./scripts/setup.sh [--with-kgrag]

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

WITH_KGRAG=false
if [[ "$1" == "--with-kgrag" ]]; then
    WITH_KGRAG=true
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "FTreeKG Development Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo

# Check if poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed. Install it with:"
    echo "   curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

echo "📦 Installing dependencies with Poetry..."
if [ "$WITH_KGRAG" = true ]; then
    echo "   (including KGRAG integration)"
    poetry install --extras kgdeps
else
    echo "   (standalone mode; use --with-kgrag for KGRAG integration)"
    poetry install
fi
echo "✓ Dependencies installed"
echo

# Run poetry show to display versions
echo "📋 Installed packages:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
poetry show | grep -E "^(ftree-kg|pycode-kg|doc-kg|pytest|ruff|ty)" || echo "   (main packages shown above)"
echo

# Get Python version
PYTHON_VERSION=$(poetry run python --version)
echo "🐍 $PYTHON_VERSION"
echo

# Verify ftree_kg installation
echo "✨ Verifying FileTreeKG installation..."
poetry run python -c "import ftree_kg; print(f'  ✓ ftree_kg: {ftree_kg.__all__}')"
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo
if [ "$WITH_KGRAG" = true ]; then
    echo "📚 KGRAG integration enabled"
else
    echo "💡 Tip: Add KGRAG integration with:"
    echo "     poetry install --with kgrag"
fi
echo
echo "Next steps:"
echo "  1. Activate the environment:"
echo "     poetry shell"
echo
echo "  2. Run tests:"
echo "     poetry run pytest"
echo
echo "  3. Format code:"
echo "     poetry run ruff format src tests conftest.py"
echo
echo "  4. Build knowledge graphs:"
echo "     poetry run pycodekg build --repo ."
echo "     poetry run dockg build --repo ."
echo
echo "Quick command reference:"
echo "     make help"
echo
