# Blackfish Frontend

Vite + React application `blackfish-ui` for the Blackfish platform.

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
npm run preview                # Preview production build

# Testing
npm test                       # Run Vitest tests
npm run test:watch             # Run tests in watch mode
npm run test:coverage          # Run tests with coverage

# Linting
npm run lint                   # ESLint check
npm run lint:fix               # Auto-fix lint issues
```

## Project Structure

```
web/
├── index.html                 # Entry point (Jinja template)
├── vite.config.js             # Vite configuration
├── vitest.config.js           # Vitest test configuration
├── src/
│   ├── main.jsx               # React entry point
│   ├── router.jsx             # React Router configuration
│   ├── config.js              # Runtime configuration
│   ├── index.css              # Global styles
│   ├── components/            # Shared components
│   ├── layouts/               # Layout components
│   ├── lib/                   # Utilities and hooks
│   ├── providers/             # React context providers
│   ├── routes/                # Page components
│   │   ├── dashboard.jsx
│   │   ├── login.jsx
│   │   ├── text-generation.jsx
│   │   ├── speech-recognition.jsx
│   │   └── {service}/components/  # Service-specific components
│   └── test/                  # Test setup
├── public/                    # Static assets
└── build/                     # Production output
```

## Code Patterns

### Adding a New Page
1. Create component in `src/routes/{page-name}.jsx`
2. Add route to `src/router.jsx`
3. Service pages should have `src/routes/{service}/components/` for service-specific components

### Component Guidelines
- Shared components go in `src/components/`
- Service-specific components in `src/routes/{service}/components/`
- Use Tailwind CSS for styling
- Use Headless UI for accessible interactive components
- Use Heroicons for icons

### Data Fetching
- Use SWR for client-side data fetching
- API calls go through the backend at configured endpoint
- Runtime config available via `src/config.js`

### Testing
- Tests are colocated with components (`.test.jsx` suffix)
- Use React Testing Library patterns
- Vitest stores snapshots in `__snapshots__/` directories next to test files

## Key Files

- `index.html` - Entry point, includes runtime config injection
- `src/main.jsx` - React app entry point
- `src/router.jsx` - React Router configuration with basename support
- `src/config.js` - Runtime configuration (API URL, base path)
- `vite.config.js` - Vite build configuration
- `vitest.config.js` - Test configuration
- `tailwind.config.js` - Tailwind theme customization

## Configuration

Runtime configuration is injected by the Python backend into `index.html`:

```javascript
window.__BLACKFISH_CONFIG__ = {
  apiUrl: "http://host:port/basepath",
  basePath: "/basepath"
};
```

This enables deployment at arbitrary base paths (e.g., Open OnDemand).

## Building for Production

The frontend is bundled with the Python package:
```bash
npm run build:lib  # Builds and copies to ../lib/src/blackfish/build/
```

The build uses `base: './'` for relative asset paths, allowing the app to work from any URL path.
