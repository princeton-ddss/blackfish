# blackfish-ui

The [Blackfish](https://github.com/princeton-ddss/blackfish) user interface.

**Code coverage**

| Statements                  | Branches                | Functions                 | Lines             |
| --------------------------- | ----------------------- | ------------------------- | ----------------- |
| ![Statements](https://img.shields.io/badge/statements-13.19%25-red.svg?style=flat) | ![Branches](https://img.shields.io/badge/branches-74.4%25-red.svg?style=flat) | ![Functions](https://img.shields.io/badge/functions-42.22%25-red.svg?style=flat) | ![Lines](https://img.shields.io/badge/lines-13.19%25-red.svg?style=flat) |

This repo is primarily for development purposes as the Blackfish application ships with a standalone front end build. Notably, token-based authentication does not work when running the UI and API separately.

## Getting Started

Almost all of the UI functionality depends on the Blackfish API, so first install that if you haven't already and get it running.

Next, clone the repo, install dependencies and run the development server:

```bash
git clone https://github.com/princeton-ddss/blackfish-ui.git && cd blackfish-ui
npm install
npm run dev
```

Now visit [http://localhost:3000/dashboard](http://localhost:3000/dashboard) and choose your adventure!

## Development

`blackfish-ui` is a [Next.js](https://nextjs.org/) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Production

To create a build of the UI, run `npm run build`. This will produce a `build` directory that can be served using your favorite technology.

## Configuration

By default, the UI looks for the Blackfish API at `http://localhost:8000/dashboard`. If the API is running on a different host or port, you can communicate this to the UI by setting the `NEXT_PUBLIC_BLACKFISH_HOST` and `NEXT_PUBLIC_BLACKFISH_PORT` environment variables *before* running the development server or build process.
