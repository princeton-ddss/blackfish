# Blackfish Frontend

Next.js 14 web application `blackfish-ui` for the Blackfish platform.

## Development Setup

```bash
nvm use              # Use correct Node version (.nvmrc)
npm install          # Install dependencies
npm run dev          # Start dev server at localhost:3000
```

## Common Commands

```bash
# Development
npm run dev                    # Start development server
npm run build                  # Production build
npm run build:lib              # Build and copy to Python package
npm start                      # Start production server

# Testing
npm test                       # Run Jest tests
npm run test:update-snapshots  # Update Jest snapshots

# Linting
npm run lint                   # ESLint check
npm run lint:fix               # Auto-fix lint issues
```

## Project Structure

```
web/
├── app/                       # Next.js App Router
│   ├── layout.js              # Root layout
│   ├── page.js                # Home page
│   ├── globals.css            # Global styles
│   ├── config.js              # App configuration
│   ├── lib/                   # Utilities
│   ├── providers/             # React context providers
│   ├── components/            # Shared components
│   ├── dashboard/             # Dashboard page
│   ├── login/                 # Auth page
│   ├── text-generation/       # Text generation service
│   │   ├── page.js
│   │   ├── lib/
│   │   └── components/
│   └── speech-recognition/    # Speech recognition service
│       ├── page.js
│       ├── lib/
│       └── components/
├── public/                    # Static assets
└── __mocks__/                 # Jest mocks
```

## Code Patterns

### Adding a New Page
1. Create directory in `app/{page-name}/`
2. Add `page.js` (and `layout.js` if needed)
3. Service pages should have `lib/` and `components/` subdirectories

### Component Guidelines
- Shared components go in `app/components/`
- Service-specific components in `app/{service}/components/`
- Use Tailwind CSS for styling
- Use Headless UI for accessible interactive components
- Use Heroicons for icons

### Data Fetching
- Use SWR for client-side data fetching
- API calls go through the backend at configured endpoint

### Testing
- Tests are colocated with components (`.test.js` suffix)
- Use React Testing Library patterns
- Snapshots in `__snapshots__/` directories

## Key Files

- `app/layout.js` - Root layout, providers, global styles
- `app/config.js` - API endpoint configuration
- `app/providers/` - React context providers
- `next.config.js` - Next.js configuration
- `tailwind.config.js` - Tailwind theme customization

## Building for Production

The frontend is bundled with the Python package:
```bash
npm run build:lib  # Builds and copies to ../lib/src/blackfish/build/
```

This allows the Python server to serve the UI as static files.
