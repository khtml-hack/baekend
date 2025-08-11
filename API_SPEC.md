# API Specification

Base URL: `/api/`

All endpoints expect and return JSON. Authentication is handled via JWT bearer tokens unless noted.

## Users

### POST `/api/users/register/`
Register a new user.
- **Request Body**: `email`, `username`, `password`, `password_confirm`
- **Response**: `user` object with `id`, `email`, `username`, `nickname`, `date_joined`, plus `refresh` and `access` JWT tokens.

### POST `/api/users/login/` or `/api/users/token/`
Obtain JWT tokens.
- **Request Body**: `email` and `password`
- **Response**: `refresh`, `access`, and `nickname_required` flag.

### POST `/api/users/token/refresh/`
Refresh an access token.
- **Request Body**: `refresh`
- **Response**: new `access` token.

### GET or PUT `/api/users/profile/` (`/api/users/me/` alias)
Retrieve or update the authenticated user's profile.
- **Response**: `id`, `email`, `username`, `nickname`, `date_joined`.

### PATCH `/api/users/nickname/`
Update nickname for the authenticated user.
- **Request Body**: `nickname`
- **Response**: Updated `nickname`.

### POST `/api/users/logout/`
Blacklist a refresh token to log out.
- **Request Body**: `refresh`

## Profiles

### POST `/api/profiles/consents/`
Store a consent record.
- **Request Body**: `consent_type`, `consent_status`
- **Response**: `id`, `consent_type`, `consent_status`, `consented_at`.

### GET or POST `/api/profiles/routes/`
List or create saved routes.
- **Request Body (create)**: `route_type` (`집`, `직장`, `학교`), `address`, `lat`, `lng`
- **Response**: route entries with `id`, `route_type`, `address`, `lat`, `lng`, `created_at`.

### GET, PUT, PATCH, or DELETE `/api/profiles/routes/<id>/`
Manage a specific saved route for the user.

## Trips

### POST `/api/trips/recommend/`
Create a travel recommendation between two addresses.
- **Request Body**: `origin_address`, `destination_address`, optional `region_code`
- **Response**: recommendation with `recommended_bucket`, `window_start`, `window_end`, `expected_duration_min`, `expected_congestion_level`, `rationale`.

### POST `/api/trips/start/<recommendation_id>/`
Start a trip based on a recommendation.
- **Response**: trip data (`id`, `status`, `planned_departure`, `started_at`, etc.) and message.

### POST `/api/trips/arrive/<trip_id>/`
Mark a trip as arrived and reward completion.
- **Response**: trip data with `completion_reward`.

### GET `/api/trips/history/`
List the user's trip history.

### GET `/api/trips/optimal-time/?window_hours=&current_time=&location=`
Return the optimal departure time within the next period.
- **Query Params**:
  - `window_hours` (default 2)
  - `current_time` (YYYY-MM-DD HH:MM)
  - `location` (e.g., `gangnam`)
- **Response**: `optimal_time`, `alternative_times`, `search_window`, `location`, `precision`, `analyzed_minutes`.

## Wallet

### GET `/api/wallet/`
Retrieve wallet balance and recent transactions.
- **Response**: `id`, `balance`, `currency_code`, `created_at`, `updated_at`, `recent_transactions` (last 10).

### GET `/api/wallet/transactions/`
Paginated transaction history.
- **Query Params**: `page`, `page_size`
- **Response**: list of `id`, `type`, `amount`, `description`, `created_at`, `trip`.

### GET `/api/wallet/summary/`
Summary of wallet balances and totals.
- **Response**: `current_balance`, `currency_code`, `total_earned`, `total_spent`, `transaction_count`, `recent_transactions` (5).

## Merchants

### GET `/api/merchants/list/?page=&page_size=&region=&category=&search=`
Paginated list of partner merchants with optional filters.
- **Response**: `merchants` array and `pagination` info.

### GET `/api/merchants/map/?region=&category=&limit=`
Simplified merchant markers for maps.
- **Response**: `markers` with `id`, `name`, `lat`, `lng`, `category`, `address`, plus `total_count` and `limit_applied`.

### GET `/api/merchants/filters/`
List available regions and categories.
- **Response**: `regions`, `categories`, `total_merchants`.

### GET `/api/merchants/<merchant_id>/`
Retrieve detailed info for a specific merchant.
- **Response**: `merchant` object (`id`, `name`, `category`, `subcategory`, `address`, `region`, `lat`, `lng`, `phone`, `hours`, `amenities`).

