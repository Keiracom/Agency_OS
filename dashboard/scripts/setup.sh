#!/bin/bash

# Elliot Dashboard Setup Script
# Run this to configure your environment

set -e

echo "🤖 Elliot Dashboard Setup"
echo "========================="
echo ""

# Check if .env exists
if [ -f ".env.local" ]; then
    echo "✅ .env.local already exists"
else
    # Try to copy from agency-os config
    if [ -f "$HOME/.config/agency-os/.env" ]; then
        echo "📋 Found agency-os config, extracting Supabase credentials..."
        
        SUPABASE_URL=$(grep "^SUPABASE_URL=" "$HOME/.config/agency-os/.env" | cut -d= -f2-)
        SUPABASE_ANON_KEY=$(grep "^SUPABASE_ANON_KEY=" "$HOME/.config/agency-os/.env" | cut -d= -f2-)
        SUPABASE_SERVICE_ROLE_KEY=$(grep "^SUPABASE_SERVICE_ROLE_KEY=" "$HOME/.config/agency-os/.env" | cut -d= -f2-)
        
        if [ -n "$SUPABASE_URL" ]; then
            cat > .env.local << EOF
# Supabase Configuration (from agency-os)
SUPABASE_URL=$SUPABASE_URL
SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY

# Public keys (exposed to browser)
NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL
NEXT_PUBLIC_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY

# API Authentication
ELLIOT_API_TOKEN=$(openssl rand -hex 32)

# Workspace path
ELLIOT_WORKSPACE=/home/elliotbot/clawd
EOF
            echo "✅ Created .env.local with Supabase credentials"
        else
            echo "⚠️  Supabase credentials not found in agency-os config"
            cp .env.example .env.local
            echo "📝 Created .env.local from example - please fill in your credentials"
        fi
    else
        cp .env.example .env.local
        echo "📝 Created .env.local from example - please fill in your credentials"
    fi
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
npm install

# Check if we should run database setup
echo ""
echo "📊 Database Setup"
echo "Run the SQL schema in your Supabase dashboard:"
echo "  - Go to Supabase Dashboard → SQL Editor"
echo "  - Copy contents of supabase-schema.sql"
echo "  - Run the query"
echo ""

# Done
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run database schema: cat supabase-schema.sql"
echo "  2. Start dev server: npm run dev"
echo "  3. Open http://localhost:3000/elliot"
echo ""
echo "To sync memory files:"
echo "  npm run sync"
