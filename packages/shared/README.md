# Shared Package

This package is intended for shared code between frontend and backend, e.g. generated API types and client utilities.

Recommended: Generate TypeScript types from the backend OpenAPI spec:

```
npx openapi-typescript http://localhost:8000/openapi.json -o packages/shared/api-types.ts
```

Then import the types in the frontend.

