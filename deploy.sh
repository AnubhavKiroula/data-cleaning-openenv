#!/bin/bash
# Production Deployment Quick Start
# This script helps you deploy to HF Spaces and Vercel

set -e

echo "======================================"
echo "🚀 Data Cleaning OpenEnv Deployment"
echo "======================================"
echo ""

# Check prerequisites
echo "✓ Checking prerequisites..."
command -v git >/dev/null 2>&1 || { echo "❌ Git not found"; exit 1; }
echo "  ✓ Git installed"

# Get deployment target
echo ""
echo "Select deployment target:"
echo "1) HuggingFace Spaces (backend)"
echo "2) Vercel (frontend)"
echo "3) Both (HF Spaces + Vercel)"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "🌐 Deploying to HuggingFace Spaces"
        echo "=================================="
        echo ""
        echo "Prerequisites:"
        echo "  1. HuggingFace account (https://huggingface.co)"
        echo "  2. GitHub repo connected to HF (AnubhavKiroula/data-cleaning-openenv)"
        echo ""
        echo "Steps:"
        echo "  1. Go to https://huggingface.co/spaces"
        echo "  2. Click 'Create new Space'"
        echo "  3. Fill in:"
        echo "     - Space name: data-cleaning-openenv"
        echo "     - SDK: Docker"
        echo "  4. Click 'Create Space'"
        echo "  5. In Space settings, link GitHub repo"
        echo "  6. Set environment variables:"
        echo "     - POSTGRES_PASSWORD=<random-string>"
        echo "     - JWT_SECRET=<random-string>"
        echo "     - ENVIRONMENT=production"
        echo ""
        echo "To generate secrets:"
        echo "  python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        echo ""
        read -p "Press Enter when HF Space is configured..."
        echo "✓ HF Space deployment complete!"
        ;;
    2)
        echo ""
        echo "🌐 Deploying to Vercel"
        echo "====================="
        echo ""
        echo "Prerequisites:"
        echo "  1. Vercel account (https://vercel.com)"
        echo "  2. GitHub account connected to Vercel"
        echo ""
        echo "Steps:"
        echo "  1. Go to https://vercel.com/dashboard"
        echo "  2. Click 'Add New' → 'Project'"
        echo "  3. Import: AnubhavKiroula/data-cleaning-openenv"
        echo "  4. Set root directory: frontend"
        echo "  5. Add environment variable:"
        echo "     - VITE_API_BASE_URL=<your-hf-space-url>/api"
        echo "  6. Click 'Deploy'"
        echo ""
        read -p "Press Enter when Vercel is configured..."
        echo "✓ Vercel deployment complete!"
        ;;
    3)
        echo ""
        echo "🌐 Deploying to HuggingFace Spaces + Vercel"
        echo "=========================================="
        echo ""
        echo "Follow the steps for HF Spaces first, then Vercel:"
        echo ""
        echo "=== HuggingFace Spaces ==="
        echo "  1. Go to https://huggingface.co/spaces"
        echo "  2. Create new Space (Docker SDK)"
        echo "  3. Link GitHub repo"
        echo "  4. Set env vars (POSTGRES_PASSWORD, JWT_SECRET)"
        echo ""
        read -p "Press Enter when HF Space is configured..."
        echo ""
        echo "=== Vercel ==="
        echo "  1. Go to https://vercel.com/dashboard"
        echo "  2. Import: AnubhavKiroula/data-cleaning-openenv"
        echo "  3. Set VITE_API_BASE_URL to HF Space URL"
        echo "  4. Deploy"
        echo ""
        read -p "Press Enter when Vercel is configured..."
        echo "✓ Full deployment complete!"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "======================================"
echo "✅ Deployment Started!"
echo "======================================"
echo ""
echo "📋 Next steps:"
echo "  1. Monitor HF Space / Vercel dashboards"
echo "  2. Wait for services to start (~5-10 min)"
echo "  3. Test backend: curl <hf-space-url>/api/health"
echo "  4. Test frontend: Open <vercel-url>"
echo "  5. Run smoke test: Upload CSV and start job"
echo ""
echo "📚 Documentation:"
echo "  - Deployment guide: docs/DEPLOYMENT.md"
echo "  - Production readiness: PRODUCTION_READINESS.md"
echo "  - Environment vars: .env.production.example"
echo ""
echo "🆘 Need help? Check the docs or open a GitHub issue!"
