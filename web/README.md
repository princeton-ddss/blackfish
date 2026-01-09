![Statements](https://img.shields.io/badge/statements-13.19%25-red.svg?style=flat)
![Branches](https://img.shields.io/badge/branches-74.4%25-red.svg?style=flat)
![Functions](https://img.shields.io/badge/functions-42.22%25-red.svg?style=flat)
![Lines](https://img.shields.io/badge/lines-13.19%25-red.svg?style=flat)

# Blackfish UI

Next.js web application `blackfish-ui` for the [Blackfish](../) MLaaS platform.

For project overview and usage instructions, see the [main README](../README.md).

## Development Setup

```bash
cd web
npm install        # Install dependencies
npm run dev        # Start dev server at localhost:3000
```

> [!NOTE]
> The UI depends on the Blackfish API. Start the backend first with `blackfish start`.

## Common Commands

```bash
# Development
npm run dev                    # Start development server
npm run build                  # Production build
npm run build:lib              # Build and copy to Python package

# Testing & Linting
npm test                       # Run Jest tests
npm run lint                   # ESLint check
```

## Build for Production

The frontend is bundled with the Python package:

```bash
npm run build:lib  # Builds and copies to ../lib/src/blackfish/build/
```

This allows the Python server to serve the UI as static files.

## Configuration

By default, the UI looks for the Blackfish API at `http://localhost:8000`. Set these environment variables to use a different endpoint:

- `NEXT_PUBLIC_BLACKFISH_HOST` - API host
- `NEXT_PUBLIC_BLACKFISH_PORT` - API port

## Documentation

- [Full Documentation](https://princeton-ddss.github.io/blackfish/)
- [Main README](../README.md)
