"""Authentication and authorization: JWT validation and RBAC dependencies.

Only token validation and request-scoped auth dependencies live here. User
creation, session issuing, and token refresh all belong to Supabase Auth
(the hosted JWT issuer), which is why this package contains no login or
registration code.
"""