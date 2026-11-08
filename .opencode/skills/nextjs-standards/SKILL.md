---
name: nextjs-standards
description: Use when implementing or reviewing Next.js App Router pages, React components, TypeScript UI, data fetching, accessibility, or frontend performance in NEXUS AI. Triggers on Next.js, React, App Router, server component, client component, TypeScript, accessibility, or frontend build.
license: MIT
compatibility: opencode
metadata:
  audience: frontend
  version: "1.0"
---

# Next.js Standards

## When to use

Use for frontend work in the Next.js application: pages, layouts, components, data fetching, forms, state, accessibility, and performance. Do not use for backend API implementation.

## Instructions

1. Inspect the existing app structure, component conventions, and styling approach before adding patterns.
2. Prefer server components by default. Add `"use client"` only when browser state, effects, or event handlers are required.
3. Keep data fetching at the server boundary where possible. Do not leak secrets or privileged API calls into client bundles.
4. Type props and API responses. Avoid `any`.
5. Handle loading, empty, error, unauthorized, and success states explicitly.
6. Use semantic HTML, labeled controls, keyboard navigation, and visible focus states.
7. Keep client components small. Avoid unnecessary global state.
8. Use `next/image` or an equivalent optimized image path when images are present.
9. Validate environment variables at the server boundary and never expose server-only values.
10. Add tests for user-visible behavior and critical flows.

## Checklist

- [ ] Existing component and styling conventions checked.
- [ ] Server/client boundary is intentional.
- [ ] Props and data are typed.
- [ ] Loading, empty, error, unauthorized, and success states exist.
- [ ] Keyboard and screen-reader paths are usable.
- [ ] No secrets in client code or public environment variables.
- [ ] Images and heavy client code are handled deliberately.
- [ ] Tests cover the changed behavior.
- [ ] Lint, typecheck, build, and tests were executed.

## Expected output

Component or page change, state handling, accessibility notes, and tests. Report the exact commands run and their observed results.

## Verification

- `npm run lint`, `npm run typecheck`, `npm run build`, and the test command were executed if configured.
- The build output was observed, not assumed.
- No paid hosted service or off-device telemetry was added.
- Client bundle impact is considered and reported when relevant.
