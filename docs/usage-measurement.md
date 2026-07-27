# Usage measurement decision

The application will use first-party aggregate counters rather than external
analytics. The only events needed for the current product decision are:

- `public_view`: a successful watchlist page read.
- `successful_add`: an authorized add that commits an entry.
- `recommendation_view`: a recommendation page request that reaches a rendered
  result, empty state, or safe provider/database error state.

Counters are stored by application date and event name in
`public.usage_daily`. No IP address, user agent, referrer, title, account ID,
browser identifier, or free-form payload is stored. The single admin remains a
single owner; these counters must never be described as registered-user counts.

The table has a small allowlist and row-level security enabled. The Flask
server records counters through its existing direct PostgreSQL connection; no
browser or external analytics provider receives the events. If the counter
write fails, the user-facing request still succeeds and the failure is logged
as a safe diagnostic event.

The first real usage summary remains blocked until the production database
route is healthy and a dated observation period can be recorded.
