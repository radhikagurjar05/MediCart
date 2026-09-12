# MediCart — Complete Interview Preparation Guide

> This guide is built **only** from the actual code in this repository (Flask app under `app/`, entry point `run.py`, seed script `seed.py`, templates, static assets, and the SQLite database `instance/medicart.db`). Anywhere a feature looks unfinished or missing, it is called out explicitly instead of being assumed.

---

## 1. Project Overview

| Field | Detail |
|---|---|
| **Project Name** | MediCart |
| **Tagline** | "Buy. Sell. Exchange. Within Your Campus." |
| **Type** | Full-stack web application (server-rendered, Flask + Jinja2) |
| **Purpose** | A campus-only online marketplace where verified college students (emails ending in `.edu` / `.ac.in`) can list, browse, buy, and exchange second-hand items such as textbooks, electronics, furniture, and stationery. |
| **Problem Statement** | General marketplaces (OLX, Facebook Marketplace, Instagram) mix strangers from anywhere in the city/country, which feels unsafe for students trading items like textbooks or gadgets. There is no trust boundary. MediCart solves this by **gating registration to campus email domains**, so every buyer and seller is presumptively a verified student. |
| **Target Users** | College/university students (as buyers and sellers) and a platform **Admin** who moderates content. |
| **Main Features** | Email/password + optional Google OAuth registration restricted to campus domains; product listings with multiple images, price or exchange mode; category browsing; advanced search & filters (text, category, price range, condition, exchange-only); AJAX wishlist; seller analytics dashboard with a Chart.js graph; public seller profile pages; dark mode that is saved per-user; admin dashboard for user banning, listing removal, and report review. |
| **Real-world Use Case** | A student who wants to sell an old semester's textbook posts it with photos and a price. Another student in the same campus searches "Textbooks" category, filters by price, finds it, wishlists it, and visits the seller's profile before deciding to buy. |

**Important honesty note:** There is **no in-app messaging/chat system**. The "Contact Seller" button on the product page (`app/templates/product/detail.html`, line 110) is rendered but has **no `onclick`, no `href`, and no form action** — clicking it does nothing. The seller's profile page is the only way a buyer can identify who to contact (presumably outside the app, e.g. in person or via other means). Be ready to say this plainly in an interview rather than pretending a chat feature exists.

---

## 2. Elevator Pitch

### 30-second version
"MediCart is a Flask-based marketplace built only for college students — you can only sign up with a `.edu` or `.ac.in` email. Students list items to sell or exchange, browse by category, filter by price and condition, and track how many views and wishlist saves their listings get on a seller dashboard. There's also an admin panel to ban abusive users and take down flagged listings."

### 2-minute version
"So MediCart is something I built to solve a very specific trust problem — general marketplace apps let anyone message anyone, which feels risky for something like selling your used electronics to a stranger. I restricted registration to campus email domains, so the whole pool of users is at least verified as students.

Under the hood it's a Flask app built with the Application Factory pattern — so `create_app()` in `app/__init__.py` wires everything together: SQLAlchemy for the ORM, Flask-Login for sessions, and optionally Flask-Dance for Google OAuth if credentials are configured. The code is split into Blueprints — auth, product, wishlist, profile, dashboard, and admin — and each Blueprint's routes are kept thin; the actual business logic (validation, image processing, analytics queries) sits in a separate `services/` layer, so routes just orchestrate calls.

For images, when someone uploads product photos, I use Pillow to resize them to a max of 1200px, strip them of their original format, and re-encode as WebP with a random UUID filename — that keeps storage small and avoids exposing the original filename or embedded metadata.

The seller dashboard aggregates real counts — active listings, sold count, total views, and how many times items were wishlisted — using SQLAlchemy aggregate queries, and renders that with Chart.js. I'll be upfront that the 7-day trend line on that chart is currently static demo data, not a real time-series query, because there's no `product_views` history table yet.

There's also an admin blueprint gated by an `admin_required` decorator that lets an admin ban/unban users, delete any listing, and review reports."

### 5-minute version (deep-dive / walkthrough)
"Let me walk you through this end-to-end.

**Architecture**: It's the Flask Application Factory pattern. `run.py` is the actual entry point — before it even creates the Flask app, it calls `initialize_database()`, which reads `DATABASE_URL` from the environment. If it's a MySQL URL, it opens a raw SQLAlchemy engine connection to the MySQL *server* (not a specific DB) and runs `CREATE DATABASE IF NOT EXISTS`, so the developer never has to manually create the schema. Then it calls `seed_categories()` from `seed.py`, which calls `create_app()` itself, runs `db.create_all()` to create every table from the SQLAlchemy models, seeds 8 fixed categories (Textbooks, Electronics, Furniture, etc.), and creates a default admin account (`admin@medicaps.ac.in` / `admin123`) if one doesn't already exist. Only after all that does `run.py` create the *real* app instance and call `app.run()`.

**Models**: There are six tables — `users`, `categories`, `products`, `product_images`, `wishlists`, and `reports`. `Product` has a `seller_id` FK to `users` and a `category_id` FK to `categories`. `ProductImage` belongs to a product and has an `is_primary` flag so the UI knows which photo to show first. `Wishlist` is a join table between users and products with a **unique constraint on `(user_id, product_id)`** so the same product can't be wishlisted twice by the same user — that's enforced at the database level, not just in application code.

**Auth**: Local login uses Werkzeug's `generate_password_hash` with `pbkdf2:sha256`. There's a second path via Flask-Dance for Google OAuth, but it's conditionally registered — `create_app()` only sets up the Google blueprint if `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are present in config, so the app degrades gracefully to email/password-only if you don't configure OAuth. Both paths funnel through `AuthService`, which enforces the same campus-email check (`is_valid_campus_email` in `app/utils/validators.py`) regardless of provider.

**Listings**: When a user posts a listing, `ProductService.create_product()` validates the category exists, parses the price (allowing it to be blank if the item is exchange-only), and requires *either* a price *or* the exchange flag — you can't post something with neither. Images go through `ImageService`, which resizes and converts to WebP.

**Search**: `ProductService.get_all_active_products()` builds a single SQLAlchemy query and conditionally chains `.filter()` calls based on which query params are present — category slug (via a join), free-text search using `ILIKE` on title/description, min/max price, condition, and an exchange-only toggle — then paginates with Flask-SQLAlchemy's built-in `paginate()`.

**What's intentionally left out** — because I'd rather be precise than oversell it: there's no CSRF token anywhere (there's actually a comment in `wishlist/index.html` acknowledging this was skipped), no real-time chat/contact-seller flow, no email verification step (the domain check is purely a string suffix check, it doesn't confirm the email is real), no automated tests, and the seller dashboard's 7-day chart is hardcoded sample data rather than a real query. I can talk through how I'd close each of those gaps."

---

## 3. Complete Application Flow

### 3.1 General request lifecycle (every page)

```
User's Browser
     │
     │  HTTP GET/POST (with session cookie if logged in)
     ▼
Flask WSGI app (run.py → app = create_app())
     │
     ▼
Werkzeug URL routing → matches a Blueprint + view function
     │
     ▼
Flask-Login (@login_required / @admin_required) — is the request allowed?
     │
     ▼
Route function (app/routes/*.py) — parses request.form / request.args / request.files
     │
     ▼
Service layer (app/services/*.py) — validation + business rules
     │
     ▼
SQLAlchemy ORM (app/models/*.py) — db.session queries / commits
     │
     ▼
Database (SQLite dev / MySQL prod)
     │
     ▼
Service returns (success: bool, result/message)
     │
     ▼
Route uses flash() for a message, then render_template() or redirect()
     │
     ▼
Jinja2 renders HTML using base.html + block content
     │
     ▼
Browser displays page (Lucide icons + Chart.js hydrate client-side)
```

### 3.2 Registration flow

```
GET/POST /auth/register
        │
        ▼
form fields: name, email, password
        │
        ▼
AuthService.register_user()
        │
        ├─ is_valid_campus_email(email)? ──No──▶ flash error, re-render form
        │        │Yes
        ├─ User.query.filter_by(email=email).first() exists? ──Yes──▶ flash "already registered"
        │        │No
        ├─ validate_password_strength(password) ──fails──▶ flash specific reason
        │        │passes
        ▼
new_user = User(name, email, auth_provider='local')
new_user.set_password(password)   # pbkdf2:sha256 hash
db.session.add(new_user); db.session.commit()
        │
        ▼
redirect → /auth/login  (flash "Registration successful")
```

### 3.3 Login flow (local)

```
POST /auth/login  { email, password, remember }
        │
        ▼
AuthService.login_user(email, password)
        │
        ├─ user not found ─────────────▶ "Invalid email or password."
        ├─ user.is_banned ──────────────▶ "This account has been suspended."
        ├─ user.auth_provider != 'local'▶ "Please log in using your Google account."
        ├─ check_password(password) fails ▶ "Invalid email or password."
        │
        ▼ all pass
flask_login.login_user(user, remember=remember)
        │
        ▼
Secure "next" redirect: only used if urlparse(next).netloc == '' (prevents open redirect)
        │
        ▼
Session cookie set (signed with SECRET_KEY) → user is now "logged in"
```

### 3.4 Google OAuth login flow

```
User clicks "Continue with Google" → /auth/login/google (Flask-Dance blueprint)
        │
        ▼
Google consent screen → redirects to /auth/google/callback
        │
        ▼
auth.google_login_callback()
        │
        ├─ google.authorized? No ──▶ flash "authentication failed", redirect to login
        ▼ Yes
GET https://.../oauth2/v2/userinfo  (via Flask-Dance's authorized session)
        │
        ▼
AuthService.get_or_create_oauth_user(email, name, provider='google')
        │
        ├─ is_valid_campus_email fails ──▶ reject (even Google accounts must be campus emails)
        ├─ existing banned user ─────────▶ reject
        ├─ existing user found ───────────▶ log them in as-is
        ├─ no existing user ──────────────▶ create User(auth_provider='google', no password)
        ▼
login_user(user); optionally copy Google profile picture to avatar_url if none set
```

### 3.5 Create listing flow

```
GET /p/create (login_required)
        │
        ▼
form: title, category_id, condition, description, price, is_exchangeable,
      exchange_preferences, images[] (multipart/form-data, up to 5 files, client-side checked)
        │
        ▼ POST
ProductService.create_product(seller_id, form_data, files)
        │
        ├─ category exists? No ──▶ "Invalid category selected."
        ├─ parse price (blank → None; non-numeric → error; negative → error)
        ├─ price is None AND not is_exchangeable? ──▶ "must provide price or mark exchangeable"
        │
        ▼
Product row created, db.session.flush() to get product.id before commit
        │
        ▼
for each uploaded file:
    ImageService.process_and_save_product_image(file)
        │
        ├─ validate extension (png/jpg/jpeg/webp)
        ├─ Pillow: open → convert RGBA/P to RGB → thumbnail to max 1200x1200
        ├─ save as WEBP, quality=85, filename = uuid4().hex + ".webp"
        ▼
    ProductImage row created; first successfully processed image becomes is_primary=True
        │
        ▼
db.session.commit()
        │
        ▼
redirect → /p/<product_id>  (flash "Your listing has been published!")
```

### 3.6 Browse / search / filter flow (Explore page)

```
GET /explore?q=..&category=..&min_price=..&max_price=..&condition=..&exchange=..&page=N
        │
        ▼
main.explore() view reads request.args, converts min/max price strings to float or None
        │
        ▼
ProductService.get_all_active_products(...)
        │
        ▼
base query: Product.query.filter_by(status='active')
   → optionally .join(Category).filter(Category.slug == cat_slug)
   → optionally .filter(title ILIKE %q% OR description ILIKE %q%)
   → optionally .filter(price >= min_price)
   → optionally .filter(price <= max_price)
   → optionally .filter(condition == condition)
   → optionally .filter(is_exchangeable == True)
        │
        ▼
.order_by(created_at desc).paginate(page, per_page=12, error_out=False)
        │
        ▼
render explore.html with Flask-SQLAlchemy Pagination object
   (template calls products.items, products.total, products.has_next/prev, products.iter_pages)
```

### 3.7 Wishlist toggle (AJAX, no page reload)

```
Product detail page → click heart button → toggleWishlist(productId, btnElement) [JS in detail.html]
        │
        ▼
fetch POST /wishlist/toggle/<product_id>   (login_required)
        │
        ▼
wishlist.toggle() route:
   existing = Wishlist.query.filter_by(user_id, product_id).first()
        │
        ├─ exists → db.session.delete(existing) → {"status": "removed"}
        ├─ not exists → db.session.add(Wishlist(...)) → {"status": "added"}
        ▼
JSON response
        │
        ▼
JS updates the heart icon fill + button text + shows a toast — NO full page reload
```

### 3.8 Seller dashboard analytics flow

```
GET /dashboard (login_required)
        │
        ▼
AnalyticsService.get_seller_stats(current_user.id)
        │
        ├─ active_listings_count = Product.query.filter_by(seller_id, status='active').count()
        ├─ sold_listings_count   = Product.query.filter(seller_id, status IN ('sold','exchanged')).count()
        ├─ total_views           = SUM(Product.views) WHERE seller_id = X   (SQL aggregate)
        ├─ wishlist_saves        = COUNT(Wishlist.id) JOIN Product WHERE seller_id = X
        ▼
stats dict returned → 4 stat cards rendered
        │
        ▼
Product.query.filter_by(seller_id).order_by(created_at desc).all() → listings table
        │
        ▼
chart_data = HARD-CODED dict {labels: [Mon..Sun], data: [12,19,15,25,22,30,28]}   ⚠ NOT REAL DATA
        │
        ▼
Jinja passes chart_data|tojson to inline <script>; Chart.js renders a line chart,
watches <html data-theme> via MutationObserver to re-color the chart on dark-mode toggle
```

### 3.9 Admin moderation flow

```
Any request to /admin/*
        │
        ▼
admin_bp.before_request → @login_required then @admin_required
        │
        ├─ not authenticated or not current_user.is_admin ──▶ flash + redirect to main.index
        ▼ passes
/admin/               → dashboard stat cards (user/listing/report counts)
/admin/users          → list all users
/admin/users/<id>/toggle-ban  → flips is_banned (blocked from banning self)
/admin/listings       → list all products, admin can force-delete any
/admin/reports        → list all Report rows, admin can "Dismiss" (status='dismissed')
                          or "Delete Listing" (deletes the reported Product outright)
```
**Gap to know:** there is no route where a normal user *creates* a `Report` — the reporting UI/endpoint for end users does not exist, even though the `Report` model and the entire admin review screen for reports are fully built. Also, deleting a reported listing does not update the report row itself (no cascading update/delete), so a stale report referencing a deleted product could remain in the table.

---

## 4. System Architecture

### 4.1 Layer-by-layer

| Layer | Technology | Details |
|---|---|---|
| **Frontend** | Server-rendered Jinja2 templates + vanilla JS + CSS variables | No SPA framework (no React/Vue). All pages are rendered on the server; small islands of interactivity (wishlist toggle, dark mode, form previews, chart) are done with plain `fetch()` and DOM APIs in `app/static/js/app.js` and inline `<script>` blocks per template. |
| **Backend** | Python 3 + Flask 3.1.1 | Application Factory pattern (`create_app()`), organized into 7 Blueprints. |
| **Database** | SQLite (dev, file `instance/medicart.db`) / MySQL via PyMySQL (prod) | Access exclusively through Flask-SQLAlchemy's ORM — no raw SQL in the routes/services (one raw `CREATE DATABASE IF NOT EXISTS` statement exists in `run.py` for bootstrap only). |
| **External APIs** | Google OAuth 2.0 (via Flask-Dance) | Optional — only wired up if `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are set. Fetches `https://www.googleapis.com/oauth2/v2/userinfo`. |
| **Authentication** | Flask-Login (session/cookie based) | No JWT anywhere in the codebase. |
| **Storage** | Local filesystem under `app/static/uploads/{products,avatars}/` | Not object storage (e.g. S3) — images live on the same disk as the app. |
| **Deployment** | Not containerized in this repo (no Dockerfile) | Runs via `python run.py` using Flask's built-in dev server (`debug=True`), which is **not** production-grade (single-threaded, not hardened). `ProductionConfig` exists in `config.py` but there's no WSGI server (gunicorn/uWSGI) configuration present. |

### 4.2 ASCII architecture diagram

```
                                ┌─────────────────────────────┐
                                │         Browser              │
                                │  HTML + CSS + Vanilla JS      │
                                │  (Lucide Icons, Chart.js CDN) │
                                └───────────────┬──────────────┘
                                                │ HTTP(S)
                                                ▼
                        ┌───────────────────────────────────────────┐
                        │            Flask Application               │
                        │            (run.py → create_app())         │
                        │                                             │
                        │   ┌───────────────────────────────────┐    │
                        │   │  Blueprints (Routes / Controllers)  │    │
                        │   │  main | auth | product | wishlist   │    │
                        │   │  profile | dashboard | admin        │    │
                        │   └───────────────┬─────────────────────┘   │
                        │                   ▼                         │
                        │   ┌───────────────────────────────────┐    │
                        │   │      Services (Business Logic)      │    │
                        │   │  AuthService | ProductService       │    │
                        │   │  ImageService | UserService         │    │
                        │   │  AnalyticsService                   │    │
                        │   └───────────────┬─────────────────────┘   │
                        │                   ▼                         │
                        │   ┌───────────────────────────────────┐    │
                        │   │   Models (SQLAlchemy ORM)            │    │
                        │   │  User | Category | Product           │    │
                        │   │  ProductImage | Wishlist | Report     │    │
                        │   └───────────────┬─────────────────────┘   │
                        │                   │                         │
                        │   Flask-Login (session cookie auth)         │
                        │   Flask-Dance (Google OAuth, optional)       │
                        └───────────────────┬─────────────────────────┘
                                            ▼
                       ┌───────────────────────────────────────┐
                       │     Database (SQLite dev / MySQL prod)  │
                       └───────────────────────────────────────┘

                       ┌───────────────────────────────────────┐
                       │   Local Filesystem: app/static/uploads/ │
                       │   (product images & avatars, WebP)      │
                       └───────────────────────────────────────┘

                       ┌───────────────────────────────────────┐
                       │   External: Google OAuth 2.0 (optional) │
                       └───────────────────────────────────────┘
```

---

## 5. Folder Structure

```
MediCart/
├── run.py                    # Entry point. Bootstraps DB, then starts the Flask dev server.
├── seed.py                   # Idempotent seeding: 8 categories + 1 default admin user.
├── requirements.txt          # Pinned dependency versions.
├── .env / .env.example       # Environment config (SECRET_KEY, DATABASE_URL, OAuth creds, upload limits).
├── instance/
│   └── medicart.db         # SQLite database file (Flask's default "instance folder" convention).
├── app/
│   ├── __init__.py           # create_app() — the Application Factory. Registers extensions & blueprints.
│   ├── config.py             # Config classes: Development / Production / Testing, chosen via FLASK_ENV.
│   ├── extensions.py         # Shared, uninitialized extension instances: db (SQLAlchemy), login_manager.
│   ├── models/                # SQLAlchemy ORM models — one file per table, plus __init__ exporting all.
│   │   ├── user.py           # User: auth fields, role, ban flag, dark mode pref, helper properties.
│   │   ├── category.py       # Category: fixed marketplace categories.
│   │   ├── product.py        # Product + ProductImage: the core listing entity.
│   │   ├── wishlist.py       # Wishlist: User<->Product join table with a unique constraint.
│   │   └── report.py         # Report: user-flagged content for admin review.
│   ├── routes/                 # Blueprints — thin controllers, one file per feature area.
│   │   ├── main.py           # Landing page, Explore/search, About, 404 handler.
│   │   ├── auth.py           # Register, login, logout, Google OAuth callback.
│   │   ├── product.py        # Create/detail/edit/status-update/delete for listings.
│   │   ├── wishlist.py       # Wishlist page + AJAX toggle endpoint.
│   │   ├── profile.py        # Public profile view, edit profile, settings, delete account.
│   │   ├── dashboard.py      # Seller analytics dashboard.
│   │   └── admin.py          # Admin-only: users, listings, reports moderation.
│   ├── services/               # Business logic layer, decoupled from Flask request/response objects.
│   │   ├── auth_service.py   # Registration/login/OAuth logic + campus-email + password rules.
│   │   ├── product_service.py# CRUD + filtered search/pagination for listings.
│   │   ├── image_service.py  # Pillow-based image validation, resize, WebP conversion, deletion.
│   │   ├── user_service.py   # Profile/avatar update, settings (dark mode/password), account deletion.
│   │   └── analytics_service.py # Seller dashboard aggregate stats (SQL COUNT/SUM queries).
│   ├── utils/
│   │   ├── decorators.py     # @admin_required — role-based route guard.
│   │   └── validators.py     # is_valid_campus_email(), validate_password_strength().
│   ├── templates/               # Jinja2 templates, organized to mirror the blueprints.
│   │   ├── base.html         # Shared layout: navbar, flash messages, footer, global CSS/JS includes.
│   │   ├── main/, auth/, product/, profile/, dashboard/, admin/, wishlist/, components/
│   └── static/
│       ├── css/               # variables.css (design tokens + dark theme), style.css, components.css, responsive.css
│       ├── js/app.js         # Theme toggle, mobile nav, flash auto-dismiss, scroll animations, toast utility
│       ├── images/            # Static assets (e.g. placeholder product image)
│       └── uploads/           # User-generated content: products/ and avatars/ subfolders (gitignored, .gitkeep only)
└── venv/                      # Local Python virtual environment (not part of the app's logic)
```

**How it connects together:** `run.py` creates the app once at process start. Inside `create_app()`, the extensions (`db`, `login_manager`) are bound to the app instance, blueprints are imported and registered, and `db.create_all()` runs so every model in `app/models/` gets a table. Every route module imports only the service(s) it needs — routes never talk to `db.session` directly for anything beyond trivial reads (there are a couple of minor exceptions, e.g. incrementing `product.views` directly in `product.py`, and the wishlist toggle route touching `db.session` directly instead of going through a service). Templates extend `base.html` and are grouped into folders that match blueprint names, which makes it easy to find "the template for route X."

---

## 6. Technology Stack

| Technology | What it is | Why used here | Advantages | Alternatives | Why this project chose it |
|---|---|---|---|---|---|
| **Flask 3.1.1** | Lightweight Python micro web framework | Core backend framework for routing, request handling, templating | Minimal boilerplate, very flexible, huge ecosystem, easy to reason about for a solo/small project | Django, FastAPI | Flask's un-opinionated nature fits a moderate-sized CRUD app where the team wanted full control over structure (Blueprints + custom service layer) without Django's built-in admin/ORM conventions getting in the way |
| **Flask-SQLAlchemy 3.1.1** | ORM integration for Flask | Defines models as Python classes, maps to DB tables, gives query builder | No raw SQL needed for 95% of operations, database-agnostic (SQLite in dev, MySQL in prod with zero code changes) | Raw SQL + a query builder, Peewee, Tortoise ORM | SQLAlchemy is the de-facto standard for Flask; lets the same models run against SQLite locally and MySQL in production just by changing `DATABASE_URL` |
| **Flask-Login 0.6.3** | Session-based user authentication helper | Manages `current_user`, `login_user()`, `logout_user()`, `@login_required` | Simple cookie-session model, no token management needed, integrates with Jinja via `current_user` | JWT (PyJWT + custom middleware), Flask-Security, Authlib | The app is a classic server-rendered site (not a decoupled API+SPA), so stateful cookie sessions are simpler and sufficient — no need for the complexity of token refresh/rotation that JWT would add |
| **Flask-Dance[sqla] 7.1.0** | OAuth client integration for Flask | Handles the Google OAuth 2.0 handshake (authorize URL, callback, token storage) | Removes the need to hand-roll OAuth2 redirect/callback/state validation | Authlib, manual `requests-oauthlib` | Chosen for its Flask-native blueprint-style integration — `make_google_blueprint()` plugs directly into the same Blueprint architecture the rest of the app uses |
| **python-dotenv 1.1.0** | Loads `.env` file into environment variables | Keeps secrets (SECRET_KEY, DB credentials, OAuth secrets) out of source code | Simple, works everywhere, no extra service required | direnv, OS-level env vars, cloud secret managers | Simplest option for local dev and a small deployment; `.env` is gitignored |
| **Pillow (PIL) 11.2.1** | Python imaging library | Resizes, converts, and re-encodes uploaded images | Pure-Python-friendly, handles format conversion (PNG/JPEG → WebP), strips metadata by re-encoding | imageio, Wand (ImageMagick binding), cloud image APIs (Cloudinary) | Free, no external service dependency, good enough for on-the-fly resize/convert without needing a media pipeline |
| **PyMySQL 1.1.1** | Pure-Python MySQL driver | Lets SQLAlchemy talk to MySQL in production via `mysql+pymysql://` | No C-extension compile step (unlike `mysqlclient`), easier to install cross-platform | mysqlclient, mysql-connector-python | Simpler installs, especially in constrained/dev environments |
| **cryptography 44.0.3** | Low-level crypto primitives | Transitive dependency (mainly used by Flask-Dance/OAuthlib for token handling) | Well-audited crypto library | pyOpenSSL alone | Pulled in indirectly, not something hand-invoked in this codebase's own code |
| **Werkzeug security (bundled with Flask)** | Password hashing utilities | `generate_password_hash` / `check_password_hash` with `pbkdf2:sha256` | Battle-tested, salted hashing built into the framework already in use — no new dependency | bcrypt, argon2-cffi | Zero extra dependency since Werkzeug ships with Flask; PBKDF2-SHA256 is a solid, standards-based choice (though bcrypt/argon2 are considered stronger against GPU cracking today) |
| **Jinja2 (bundled with Flask)** | Server-side templating engine | Renders all HTML with template inheritance (`base.html`) | Auto-escapes output by default (XSS protection), macros/blocks for reuse | Server-rendered React (Next.js), Mako | Comes for free with Flask; fits the server-rendered architecture |
| **Chart.js (via CDN)** | JS charting library | Renders the "Listing Views" line chart on the seller dashboard | Lightweight, no build step needed, easy canvas-based rendering | D3.js, ApexCharts | Simplest way to get an attractive chart without a JS bundler/build pipeline |
| **Lucide Icons (via CDN)** | Icon library | All the small UI icons (`<i data-lucide="...">`) | Modern, consistent icon set, tree-shakes via `lucide.createIcons()` | Font Awesome, Heroicons | Clean, modern look with a single script tag — no icon font subset build needed |
| **SQLite (dev)** | Embedded file-based database | Zero-config local development database | No server process to manage, file lives in `instance/` | PostgreSQL locally via Docker | Fastest way to iterate locally without installing a DB server |
| **MySQL (prod, via `DATABASE_URL`)** | Relational database server | Intended production datastore | Mature, widely hosted, well understood ops story | PostgreSQL | README specifically calls out MySQL as the production target, with auto-creation logic in `run.py` |

---

## 7. Database Design

### 7.1 Tables (from live inspection of `instance/medicart.db`, matching the SQLAlchemy models)

**`users`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(100) | NOT NULL |
| email | VARCHAR(150) | NOT NULL, UNIQUE, indexed |
| password_hash | VARCHAR(256) | NULLABLE (null for OAuth-only users) |
| avatar_url | VARCHAR(300) | NULLABLE |
| bio | TEXT | NULLABLE |
| phone | VARCHAR(20) | NULLABLE |
| role | VARCHAR(20) | NOT NULL, default `'student'` |
| is_active | BOOLEAN | NOT NULL, default True |
| is_banned | BOOLEAN | NOT NULL, default False |
| auth_provider | VARCHAR(20) | NOT NULL, default `'local'` |
| dark_mode | BOOLEAN | NOT NULL, default False |
| created_at | DATETIME | default now (UTC) |
| updated_at | DATETIME | default/onupdate now (UTC) |

**`categories`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(50) | NOT NULL, UNIQUE |
| slug | VARCHAR(50) | NOT NULL, UNIQUE, indexed |
| icon | VARCHAR(50) | NULLABLE (Lucide icon name) |
| description | VARCHAR(200) | NULLABLE |

**`products`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| seller_id | INTEGER | NOT NULL, FK → `users.id` |
| category_id | INTEGER | NOT NULL, FK → `categories.id` |
| title | VARCHAR(100) | NOT NULL |
| description | TEXT | NOT NULL |
| price | NUMERIC(10,2) | NULLABLE (null = exchange-only) |
| is_exchangeable | BOOLEAN | NOT NULL, default False |
| exchange_preferences | VARCHAR(200) | NULLABLE |
| condition | VARCHAR(20) | NOT NULL — one of `new / like_new / good / fair / poor` (enforced only in application code, not a DB CHECK constraint) |
| status | VARCHAR(20) | NOT NULL, default `'active'` — one of `active / sold / exchanged / delisted` (also app-level only) |
| views | INTEGER | default 0 |
| created_at / updated_at | DATETIME | default/onupdate now (UTC) |

**`product_images`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| product_id | INTEGER | NOT NULL, FK → `products.id` |
| image_url | VARCHAR(300) | NOT NULL |
| is_primary | BOOLEAN | default False |
| created_at | DATETIME | default now (UTC) |

**`wishlists`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | NOT NULL, FK → `users.id` |
| product_id | INTEGER | NOT NULL, FK → `products.id` |
| created_at | DATETIME | default now (UTC) |
| — | — | **UNIQUE constraint** `uq_user_product_wishlist` on `(user_id, product_id)` |

**`reports`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK |
| reporter_id | INTEGER | NOT NULL, FK → `users.id` |
| product_id | INTEGER | NOT NULL, FK → `products.id` |
| reason | TEXT | NOT NULL |
| status | VARCHAR(20) | default `'pending'` — `pending / reviewed / dismissed` |
| admin_notes | TEXT | NULLABLE |
| created_at | DATETIME | default now (UTC) |
| reviewed_at | DATETIME | NULLABLE |

### 7.2 Entity-Relationship Diagram (ASCII)

```
┌────────────┐        1     M      ┌─────────────┐
│  categories │ ─────────────────▶ │   products   │
└────────────┘                     └──────┬──────┘
                                           │ 1
                                           │
                     ┌─────────────────────┼───────────────────────┐
                     │ M                   │ M                     │ M
              ┌──────▼───────┐     ┌───────▼────────┐      ┌───────▼──────┐
              │ product_images│    │   wishlists     │      │   reports     │
              └───────────────┘    └────────┬────────┘      └───────┬──────┘
                                            │ M                     │ M
                                            │                       │
                                    ┌───────▼───────────────────────▼──────┐
                                    │                users                  │
                                    └────────────────────────────────────────┘
```

- `users` (1) —— (M) `products`  via `products.seller_id`
- `categories` (1) —— (M) `products` via `products.category_id`
- `products` (1) —— (M) `product_images` via `product_images.product_id`
- `users` (M) —— (M) `products` through `wishlists` (a proper join table with its own PK and a uniqueness guard)
- `users` (1) —— (M) `reports` as reporter, `products` (1) —— (M) `reports` as the flagged item

### 7.3 Why the schema is designed this way

- **Nullable `price`** models "exchange-only" listings without needing a separate table or a magic sentinel value (like `-1`); the app enforces "price OR exchange" in `ProductService`, keeping the schema simple while the invariant lives in code.
- **Separate `ProductImage` table** instead of a comma-separated string column allows multiple images per product, ordering, and an `is_primary` flag — a normalized one-to-many relationship instead of a denormalized blob.
- **`Wishlist` as its own table with a composite unique constraint** is the standard way to model a many-to-many relationship with metadata (here, `created_at`) — cleaner than an in-memory list column, and the DB itself guarantees "no duplicate wishlist entries," which is stronger than an application-level check (which could race under concurrent requests).
- **String-based `status`/`condition`/`role` fields** rather than a separate lookup table trade a bit of DB-level enforcement for simplicity — acceptable for a project of this size, but a real weakness at scale (see Section 18/20).
- **UTC timestamps with `default`/`onupdate` lambdas** ensure `created_at` and `updated_at` are always set server-side, not client-supplied.
- **No `ON DELETE CASCADE`** is configured on any foreign key in the SQLAlchemy models (only `cascade="all, delete-orphan"` at the ORM relationship level for `Product.images` and `User.wishlisted_items`/`Product.wishlisted_by`). That means, for example, deleting a `Product` through the ORM correctly cascades to its `ProductImage` and `Wishlist` rows (because those relationships declare `cascade="all, delete-orphan"`), but **`Report` has no cascade configured**, so deleting a reported product can leave an orphaned `Report` row pointing at a non-existent product — a real design gap worth naming if asked.

### 7.4 Indexes

- `users.email` — indexed (also unique) — supports fast login lookups.
- `categories.slug` — indexed (also unique) — supports fast category-filtered queries.
- All primary keys are auto-indexed by SQLite/MySQL.
- No composite/secondary indexes on `products.status`, `products.seller_id`, or `products.category_id` — these are exactly the columns used in every dashboard/explore query, so at scale these would need indexes (see Section 17).

---

## 8. API Documentation

All endpoints are traditional Flask **HTML-form + redirect** endpoints (server-rendered), except the wishlist toggle which is a JSON AJAX endpoint. There is no separate `/api/` namespace or REST API layer.

### 8.1 Auth (`/auth`, blueprint: `auth_bp`)

| Endpoint | Method | Purpose | Request | Response | Validation | Possible Errors |
|---|---|---|---|---|---|---|
| `/auth/register` | GET, POST | Show/handle registration | form: `name`, `email`, `password` | Redirect to login on success; re-render form with flash on failure | Campus email domain, uniqueness, password ≥8 chars with letter+number | "already registered", invalid domain, weak password |
| `/auth/login` | GET, POST | Show/handle login | form: `email`, `password`, `remember` | Sets session cookie, redirects to `next` or home | User exists, not banned, correct provider, correct password | "Invalid email or password", "account suspended", "log in using X account" |
| `/auth/logout` | GET | Ends session | — (login required) | Redirect to home | — | — |
| `/auth/google/callback` | GET | OAuth callback after Google consent | Google-provided auth code (handled by Flask-Dance) | Login + redirect | `google.authorized`, valid campus email, not banned | "authentication failed", "Failed to fetch user info", generic exception message |

### 8.2 Main (`main_bp`, no prefix)

| Endpoint | Method | Purpose | Request | Response | Notes |
|---|---|---|---|---|---|
| `/` | GET | Landing page | — | Renders categories + 8 most recent active products | |
| `/explore` | GET | Search/filter/browse | query params: `q, category, condition, exchange, min_price, max_price, page` | Paginated product grid | Price strings parsed defensively (empty string → None) |
| `/about` | GET | Static about page | — | — | — |
| 404 handler | — | Custom not-found page | — | `main/404.html`, HTTP 404 | Registered via `@main_bp.app_errorhandler(404)` |

### 8.3 Product (`/p`, `product_bp`)

| Endpoint | Method | Purpose | Request | Response | Validation | Errors |
|---|---|---|---|---|---|---|
| `/p/create` | GET, POST | Create listing | multipart form: title, category_id, condition, description, price, is_exchangeable, exchange_preferences, images[] | Redirect to detail page | login required; category must exist; price/exchange rule; image extension whitelist | "Invalid category", "Price cannot be negative", "must provide a price or mark exchangeable" |
| `/p/<id>` | GET | View listing detail | path param `product_id` | Renders detail page; **side effect: increments `views` by 1 on every load, including the owner's own views** | Product must exist (else redirect with flash) | "Listing not found" |
| `/p/<id>/edit` | GET, POST | Edit listing | form (same fields as create, minus images) | Redirect to detail | Must be owner or admin | "You do not have permission to edit this listing" |
| `/p/<id>/status` | POST | Change status (e.g., mark sold) | form: `status` | Redirect to detail | Status must be in whitelist; must be owner or admin | "Invalid status", permission denied |
| `/p/<id>/delete` | POST | Delete listing + its images | — | Redirect to home (success) or detail (failure) | Must be owner or admin | permission denied |

### 8.4 Wishlist (`/wishlist`, `wishlist_bp`)

| Endpoint | Method | Purpose | Request | Response | Notes |
|---|---|---|---|---|---|
| `/wishlist/` | GET | View my wishlist | login required | HTML page listing wishlisted products | |
| `/wishlist/toggle/<product_id>` | POST | **AJAX** add/remove from wishlist | login required, `product_id` in path | `{"status": "added"/"removed"/"error", "message": "..."}` as JSON | Uses `get_or_404`; wraps in try/except with rollback on failure, returns HTTP 500 on exception |

### 8.5 Profile (`/profile`, `profile_bp`)

| Endpoint | Method | Purpose | Request | Response | Notes |
|---|---|---|---|---|---|
| `/profile/<user_id>` | GET | Public profile | path param | Active listings + total sold count for that user | Publicly viewable, no login required |
| `/profile/edit` | GET, POST | Edit name/bio/phone/avatar | multipart form | Redirect to own profile | login required; avatar cropped to square 300×300 WebP |
| `/profile/settings` | GET, POST | Dark mode + change password | form: `dark_mode`, `current_password`, `new_password`, `confirm_password` | Redirect to settings page | Current password must match; new passwords must match; new password ≥8 chars; skipped entirely for OAuth users |
| `/profile/delete` | POST | Delete own account | — | Logs out + redirect home | login required; hard-deletes the `User` row (cascades to wishlist entries via ORM relationship) |

### 8.6 Dashboard (`/dashboard`, `dashboard_bp`)

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/dashboard/` | GET | Seller analytics | Stat cards (active/sold/views/wishlist-saves) computed live from DB + a **static/mocked** 7-day chart dataset |

### 8.7 Admin (`/admin`, `admin_bp`, all routes gated by `admin_required`)

| Endpoint | Method | Purpose | Notes |
|---|---|---|---|
| `/admin/` | GET | Dashboard: user/listing/report counts + 5 most recent signups | |
| `/admin/users` | GET | List all users | |
| `/admin/users/<id>/toggle-ban` | POST | Ban/unban a user | Cannot ban yourself |
| `/admin/listings` | GET | List all products | |
| `/admin/listings/<id>/delete` | POST | Force-delete any listing | No confirmation server-side (client-side `confirm()` only) |
| `/admin/reports` | GET | List all reports | |
| `/admin/reports/<id>/dismiss` | POST | Mark report as `dismissed` | No route to mark `reviewed` with `admin_notes` despite the model supporting it |

### 8.8 Internal request flow for a typical POST endpoint

```
Browser form submit (POST, multipart or urlencoded)
      │
      ▼
Flask routes to view function (checks @login_required / @admin_required first)
      │
      ▼
view function reads request.form / request.files (NOT validated against a schema library —
   no marshmallow / pydantic / WTForms; validation is hand-written in the service layer)
      │
      ▼
Service method called with plain Python values
      │
      ▼
Service does business validation → returns (bool success, str message_or_object)
      │
      ▼
view function branches on success: flash() + redirect(), or flash() + re-render same form
```

---

## 9. Authentication & Authorization

| Aspect | How it works in this codebase |
|---|---|
| **Login Flow** | Email/password checked against a PBKDF2-SHA256 hash (`werkzeug.security`), or Google OAuth via Flask-Dance. Both create/verify a `User` row and call Flask-Login's `login_user()`. |
| **Password Storage** | `generate_password_hash(password, method='pbkdf2:sha256')` stored in `users.password_hash`. OAuth-only users have `password_hash = NULL`. Passwords are **never** stored or logged in plaintext. |
| **JWT** | **Not used anywhere in this project.** There is no token issuance, no `Authorization: Bearer` header handling. |
| **Sessions** | Flask-Login manages a server-signed session using Flask's default client-side session cookie (signed with `app.config['SECRET_KEY']`, itself read from `SECRET_KEY` in `.env`, falling back to a hardcoded dev key `'dev-fallback-secret-key'` if unset — a real risk if deployed without setting `SECRET_KEY`). `remember=True` extends the cookie's lifetime via Flask-Login's "remember me" cookie. |
| **Cookies** | Session cookie is HttpOnly by default (Flask sets `HttpOnly` on the session cookie) — cannot be read by JavaScript, which mitigates XSS-based session theft. There is **no explicit `Secure` or `SameSite` cookie configuration** in `config.py`, so on plain HTTP the cookie could be sent unencrypted, and cross-site request behavior relies on Flask's defaults. |
| **Roles** | Two roles: `'student'` (default) and `'admin'`, stored as a plain string column on `User`. `User.is_admin` / `User.is_student` are convenience properties. There is no granular permission system (no roles-and-permissions table) — it's a simple binary admin/non-admin check. |
| **Authorization enforcement** | `@login_required` (Flask-Login) guards any route needing a logged-in user. `@admin_required` (custom decorator in `app/utils/decorators.py`) checks `current_user.is_authenticated and current_user.is_admin`; if not, flashes an error and redirects to the homepage — it does **not** return an HTTP 403, it silently redirects. Ownership checks (e.g., "can this user edit this product?") are done manually inside each service method by comparing `product.seller_id == user_id` (or allowing `is_admin` to override). |
| **Campus email gating** | Both local registration and OAuth registration are funneled through `is_valid_campus_email()`, which only checks that the email **string** ends in `.edu` or `.ac.in` (or is in a hardcoded allowed-domain list). **This is not real identity verification** — nothing confirms the email address is real, owned by the registrant, or actually issued by a university (anyone can register `fake@anything.edu` if they type it, since there's no verification email sent). |
| **Ban enforcement** | `User.is_banned` is checked at login time (both local and OAuth) — a banned user cannot log in even with correct credentials. However, an **already-logged-in** banned user's *existing session* is not force-invalidated at the moment of banning; they'd only be blocked the next time they try to log in fresh. |
| **Security best practices explicitly present** (per README + code) | PBKDF2-SHA256 hashing; secure "next" redirect validation (`urlparse(next_page).netloc == ''` prevents open-redirect attacks); file extension whitelist on uploads; image re-encoding via Pillow (strips embedded EXIF/metadata and prevents disguised-executable uploads); route-level decorators for auth/admin gating. |

**What's genuinely missing (say this clearly in interviews, don't oversell):**
- **No CSRF protection.** There is no Flask-WTF/CSRF token anywhere; forms are plain HTML `<form>` tags with no hidden token field. A template comment in `app/templates/wishlist/index.html` even says *"Assuming we might need CSRF token later, but skipping for now"* — an explicit, in-code acknowledgment of this gap.
- **No email verification** step for registration.
- **No rate limiting** on login/register (no Flask-Limiter or similar) — vulnerable to brute-force credential stuffing.
- **No password reset / "forgot password"** flow.
- **No 2FA.**

---

## 10. Feature Breakdown

### 10.1 Campus-restricted Registration & Login
- **Purpose:** Ensure only students with a plausible campus email can use the marketplace.
- **Internal working:** `is_valid_campus_email()` checks the email suffix; `AuthService` wraps this check for both local and OAuth signup paths.
- **Files:** `app/utils/validators.py`, `app/services/auth_service.py`, `app/routes/auth.py`, `app/templates/auth/*.html`.
- **Execution flow:** See Section 3.2/3.3/3.4.

### 10.2 Product Listings (Create/Edit/Delete/Status)
- **Purpose:** Let students post items for sale or exchange, and manage their own listings.
- **Internal working:** `ProductService` centralizes validation (category existence, price/exchange rule) and delegates image handling to `ImageService`. Ownership checks (`seller_id == user_id or is_admin`) gate edit/delete/status changes.
- **Files:** `app/models/product.py`, `app/services/product_service.py`, `app/routes/product.py`, `app/templates/product/*.html`.
- **Execution flow:** See Section 3.5.

### 10.3 Image Processing Pipeline
- **Purpose:** Normalize arbitrary user-uploaded images into small, safe, web-optimized files.
- **Internal working:** Pillow opens the file, converts palette/alpha images to RGB, downsizes to fit within 1200×1200 (`img.thumbnail`, preserves aspect ratio), assigns a random UUID filename, and saves as WebP at quality 85. Avatars go through a similar but separate path in `UserService` that additionally **center-crops to a square** before resizing to a fixed 300×300.
- **Files:** `app/services/image_service.py`, `app/services/user_service.py`.
- **Why separate logic for avatars instead of reusing `ImageService`:** the code has an explicit comment noting `ImageService` "currently hardcodes the 'products' path," so avatar processing was hand-rolled inline in `UserService` rather than generalizing `ImageService` — a known duplication, good "what would you refactor" talking point.

### 10.4 Advanced Search & Filtering (Explore Page)
- **Purpose:** Let buyers narrow down listings by free text, category, price range, condition, and exchange availability, with pagination.
- **Internal working:** A single SQLAlchemy query is progressively narrowed by conditionally chained `.filter()` calls, only applying a filter if the corresponding query parameter was actually supplied.
- **Files:** `app/services/product_service.py` (`get_all_active_products`), `app/routes/main.py` (`explore`), `app/templates/main/explore.html`.

### 10.5 Wishlist (AJAX Favorites)
- **Purpose:** Let logged-in users save products for later without navigating away or reloading the page.
- **Internal working:** A single toggle endpoint checks for an existing `Wishlist` row and either deletes or inserts it, returning JSON; the frontend JS updates the button's icon/text/color in place and shows a toast notification.
- **Files:** `app/models/wishlist.py`, `app/routes/wishlist.py`, inline JS in `app/templates/product/detail.html`.
- **DB-level guarantee:** the unique constraint on `(user_id, product_id)` means even a double-submitted request can't create duplicate wishlist rows.

### 10.6 Seller Dashboard & Analytics
- **Purpose:** Give sellers visibility into how their listings are performing.
- **Internal working:** `AnalyticsService.get_seller_stats()` runs four separate aggregate queries (COUNT/SUM) scoped to `seller_id`. The listings table below it queries all of the seller's products directly in the route. The line chart is rendered client-side with Chart.js, reading a dict passed from the route via Jinja's `|tojson` filter.
- **Files:** `app/services/analytics_service.py`, `app/routes/dashboard.py`, `app/templates/dashboard/index.html`.
- **Known limitation:** the "Last 7 Days" chart data is a **hardcoded static list** (`[12, 19, 15, 25, 22, 30, 28]`), not a real per-day time-series query — there is no table tracking daily view counts, only a lifetime `views` counter on `Product`.

### 10.7 Public Seller Profiles
- **Purpose:** Let a buyer see a seller's other active listings and reputation signal (member-since date, total items sold) before deciding to engage.
- **Internal working:** Queries `Product` filtered by `seller_id` and `status` (active vs sold), no authentication required to view.
- **Files:** `app/routes/profile.py` (`view`), `app/templates/profile/view.html`.

### 10.8 Dark Mode
- **Purpose:** User-controlled light/dark theme that persists across devices (not just the browser).
- **Internal working:** Preference is stored in `users.dark_mode` in the DB (persisted server-side) **and** mirrored to `localStorage` client-side for instant toggling without a page reload. `base.html`'s root `<html data-theme="...">` attribute is set server-side from `current_user.dark_mode` on first load, then `app.js`/inline scripts flip it client-side and sync `localStorage`. All colors are CSS custom properties (`variables.css`), redefined under the `[data-theme="dark"]` selector.
- **Files:** `app/static/css/variables.css`, `app/static/js/app.js`, `app/templates/base.html`, `app/templates/profile/settings.html`, `app/services/user_service.py` (`update_settings`).
- **Subtlety:** on first load, an **anonymous** visitor's theme comes from `prefers-color-scheme` / localStorage (client-only), since there's no `current_user.dark_mode` to read; only logged-in users get the DB-backed value baked into the initial server-rendered HTML.

### 10.9 Admin Moderation
- **Purpose:** Give a platform operator tools to keep the marketplace safe — ban abusive users, remove inappropriate listings, and review flagged content.
- **Internal working:** `admin_bp.before_request` stacks `@login_required` then `@admin_required` so **every** route in the blueprint is protected without repeating the decorator on each view function. Admin actions are simple, direct SQLAlchemy field flips/deletes (no separate `AdminService` — this is the one blueprint that talks to the DB directly from the route layer).
- **Files:** `app/routes/admin.py`, `app/utils/decorators.py`, `app/templates/admin/*.html`.
- **Gap:** no route exists for a regular user to **create** a `Report` in the first place — the reporting form/button is not implemented anywhere in the buyer-facing UI, even though the entire admin-side review workflow for reports is built and functional.

### 10.10 Google OAuth (Optional)
- **Purpose:** Frictionless sign-in for students who prefer not to create a new password.
- **Internal working:** Conditionally registered in `create_app()` only if OAuth credentials are configured, so the feature gracefully doesn't appear at all (no "Continue with Google" button rendered — see `register.html`'s `{% if config.get('GOOGLE_CLIENT_ID') %}`) when not configured.
- **Files:** `app/__init__.py`, `app/routes/auth.py` (`google_login_callback`), `app/services/auth_service.py` (`get_or_create_oauth_user`).

---

## 11. Code Walkthrough

**Where to start reading this codebase, in order:**

1. **`run.py`** — the true entry point. Understand `initialize_database()` first (MySQL auto-creation + seeding), then see that `create_app()` is called *after* that, and the dev server starts with `app.run(debug=True, port=5000)`.
2. **`app/config.py`** — see how `FLASK_ENV` selects a config class, and what settings exist (`SECRET_KEY`, `SQLALCHEMY_DATABASE_URI`, `MAX_CONTENT_LENGTH`, `ALLOWED_EXTENSIONS`, Google OAuth keys).
3. **`app/extensions.py`** — the two shared extension singletons (`db`, `login_manager`) that get bound to the app later. This two-step "declare, then init_app" pattern is what avoids circular imports in Flask factories.
4. **`app/__init__.py`** (`create_app()`) — the Application Factory. Read top to bottom: extension init → upload folder creation → `user_loader` registration → blueprint registration → conditional Google OAuth blueprint → `db.create_all()`.
5. **Routing layer — `app/routes/*.py`** — thin controllers. Read `main.py` first (simplest), then `auth.py`, `product.py`, `wishlist.py`, `profile.py`, `dashboard.py`, `admin.py`.
6. **Controllers → Services** — for each route file, jump to the matching `app/services/*.py` file to see where the actual decision-making happens (validation, DB writes).
7. **Services → Models** — `app/models/*.py` — the SQLAlchemy schema definitions, relationships, and small convenience properties/methods (e.g., `User.is_admin`, `Product.primary_image`).
8. **Utilities — `app/utils/`** — cross-cutting helpers used by services/routes: `decorators.py` (`admin_required`), `validators.py` (email/password rules).
9. **Templates — `app/templates/`** — start with `base.html` (the shared shell), then drill into the folder matching whichever route you're tracing.
10. **Static assets — `app/static/`** — `js/app.js` for global behaviors; per-page inline `<script>` blocks for page-specific AJAX/interactivity (wishlist toggle, image preview, chart rendering).

**Configuration:** everything sensitive/environment-specific is read via `os.getenv()` in `config.py`, backed by a `.env` file loaded with `python-dotenv`. There is no separate `settings/` package or YAML config — just the one `config.py`.

---

## 12. Important Functions

| Function | File | Purpose | Inputs | Outputs | Why it exists |
|---|---|---|---|---|---|
| `create_app(config_name=None)` | `app/__init__.py` | Application Factory — builds and wires a complete Flask app instance | Optional config name string | Configured `Flask` app object | Enables creating multiple independent app instances (e.g., for testing) without global state; central place where every blueprint/extension is registered |
| `initialize_database()` | `run.py` | Ensures the MySQL database exists (if using MySQL) and that all tables + seed data are present before the app serves traffic | Reads `DATABASE_URL` from env | None (side effect: DB ready) | Removes the manual "create the database first" step for whoever runs the project |
| `seed_categories()` | `seed.py` | Idempotently inserts the 8 fixed categories and a default admin account | None | None (side effect: DB rows) | Guarantees a usable app on first run without manual data entry |
| `AuthService.register_user(name, email, password)` | `app/services/auth_service.py` | Validates and creates a new local user | name, email, password strings | `(bool success, User \| str message)` | Central chokepoint for all registration business rules (domain check, uniqueness, password strength) |
| `AuthService.login_user(email, password)` | `app/services/auth_service.py` | Authenticates a local user | email, password | `(bool success, User \| str message)` | Encapsulates all reasons a login can fail (not found, banned, wrong provider, wrong password) in one ordered check |
| `AuthService.get_or_create_oauth_user(email, name, provider)` | `app/services/auth_service.py` | Finds or creates a user coming from an OAuth provider | email, name, provider string | `(bool success, User \| str message)` | Keeps OAuth users subject to the exact same campus-domain and ban rules as local users |
| `ProductService.create_product(seller_id, data, files)` | `app/services/product_service.py` | Validates and persists a new listing, including its images | seller id, form dict, uploaded files | `(bool success, int product_id \| str error)` | Single source of truth for "what makes a valid listing" |
| `ProductService.get_all_active_products(...)` | `app/services/product_service.py` | Builds a filtered, paginated query over active listings | category_slug, search_query, min/max price, condition, is_exchangeable, page, per_page | Flask-SQLAlchemy `Pagination` object | Powers both the homepage feed (first 8) and the full Explore page with the same logic |
| `ImageService.process_and_save_product_image(file)` | `app/services/image_service.py` | Validates, resizes, converts, and saves one uploaded image | Werkzeug `FileStorage` object | Relative URL string, or `None` on failure | Keeps all uploaded product images small, uniform format (WebP), and safely named (no user-controlled filenames reach disk) |
| `ImageService.delete_image(image_url)` | `app/services/image_service.py` | Removes a physical file from disk when a listing/image is deleted | Stored image URL string | Boolean | Prevents orphaned files accumulating on disk when listings are deleted |
| `AnalyticsService.get_seller_stats(user_id)` | `app/services/analytics_service.py` | Computes 4 aggregate metrics for a seller | user id | Dict of 4 integers | Single query surface for the dashboard's stat cards, using SQL-side `COUNT`/`SUM` instead of pulling all rows into Python |
| `is_valid_campus_email(email)` | `app/utils/validators.py` | Decides if an email is allowed to register/login | email string | Boolean | The core rule that defines "who counts as a student" for this platform |
| `validate_password_strength(password)` | `app/utils/validators.py` | Enforces minimum password rules | password string | `(bool valid, str error_message)` | Keeps password policy in one reusable place instead of duplicated in routes |
| `admin_required(f)` | `app/utils/decorators.py` | Decorator that blocks non-admins from a view | A view function | Wrapped view function | DRY way to protect every admin route without repeating the same `if` check |
| `User.set_password` / `User.check_password` | `app/models/user.py` | Hash and verify passwords | Plaintext password | None / Boolean | Keeps password hashing logic attached to the model, so no other code ever touches raw hashes directly |
| `Product.primary_image` (property) | `app/models/product.py` | Picks which image to show first for a listing | — | URL string (real image or placeholder) | Centralizes "what if there's no primary flagged, or no images at all" fallback logic used across many templates |

---

## 13. Interview Questions

### 13.1 Basic (25 questions)

1. **What is MediCart and what problem does it solve?**
   *Answer:* It's a Flask-based marketplace restricted to students with campus (`.edu`/`.ac.in`) emails, so buyers/sellers trading used items like textbooks or electronics have some baseline trust that they're both students, unlike open marketplaces like OLX.

2. **What design pattern does the Flask app use to bootstrap itself?**
   *Answer:* The Application Factory pattern — `create_app()` in `app/__init__.py` builds and configures the Flask instance, instead of a module-level global `app = Flask(__name__)`. This allows creating separate app instances for testing vs. running.

3. **What is a Flask Blueprint, and how many does this project have?**
   *Answer:* A Blueprint groups related routes/templates/static files under one namespace that can be registered onto the main app. This project has 7: `main`, `auth`, `product`, `wishlist`, `profile`, `dashboard`, `admin`.

4. **How is the database configured differently for development vs production?**
   *Answer:* `app/config.py` defines `DevelopmentConfig` (defaults to `sqlite:///medicart.db`) and `ProductionConfig` (requires `DATABASE_URL`, intended to be MySQL). `FLASK_ENV` picks which one loads.

5. **How are passwords stored?**
   *Answer:* Hashed with `werkzeug.security.generate_password_hash` using `pbkdf2:sha256`, never stored in plaintext. Verified with `check_password_hash`.

6. **Does this project use JWT?**
   *Answer:* No. Authentication is entirely session/cookie-based via Flask-Login.

7. **What ORM is used, and why?**
   *Answer:* Flask-SQLAlchemy. It lets model classes in `app/models/` map directly to tables and lets the same code run against SQLite (dev) or MySQL (prod) without changes.

8. **What are the six database tables in this project?**
   *Answer:* `users`, `categories`, `products`, `product_images`, `wishlists`, `reports`.

9. **How does a product get marked "for exchange" vs "for sale"?**
   *Answer:* `Product.price` is nullable; if it's `None` and `is_exchangeable` is `True`, it's an exchange-only listing. The service layer requires at least one of price or exchange to be set.

10. **What image format are uploaded photos converted to, and why?**
    *Answer:* WebP, because it gives good compression at similar quality to JPEG/PNG, keeping storage and page-load size small.

11. **How does the wishlist feature avoid a full page reload?**
    *Answer:* The heart button triggers a `fetch()` POST call to `/wishlist/toggle/<id>`, which returns JSON; JavaScript then updates the button's icon/text without navigating.

12. **What prevents a user from wishlisting the same product twice?**
    *Answer:* A unique constraint at the database level on `(user_id, product_id)` in the `wishlists` table, in addition to the route checking for an existing row first.

13. **How is dark mode implemented?**
    *Answer:* A `dark_mode` boolean column on `User`, settable from the Settings page; it's also mirrored to the browser's `localStorage` so the toggle works instantly client-side and persists across sessions server-side.

14. **How does the app restrict registration to students?**
    *Answer:* `is_valid_campus_email()` checks if the email ends in `.edu` or `.ac.in` (or matches a hardcoded allowed-domain list) before allowing registration or OAuth login.

15. **What happens when an admin bans a user?**
    *Answer:* `User.is_banned` flips to `True`; that user is blocked from logging in going forward (both local and Google login paths check this flag), but an existing session isn't force-terminated.

16. **What Python library handles image resizing?**
    *Answer:* Pillow (PIL) — used in `ImageService` and inline in `UserService` for avatars.

17. **How is pagination implemented on the Explore page?**
    *Answer:* Flask-SQLAlchemy's built-in `.paginate(page, per_page, error_out=False)` on the query object, returning a `Pagination` object the template iterates over.

18. **What JavaScript charting library is used, and where?**
    *Answer:* Chart.js, on the seller dashboard, to draw a line chart of "Listing Views (Last 7 Days)."

19. **Is that chart backed by real historical data?**
    *Answer:* No — it's currently a hardcoded static array in `app/routes/dashboard.py`, explicitly commented as a placeholder for a future real time-series query.

20. **What decorator protects admin-only routes?**
    *Answer:* `@admin_required` from `app/utils/decorators.py`, applied once via `admin_bp.before_request` so it covers the entire admin blueprint.

21. **Can a seller edit someone else's listing?**
    *Answer:* No — `ProductService` checks `product.seller_id == user_id or is_admin` before allowing edit/delete/status changes.

22. **What's stored in the `.env` file?**
    *Answer:* `SECRET_KEY`, `DATABASE_URL`, Google OAuth client ID/secret, upload size limit, and upload folder path.

23. **What happens if `GOOGLE_CLIENT_ID` isn't set?**
    *Answer:* `create_app()` simply skips registering the Google OAuth blueprint, and the "Continue with Google" button doesn't render (guarded by `{% if config.get('GOOGLE_CLIENT_ID') %}` in the templates).

24. **How are flash messages displayed to the user?**
    *Answer:* Flask's `flash()` stores a `(category, message)` pair in the session; `base.html` reads `get_flashed_messages(with_categories=true)` and renders them, and `app.js` auto-dismisses them after a few seconds.

25. **What does `Product.primary_image` return if a listing has no images?**
    *Answer:* A placeholder path, `/static/images/product-placeholder.jpg`.

### 13.2 Intermediate (25 questions)

26. **Walk through what happens end-to-end when a user submits the "create listing" form.**
    *Answer:* See Section 3.5 — form data hits `product.create()`, delegates to `ProductService.create_product()`, which validates category/price, creates the `Product` row, flushes to get an ID, then processes each uploaded image via `ImageService`, attaching `ProductImage` rows, and commits once at the end.

27. **Why does the code call `db.session.flush()` before processing images instead of just `commit()`?**
    *Answer:* `flush()` sends the pending INSERT to the DB (assigning the auto-increment `product.id`) without ending the transaction, so the code can immediately use `product.id` to create related `ProductImage` rows in the *same* transaction — if anything fails afterward, everything rolls back together.

28. **Explain the search filter logic in `get_all_active_products`. Why build the query this way?**
    *Answer:* It starts from a base query (`status='active'`) and conditionally chains `.filter()` only when a given parameter is truthy — this is the standard "dynamic query builder" pattern in SQLAlchemy, avoiding either duplicating queries for every filter combination or constructing raw SQL strings.

29. **Why is `is_valid_campus_email` also checked in the OAuth flow, not just local registration?**
    *Answer:* Otherwise a user could bypass the campus-restriction entirely by simply using any personal Gmail account through Google login — the business rule ("only students") has to be enforced regardless of the authentication method.

30. **How does the "secure redirect" after login prevent open-redirect vulnerabilities?**
    *Answer:* `next_page` from the query string is only trusted if `urlparse(next_page).netloc == ''`, meaning it must be a relative path with no host component — otherwise an attacker could craft a login link with `?next=https://evil.com` to redirect victims off-site after they authenticate.

31. **Why does avatar processing duplicate image logic instead of reusing `ImageService`?**
    *Answer:* Because `ImageService.process_and_save_product_image()` hardcodes the `products` upload subdirectory and doesn't support square-cropping; rather than generalizing it, `UserService` inlines a near-duplicate Pillow pipeline with different dimensions (300×300, center-cropped). This is a known duplication — a good "what would you refactor" answer.

32. **How does the unique constraint on `wishlists` protect against race conditions that pure application logic wouldn't?**
    *Answer:* If two rapid-fire toggle requests both check "does this row exist?" and both get "no" before either commits, application-only logic could insert two rows; a database-level unique constraint guarantees the second insert fails at the DB layer regardless of timing.

33. **Why is `AnalyticsService` written with SQL aggregate functions (`COUNT`, `SUM`) instead of loading all products into Python and summing there?**
    *Answer:* Aggregation in the database is far more efficient — it avoids pulling potentially thousands of rows over the wire just to compute a single number, and lets the database use indexes/optimizations internally.

34. **What is the difference between `Flask-Login`'s session and a JWT-based session, and why does this project use the former?**
    *Answer:* Flask-Login stores a signed reference to the user in a server-readable, client-held cookie, validated on every request by looking up the user via `user_loader`; JWTs are self-contained, stateless tokens verified purely by signature, no server lookup needed but harder to revoke instantly. This project is a traditional server-rendered site with `current_user` available directly in Jinja templates, so the simpler, well-integrated cookie-session model fits better than adding token issuance/refresh complexity.

35. **How would you explain the difference between `db.session.commit()` and `db.session.flush()` to a junior developer?**
    *Answer:* `flush()` pushes pending changes to the DB within the current transaction (so IDs/constraints become visible) but doesn't make them permanent; `commit()` ends the transaction and makes changes permanent (and un-rollback-able).

36. **Why does `ProductService.create_product` wrap everything in a try/except with `db.session.rollback()`?**
    *Answer:* If any step fails after some records were already added to the session (but not yet committed), rolling back ensures partial writes (e.g., a `Product` with only 2 of 5 images attached) never get persisted — the whole operation is atomic in intent.

37. **What's the significance of `lazy='dynamic'` on the `Wishlist`/`ProductImage` relationships vs `lazy='joined'`?**
    *Answer:* `lazy='dynamic'` (used for `User.wishlisted_items`, `Product.wishlisted_by`) returns a query object you can further filter/count without loading all rows — useful when you might only want a count. `lazy='joined'` (used for `Product.images`) always eagerly loads via a SQL JOIN whenever the parent is loaded, which is efficient here because a product's images are almost always needed together with the product.

38. **How does `admin_bp.before_request` combined with two decorators actually work?**
    *Answer:* `@admin_bp.before_request` registers a function that Flask runs before every request routed to that blueprint; stacking `@login_required` and `@admin_required` on top of it means both checks run automatically before any individual view in `admin.py`, without needing to decorate each view function separately.

39. **What would happen if two categories had the same slug?**
    *Answer:* It can't happen — `Category.slug` has a `unique=True` constraint, so the database itself would reject a duplicate insert (and the seed script explicitly checks `filter_by(slug=...).first()` before inserting to avoid ever attempting it).

40. **Explain how `condition` and `status` are validated on `Product`. Is this enforced by the database?**
    *Answer:* No — these are plain `VARCHAR` columns with no `CHECK` constraint or DB-level enum. Validity (e.g., `status` must be one of 4 values) is only checked in `ProductService.update_status()`'s Python-level whitelist. A direct DB write bypassing the service layer could insert an invalid value.

41. **How does `main.explore()` prevent a `ValueError` when a user submits an empty price filter field?**
    *Answer:* It explicitly checks `if min_price_str else None` before calling `float()`, rather than calling `float('')` directly, which would raise an exception.

42. **What does `ImageService.allowed_file()` check, and is it a strong security control on its own?**
    *Answer:* It checks the file extension against `current_app.config['ALLOWED_EXTENSIONS']` (`png/jpg/jpeg/webp`). By itself, extension-checking is weak (a file can be renamed), but because the image is then *actually opened and re-encoded by Pillow*, a non-image file disguised with an image extension would fail to open/process rather than being saved as-is — the real security benefit comes from the re-encoding step, not the extension check alone.

43. **Why store `is_primary` on `ProductImage` instead of always using `images[0]`?**
    *Answer:* It gives explicit, stable control over which photo is the "cover" image regardless of upload/insert order, and `Product.primary_image` falls back to `images[0]` only if no image is explicitly flagged — a defensive default.

44. **How does the seed script make itself safe to run multiple times (idempotency)?**
    *Answer:* Before inserting each category or the admin user, it queries for an existing row with the same unique key (`slug` or `email`) and only inserts if none is found — so re-running `seed.py` or restarting the app never creates duplicates.

45. **Why does `run.py` call `create_app()` twice indirectly (once inside `seed_categories()`, once directly)?**
    *Answer:* `seed_categories()` needs its own app context to run DB operations before the "real" serving app is constructed (partly for encapsulation/isolation of the seeding step); the cost is a redundant `create_app()` call at every startup, which also means `db.create_all()` runs twice — harmless since `create_all()` is idempotent (skips existing tables), but worth noting as slightly wasteful.

46. **What does the Explore page do to preserve all other filters when a user changes just one (e.g., clicks a category radio button)?**
    *Answer:* Each filter's form auto-submits on change (`onchange="document.getElementById('filter-form').submit()"`), and hidden inputs carry forward the current search text (`q`) and other applied filters, so submitting one filter doesn't wipe out the others.

47. **How would a stale report (pointing to a deleted product) be surfaced as a bug?**
    *Answer:* If admin deletes a reported listing via `/admin/listings/<id>/delete` (or via the "Delete Listing" button on the Reports page itself), the `Report` row referencing that `product_id` is never deleted or updated — rendering `/admin/reports` again would try to access `report.product.title`, which would fail or render as `None`/error since the relationship target no longer exists.

48. **Why is `Product.condition` and `Product.status` not modeled as a Python `Enum`?**
    *Answer:* It isn't in this codebase — they're just plain strings validated ad-hoc; using SQLAlchemy's `Enum` type (or at least Python `enum.Enum` constants shared between model and service) would be a natural improvement for correctness and self-documentation.

49. **What's the purpose of the `member_since` and `initials` properties on `User`?**
    *Answer:* They're presentation-layer conveniences computed on the fly from `created_at`/`name` — kept on the model so templates don't need to duplicate formatting logic (`strftime`, name-splitting) in multiple places.

50. **How does the app avoid circular imports between `extensions.py`, models, and `create_app()`?**
    *Answer:* `db` and `login_manager` are instantiated once in `extensions.py` with no app bound yet; models import `db` from `extensions.py` (not from `app/__init__.py`), and `create_app()` imports models/blueprints lazily *inside* the factory function body — this deferred-import pattern is the standard fix for Flask factory circular-import issues.

### 13.3 Advanced (25 questions)

51. **If this app needed to scale to 1 million users, what's the single biggest architectural bottleneck as it stands today?**
    *Answer:* The Flask dev server (`app.run(debug=True)`) is not production-grade — single-process, no concurrency handling built for load. Beyond that, missing indexes on `products.seller_id`/`status`/`category_id`, no caching layer, and local-disk image storage (not horizontally scalable across multiple app servers) would all become bottlenecks. See Section 17 for a full breakdown.

52. **How would you convert the session-based auth model to support a separate mobile app / API client?**
    *Answer:* Introduce token-based auth (JWT or opaque API tokens) as a *parallel* auth path alongside the existing cookie-session flow (Flask-Login can coexist with an API-token check), likely by adding a `/api/` blueprint that issues/validates tokens instead of using `login_user()`, while keeping the existing web UI on cookies.

53. **Why might PBKDF2-SHA256 be considered weaker than bcrypt/argon2 for password storage, and would you change it?**
    *Answer:* PBKDF2 is CPU-bound and can be accelerated significantly with GPUs/ASICs compared to bcrypt (which is deliberately slow and memory-light) or argon2 (memory-hard, resistant to parallel hardware attacks). For a production system I'd migrate to argon2 via `argon2-cffi`, ideally with a migration path that re-hashes on next successful login.

54. **The app has no CSRF protection. Describe a concrete attack this makes possible, and how you'd fix it.**
    *Answer:* An attacker could host a page with a hidden auto-submitting form pointing at, e.g., `/profile/delete` or `/admin/users/<id>/toggle-ban`; if a logged-in victim (or admin) visits that page, their browser sends the session cookie automatically and the action executes without their consent. Fix: add Flask-WTF's CSRF protection (`CSRFProtect(app)`), embed a hidden CSRF token in every state-changing form, and validate it server-side.

55. **How would you redesign the "views" tracking so the dashboard chart is real instead of hardcoded?**
    *Answer:* Add a `product_views` table (or a simpler daily-rollup table) recording `(product_id, date, count)`, incremented on each detail-page view (ideally de-duplicated per viewer per day to avoid trivial self-inflation), then query the last 7 days grouped by date for the chart instead of the current single lifetime counter on `Product`.

56. **The product detail page increments `views` on every request, even the owner's own visits and repeated refreshes. What's wrong with that, and how would you fix it?**
    *Answer:* It inflates view counts artificially (an owner refreshing their own listing, or a bot/crawler hitting the page, both count) and gives sellers a misleading analytics signal. A fix: only increment when `current_user.id != product.seller_id`, and/or de-duplicate views per (user or IP+session) per time window using a `Set`/Redis-backed dedup key or a `product_views` log table with a uniqueness window.

57. **Explain a plausible race condition in the wishlist toggle endpoint and whether it's actually exploitable given the schema.**
    *Answer:* Two near-simultaneous POSTs from the same user for the same product could both read "no existing row" before either insert commits, and both attempt to insert — but because of the `UniqueConstraint('user_id', 'product_id')`, the second insert fails at the database level, which the route's `except Exception` block would catch and roll back, returning a 500 with `{"status": "error"}` — so it fails safely rather than creating duplicates, but the user-facing failure isn't graceful (they'd just see an error toast on what should have succeeded as a toggle).

58. **If you needed to add real-time buyer-seller messaging (currently just a dead "Contact Seller" button), what would you build?**
    *Answer:* A `Conversation`/`Message` model (conversation scoped to a buyer+seller+product), a Blueprint for message routes, and either polling (simplest, fits the existing server-rendered architecture) or WebSockets (via Flask-SocketIO) for real-time delivery — polling would be the pragmatic first step given no other real-time infra exists in this app today.

59. **How would you index the database to make the Explore page fast at scale?**
    *Answer:* Composite index on `(status, category_id, created_at)` for the common "active in category, newest first" query pattern, an index on `seller_id` for dashboard/profile queries, and for full-text search on title/description, move off `ILIKE '%...%'` (which can't use a normal B-tree index efficiently) to a proper full-text search engine (Postgres `tsvector`, MySQL `FULLTEXT`, or an external engine like Elasticsearch/Meilisearch).

60. **Why is `ILIKE` used for search, and what's its performance downside at scale?**
    *Answer:* `ILIKE '%term%'` gives simple case-insensitive substring matching without extra setup, but a leading wildcard (`%term`) can't use a standard index — it forces a full table scan on `products`, which becomes slow as the table grows.

61. **The `SECRET_KEY` config falls back to a hardcoded string if the env var is missing. Why is that dangerous, and what would you do differently in production?**
    *Answer:* If deployed with the fallback key, session cookies/signing become predictable/publicly known (since it's in this very repo's source), letting an attacker forge session cookies. Fix: fail fast at startup in `ProductionConfig` if `SECRET_KEY` isn't set, rather than silently falling back.

62. **How would you introduce caching to reduce database load on the homepage and Explore page?**
    *Answer:* Add Flask-Caching with a Redis backend; cache the category list (rarely changes) with a long TTL and a cache-bust on category changes, and cache the "recent 8 products" homepage query for a short TTL (e.g., 30–60 seconds) since it doesn't need to be perfectly real-time.

63. **What's a safe way to handle background/async tasks this app currently does synchronously (e.g., image processing)?**
    *Answer:* Move image resizing/encoding off the request thread into a task queue (Celery + Redis/RabbitMQ, or RQ) — the create-listing request would save the raw upload, enqueue a processing job, and return immediately with a "processing" placeholder image, updating to the final WebP once the worker finishes. This matters especially under concurrent uploads since Pillow operations are CPU-bound and currently block the request.

64. **How would you split this monolith into microservices if it needed to scale independently by feature?**
    *Answer:* Natural seams already exist along the service boundaries: an Auth service, a Listings/Search service (likely paired with a search engine), a Media/Image-processing service, and a Notifications/Messaging service (once built) — the existing `services/` layer's separation of concerns makes this decomposition easier than if logic were scattered directly in routes.

65. **The app increments a lifetime `views` counter directly with `product.views += 1; db.session.commit()`. What's the concurrency risk here under high traffic?**
    *Answer:* This is a read-modify-write race: two concurrent requests could both read the same starting value before either commits, causing a lost update (one increment is silently dropped). At scale, this should be an atomic DB-level increment (e.g., `UPDATE products SET views = views + 1 WHERE id = :id`, which SQLAlchemy supports via `Product.views = Product.views + 1` compiled to a single SQL expression) rather than a Python-side read-then-write.

66. **How would you add horizontal scalability for image storage?**
    *Answer:* Move uploads off local disk to object storage (S3-compatible), storing just the object key/URL in `ProductImage.image_url` — this decouples images from any specific app server instance, which is required the moment you run more than one web server behind a load balancer.

67. **What monitoring/logging would you add before calling this production-ready?**
    *Answer:* Structured application logging (currently only `current_app.logger.error(...)` in a couple of `except` blocks in `ImageService`), a request/error tracking tool (e.g., Sentry), and infrastructure-level metrics (response times, error rates, DB query times) via something like Prometheus/Grafana or a hosted APM.

68. **What testing exists in this project today, and what would you add first?**
    *Answer:* There are no automated tests in this repository at all (no `tests/` directory, no pytest config). I'd start with unit tests for the service layer (pure business logic, easy to test in isolation — e.g., `validate_password_strength`, `is_valid_campus_email`, `ProductService`'s price/exchange validation), then integration tests hitting routes with Flask's test client against the `TestingConfig` (`sqlite:///:memory:`, already defined in `config.py` but unused).

69. **How does `TestingConfig` differ from the other configs, and is it actually wired up anywhere?**
    *Answer:* It sets `TESTING = True` and an in-memory SQLite DB (`sqlite:///:memory:`) — ideal for fast, isolated tests. It exists in `config.py`'s `config` dict but nothing in the codebase currently invokes `create_app('testing')` — it's dead/unused configuration, ready for a test suite that doesn't exist yet.

70. **Explain how you'd implement rate limiting on the login/register endpoints and why it matters here.**
    *Answer:* Add Flask-Limiter keyed by IP (and/or email) with a strict limit (e.g., 5 attempts/minute) on `/auth/login` and `/auth/register` — without it, this app is currently open to credential-stuffing/brute-force attacks and registration spam, since nothing throttles repeated POSTs.

71. **What would a real "reviewed" report workflow look like, given the model already has `admin_notes` and `reviewed_at` fields that are never set by any route?**
    *Answer:* Add a route like `/admin/reports/<id>/resolve` accepting `admin_notes` and an action (e.g., "remove listing" / "warn seller" / "no action"), setting `status='reviewed'`, `reviewed_at=now()`, and `admin_notes` — today only `dismiss` (→ `'dismissed'`) and outright product deletion exist; the "reviewed" status and notes fields are defined in the schema but structurally unreachable through any current endpoint.

72. **How would you prevent the orphaned-report bug (Section 7.3) at the database level instead of relying on application discipline?**
    *Answer:* Add `ondelete='CASCADE'` (or `'SET NULL'`) to the `reports.product_id` foreign key definition (and a matching `cascade` on the SQLAlchemy relationship), so deleting a `Product` automatically removes (or nullifies) any `Report` rows referencing it, instead of leaving dangling references.

73. **If you had to support multiple campuses (not just one university) properly, what schema change would you make?**
    *Answer:* Introduce a `Campus`/`University` table and a `campus_id` foreign key on `User` (derived from the verified email domain), then scope product visibility/search to the viewer's own campus by default — today, the campus-email check only gates *registration*, but all students from every accepted domain share one single global marketplace with no campus-level segmentation.

74. **What's the tradeoff of running `db.create_all()` on every app startup instead of using a real migration tool like Alembic/Flask-Migrate?**
    *Answer:* `create_all()` is convenient for early development (no migration files to write) but it **only creates tables that don't yet exist** — it does not alter existing tables when a model changes (e.g., adding a new column to `User` won't retroactively add that column to an already-created `users` table). This project's README even mentions Flask-Migrate as part of the stack, but it is **not actually in `requirements.txt`** and no `migrations/` folder exists — schema evolution over time would require manually altering the database or dropping/recreating it, which is unsafe for a real production database with existing data.

75. **Given everything above, what are the top 3 things you'd fix first if given one more sprint, and why those specifically?**
    *Answer:* (1) CSRF protection — because it's a concrete, exploitable security gap with a well-known, low-effort fix (Flask-WTF). (2) Real report-submission route + resolving the orphaned-report cascade issue — because the report/moderation feature is currently half-built (admin side exists, user side doesn't) and could actively break (dangling FK) as-is. (3) Move to a real migration tool (Flask-Migrate/Alembic) — because every future schema change becomes progressively riskier without it, and it's the kind of debt that's cheap to fix now and expensive to fix after production data exists.

---

## 14. Cross Questions (Follow-up Chains)

**Chain 1 — Why Flask?**
```
Why Flask?
   → "Lightweight, flexible, I wanted control over folder structure."
Why not Django?
   → "Django bundles an ORM, admin panel, and auth system with strong conventions;
      for a project this size I didn't need Django's batteries, and Flask let me
      design my own service-layer architecture rather than fight Django's MVT structure."
Why not FastAPI?
   → "FastAPI shines for JSON APIs with async I/O and automatic OpenAPI docs;
      this app is server-rendered HTML with Jinja2, which FastAPI doesn't provide
      out of the box the way Flask does — I'd have had to bolt on a template engine anyway."
Trade-offs?
   → "Flask gives me flexibility but also means I hand-rolled things Django would give
      for free (admin panel, CSRF middleware, migrations) — and in fact CSRF protection
      is a real gap in this project today because I didn't add Flask-WTF."
When would you choose Django instead?
   → "If the project needed a fast admin backoffice out of the box, built-in migrations,
      and a more 'convention over configuration' team structure — Django's admin alone
      would have given free CRUD screens for Users/Products/Reports instead of hand-building
      the entire /admin blueprint from scratch."
```

**Chain 2 — Why session-based auth instead of JWT?**
```
Why Flask-Login sessions instead of JWT?
   → "It's a server-rendered app, not a decoupled SPA/API — current_user needs to be
      available directly in Jinja templates on every page load, which cookie-sessions give for free."
Isn't JWT more "modern"?
   → "JWT solves a different problem — stateless auth across multiple services/servers
      without a shared session store. This app doesn't have that requirement yet."
What if you needed a mobile app to talk to the same backend?
   → "I'd add a parallel token-based auth path for API clients — issue a JWT or opaque
      token from a dedicated /api/auth/login endpoint — while leaving the existing
      web session flow untouched for the browser-based UI."
How would you revoke a JWT if a user gets banned mid-session, since JWTs are stateless?
   → "Either keep tokens short-lived and re-validate ban status on every refresh,
      or maintain a small server-side blocklist/Redis set of revoked token IDs checked
      on each request — which reintroduces some statefulness, which is the classic
      JWT revocation trade-off."
```

**Chain 3 — Why no CSRF protection?**
```
Why is there no CSRF protection?
   → "It was consciously skipped for this iteration — there's actually a code comment
      in wishlist/index.html acknowledging it was deferred."
What's the actual risk?
   → "Any state-changing POST route — delete listing, ban user, toggle wishlist,
      delete account — could be triggered by a malicious third-party page if a
      victim with an active session visits it, since the browser auto-attaches cookies."
How would you fix it, concretely?
   → "Flask-WTF's CSRFProtect(app), which auto-validates a hidden token on every
      POST form; I'd add {{ csrf_token() }} as a hidden field to every <form> in the templates."
Would that break the AJAX wishlist endpoint?
   → "I'd need to also send the token via a custom header (e.g., X-CSRFToken) in the
      fetch() call for the /wishlist/toggle endpoint, since it's JSON, not a classic form post."
```

**Chain 4 — Why is the dashboard chart hardcoded?**
```
Is the dashboard chart data real?
   → "No — it's a hardcoded 7-value array in the dashboard route, explicitly
      commented as an MVP placeholder."
Why not implement it properly?
   → "There's no table tracking views over time — Product only has a lifetime
      'views' integer, not a per-day history."
How would you build the real version?
   → "Add a product_views table logging (product_id, viewed_at) or a daily
      rollup table, then group by day for the last 7 days per seller."
Would that affect performance if every page view writes a row?
   → "Yes, at scale I'd batch/async that write (e.g., through a queue) rather than
      writing synchronously on every single detail-page request."
```

**Chain 5 — Why store images on local disk instead of cloud storage?**
```
Why local disk for uploads?
   → "Simplicity for a single-server project — no external service/credentials needed."
What breaks if you scale to multiple app servers behind a load balancer?
   → "Each server would only see the files uploaded to it locally, so a user's image
      might 404 depending on which server handles a later request."
How would you fix that?
   → "Move to S3-compatible object storage; store the returned key/URL in
      ProductImage.image_url instead of a local path, so any server can serve any image."
```

---

## 15. Challenges Faced

These are grounded strictly in decisions visible in the code — not invented anecdotes.

| Challenge | Root Cause | Solution Implemented | Learning |
|---|---|---|---|
| **Handling "price OR exchange" as a valid listing state without a messy schema** | A listing can be for sale, for exchange, or both — modeling this as separate tables/flags could get complicated | Made `price` nullable and added an `is_exchangeable` boolean, then enforced "at least one must be set" purely in `ProductService`, not the database | Sometimes the simplest schema plus an application-level invariant is more pragmatic than an over-normalized schema, as long as the invariant is enforced in exactly one place (the service layer) |
| **Avoiding circular imports in the Flask factory pattern** | `models` need `db`, `create_app()` needs `models` (for the user loader) and `routes` (which need `services`, which need `models`) | Declared `db`/`login_manager` in a separate `extensions.py` with no app bound, and deferred all model/blueprint imports to *inside* `create_app()` | This is the canonical Flask factory pattern fix — understanding *why* Python circular imports happen (module-level imports executing top-to-bottom at import time) was key |
| **Making the app runnable with zero manual database setup (MySQL)** | Contributors/graders shouldn't need to manually create a MySQL database and run migrations before the app works | `run.py`'s `initialize_database()` opens a server-level (not database-level) SQLAlchemy connection and runs `CREATE DATABASE IF NOT EXISTS` before the app itself connects to that specific database | Bootstrapping infra automatically trades a bit of "magic" for a much smoother first-run experience, but it does mean the app has elevated DB privileges (CREATE DATABASE) at startup, which wouldn't be appropriate for most production deployments |
| **Uploaded images varying wildly in size/format** | Users can upload arbitrarily large PNGs/JPEGs with transparency, different aspect ratios, and unpredictable orientation | Standardized every product image through Pillow: convert RGBA/palette to RGB, downscale to max 1200px on the long edge, re-encode as WebP at quality 85 with a random filename | Normalizing user input at the boundary (upload time) rather than trying to handle every format/size downstream keeps the rest of the app (templates, thumbnails) simple |
| **Keeping filter combinations on the Explore page composable** | Users can combine text search + category + price range + condition + exchange-only in any combination | Built the query incrementally with conditional `.filter()` calls on a single `Product.query` base, rather than writing a separate query per filter combination | SQLAlchemy's query objects are immutable-and-chainable, so this "build it up conditionally" pattern scales cleanly as more filters get added later |
| **Making Google OAuth optional without breaking the app for users who don't configure it** | Not every developer running this locally will set up Google OAuth credentials | `create_app()` only registers the Flask-Dance Google blueprint if both `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are present; templates check `config.get('GOOGLE_CLIENT_ID')` before rendering the button | Feature-flagging optional integrations at the config level (rather than assuming they're always configured) avoids hard failures for anyone missing those credentials |
| **CSRF protection was consciously deferred** | Adding Flask-WTF and threading tokens through every form (including the AJAX wishlist endpoint) was a scope/time trade-off | Left unimplemented, with an explicit in-code comment acknowledging the gap rather than silently leaving it undocumented | Better to leave an honest TODO/comment about a known security gap than to pretend it's handled — this is exactly the kind of thing to proactively bring up in an interview rather than hope it isn't asked |

---

## 16. Improvements (Given One More Month)

1. **Add CSRF protection** (Flask-WTF `CSRFProtect`) across every form and the AJAX wishlist endpoint — the single highest-value security fix given how cheap it is.
2. **Build the missing report-submission flow** — a "Report this listing" button/form on the product detail page that creates a `Report` row, completing the feature the admin side already supports end-to-end.
3. **Fix the orphaned-report bug** by adding `ondelete='CASCADE'` (or `SET NULL`) on `reports.product_id`, or deleting associated reports when a product is deleted.
4. **Replace `db.create_all()` with Flask-Migrate/Alembic** so schema changes can be applied to an existing database without data loss.
5. **Build real view-tracking** — a `product_views` (or daily rollup) table so the dashboard's Chart.js graph reflects actual behavior instead of a static array.
6. **Add a real buyer-seller messaging feature** to replace the currently non-functional "Contact Seller" button — even a simple polling-based inbox would be a major functional upgrade.
7. **Add automated tests** — unit tests for the service layer (pure logic, no Flask context needed for most of it) and integration tests using Flask's test client against `TestingConfig`, which already exists but is unused.
8. **Add rate limiting** (Flask-Limiter) on login/register to prevent brute-force and registration spam.
9. **Move to argon2 or bcrypt** for password hashing instead of PBKDF2-SHA256.
10. **Add indexes** on `products.seller_id`, `products.status`, `products.category_id` (and a composite index for the common Explore query shape).
11. **Move uploaded media to object storage** (S3-compatible) to make the app horizontally scalable across multiple servers.
12. **Deduplicate the avatar vs product image-processing code** into a single configurable `ImageService` method instead of two near-identical Pillow pipelines.
13. **Fail fast on missing `SECRET_KEY`** in `ProductionConfig` instead of silently falling back to a hardcoded dev key.
14. **Add structured logging + error monitoring** (e.g., Sentry) beyond the couple of `current_app.logger.error()` calls that exist today.
15. **Add a `Dockerfile` + a production WSGI server config** (gunicorn/uWSGI behind nginx) since the app currently only runs via Flask's development server.

---

## 17. Scalability (At 1 Million Users)

| Area | Current State | Bottleneck at Scale | Improvement |
|---|---|---|---|
| **Web server** | Flask dev server, `debug=True`, single process | Cannot handle concurrent load reliably; debug mode leaks stack traces | Run behind gunicorn/uWSGI with multiple workers, behind nginx, with `DEBUG=False` |
| **Database queries** | Missing indexes on `seller_id`, `status`, `category_id`; `ILIKE '%term%'` full scans for search | Explore page and dashboard queries slow down linearly with table size | Add targeted indexes; move free-text search to a dedicated search engine (Elasticsearch/Meilisearch) or DB full-text search |
| **Caching** | None — every homepage load re-queries categories + recent products | Repeated identical queries hammer the DB | Add Flask-Caching + Redis for category lists, homepage feed, and possibly per-product detail pages with short TTLs |
| **Image storage** | Local filesystem under `app/static/uploads/` | Not shared across multiple app server instances; disk fills up on a single box | Move to S3-compatible object storage; serve via CDN |
| **View counting** | Synchronous `product.views += 1; commit()` on every detail page load (a read-modify-write race) | Lost updates under concurrent traffic; also artificially inflates counts (owner refreshing own page counts too) | Atomic SQL increment (`views = views + 1` compiled server-side) and/or move to an async queue-based increment; exclude owner's own views |
| **Image processing** | Synchronous Pillow resize/encode inside the request/response cycle | CPU-bound work blocks the request thread; slow uploads under load | Move to a background task queue (Celery/RQ + Redis) — accept upload, respond immediately, process async |
| **Background jobs** | None exist — everything in this app is synchronous, request-triggered | Any future heavy operation (bulk emails, analytics rollups, image reprocessing) would block requests | Introduce Celery/RQ workers for anything that doesn't need to complete before the HTTP response is sent |
| **Session/auth store** | Client-side signed session cookie via Flask-Login (no server-side session store) | Actually scales fine horizontally as-is (stateless per request, no shared session store needed) since Flask's default session is cookie-based, not server-side | If moving to server-side sessions for revocation needs, use Redis-backed sessions (Flask-Session) so any app server can validate any session |
| **Microservices** | Single monolith, but already has clean internal service boundaries (`AuthService`, `ProductService`, `ImageService`, `AnalyticsService`, `UserService`) | A single service layer sharing one DB and one deploy unit | The existing service classes map naturally onto future microservice boundaries (Auth, Listings/Search, Media processing, Notifications) if/when independent scaling is needed — but this is a "later" concern, not a "first million users" concern |
| **Cloud improvements** | Runs on a single machine assumption | Single point of failure | Multi-AZ deployment, load balancer across multiple app instances, managed MySQL (e.g., RDS) with read replicas for read-heavy Explore/dashboard queries |
| **Monitoring** | Only a couple of `current_app.logger.error()` calls in `ImageService` | No visibility into errors, latency, or throughput in production | Add APM/error tracking (Sentry), metrics (Prometheus/Grafana or a hosted equivalent), and structured request logging |
| **Logging** | Flask's default logger, minimal usage | Hard to debug production incidents after the fact | Structured JSON logging with request IDs, centralized log aggregation (e.g., ELK stack or a hosted logging service) |

**Overall framing for an interview answer:** "At today's scale (a handful of test users, one SQLite/MySQL instance, one server), none of this matters. The moment you're talking about real concurrent traffic, the highest-leverage fixes in order would be: (1) stop using the dev server, (2) add the missing indexes and fix the `ILIKE` search pattern, (3) move image processing off the request thread, (4) move uploaded media to object storage so you can run more than one app server. Everything else — caching, read replicas, microservices — comes after those fundamentals are solid."

---

## 18. Security Analysis

| Threat | Status | Detail |
|---|---|---|
| **SQL Injection** | ✅ **Handled** | All database access goes through SQLAlchemy's ORM/query builder with parameterized queries (`filter_by`, `filter(Column == value)`, `.ilike(...)`), including the one raw SQL statement in `run.py` (`CREATE DATABASE IF NOT EXISTS {db_name}`) which interpolates a value parsed from the trusted, developer-supplied `DATABASE_URL` env var, not user input. No string-concatenated SQL exists anywhere in the app's request-handling code. |
| **XSS (Cross-Site Scripting)** | ✅ **Mostly handled** | Jinja2 auto-escapes all template variables by default, so user-supplied content (product titles, descriptions, bios) rendered via `{{ }}` is HTML-escaped automatically. No use of the `|safe` filter or `Markup()` was found wrapping user input. |
| **CSRF (Cross-Site Request Forgery)** | ❌ **Not handled** | No CSRF tokens anywhere — no Flask-WTF, no hidden token fields on any `<form>`. Explicitly acknowledged in a code comment in `wishlist/index.html`. Every state-changing POST route (ban user, delete listing, delete account, toggle wishlist, dismiss report) is vulnerable to a forged cross-site request if a victim with an active session is lured to a malicious page. |
| **Authentication** | ⚠️ **Partially handled** | Passwords are properly hashed (PBKDF2-SHA256); login checks ban status and provider mismatch. But: no rate limiting on login attempts (brute-force risk), no email verification (anyone can type a fake `@x.edu` address), no 2FA, and `SECRET_KEY` silently falls back to a hardcoded dev value if unset in the environment. |
| **Authorization** | ✅ **Handled at the ownership/role level** | Ownership checks (`seller_id == user_id or is_admin`) gate edit/delete/status-change. Role checks (`admin_required`) gate the entire admin blueprint via `before_request`. No route was found that skips these checks where it shouldn't. |
| **Input Validation** | ⚠️ **Partially handled** | Business-rule validation exists in the service layer (price format/sign, category existence, password strength, file extension whitelist). But there's no schema-based validation library (no WTForms/marshmallow/pydantic) — validation is hand-written per field, which is easy to miss a case in as the app grows, and there's no server-side length/format enforcement beyond what HTML `maxlength`/`required` attributes provide client-side (which can be bypassed by directly POSTing to the endpoint). |
| **File Upload Security** | ✅ **Reasonably handled** | Extension whitelist + `MAX_CONTENT_LENGTH` config limit + re-encoding every image through Pillow (which both normalizes format and effectively "detonates" any non-image file, since Pillow will fail to open it) + random UUID filenames (prevents path traversal / filename-based attacks and avoids trusting user-supplied filenames). |
| **Secrets Management** | ⚠️ **Partially handled** | Secrets (`SECRET_KEY`, DB credentials, OAuth secrets) are kept out of source control via `.env` (gitignored) and loaded with `python-dotenv`. However, there's a hardcoded fallback `SECRET_KEY` in `config.py`, and the README documents a real, working default admin password (`admin123`) that would be a serious problem if ever deployed without being changed. |
| **HTTPS** | ❌ **Not enforced by the app itself** | No `Flask-Talisman`, no `SESSION_COOKIE_SECURE` flag set, no HTTP→HTTPS redirect logic in the code. HTTPS termination, if used at all, would have to be handled entirely at the deployment/proxy layer (e.g., nginx), which isn't present in this repository. |
| **Open Redirect** | ✅ **Handled** | Post-login "next" redirect explicitly checks `urlparse(next_page).netloc == ''` before trusting it, both for local and OAuth login. |
| **Session Fixation / Cookie Security** | ⚠️ **Partially handled** | Flask-Login's default cookie is HttpOnly, mitigating JS-based cookie theft; but no explicit `SESSION_COOKIE_SECURE=True` or `SESSION_COOKIE_SAMESITE` setting was found in `config.py`. |
| **Denial of Service / Rate Limiting** | ❌ **Not handled** | No Flask-Limiter or equivalent anywhere — login, registration, wishlist toggling, and listing creation are all unthrottled. |

**Bottom line for an interview:** be ready to say clearly — "SQL injection and XSS are handled well because of how Flask/SQLAlchemy/Jinja2 work by default. CSRF, rate limiting, and HTTPS enforcement are the real, honest gaps in this project, and I know exactly what library/change would close each one."

---

## 19. Resume Questions

*(If "MediCart" appears as a bullet point on a resume, expect questions like these.)*

1. **"Tell me about MediCart."** → Use the 2-minute elevator pitch (Section 2).
2. **"What was your specific role/contribution?"** → Full-stack: designed the schema, built all Blueprints/services, implemented image processing, wired up optional OAuth, built the admin panel.
3. **"What was the hardest part to build?"** → The dynamic, composable filter query on the Explore page, or safely bootstrapping a MySQL database automatically in `run.py` — pick whichever you can speak to in the most depth.
4. **"Why did you choose Flask over Django/Node/Spring?"** → See Section 14, Chain 1.
5. **"How did you handle authentication?"** → Session-based via Flask-Login + PBKDF2 password hashing + optional Google OAuth via Flask-Dance.
6. **"Did you use JWT?"** → No — be honest, and explain why session-based auth fit a server-rendered app better (Section 13.2, Q34).
7. **"How is the database structured?"** → Walk through the 6 tables and their relationships (Section 7).
8. **"What database did you use, and why?"** → SQLite for local dev, MySQL for production, switched purely by `DATABASE_URL` thanks to SQLAlchemy being database-agnostic.
9. **"Did you write any tests?"** → Be honest: no automated tests exist yet; explain what you'd add first (service-layer unit tests, then Flask test-client integration tests) and that `TestingConfig` already exists, unused, ready for this.
10. **"How do you handle image uploads?"** → Pillow-based pipeline: validate extension, resize to max 1200px, convert to WebP, UUID filename (Section 10.3).
11. **"Is there a search feature? How does it work?"** → Yes — a single dynamically-built SQLAlchemy query with optional filters for text, category, price range, condition, exchange status, and pagination (Section 3.6).
12. **"How would this scale to more users?"** → Use Section 17's framing: dev server → real WSGI server, missing indexes, sync image processing → async, local disk → object storage.
13. **"What security measures did you implement?"** → Password hashing, XSS protection via Jinja2 auto-escaping, SQLi protection via the ORM, open-redirect protection, file-upload validation + re-encoding.
14. **"What security gaps exist, if any?"** → Be upfront: no CSRF protection (acknowledged in-code), no rate limiting, no HTTPS enforcement in-app, no email verification (Section 18).
15. **"How does the admin panel work?"** → A dedicated `admin_bp` Blueprint, gated entirely by a `before_request` hook stacking `@login_required` + `@admin_required`, covering user bans, listing deletion, and report review (Section 10.9).
16. **"What was mocked/faked vs. fully real in your project?"** → The seller dashboard's 7-day view chart uses static demo data; be upfront about this rather than getting caught overselling it.
17. **"Walk me through what happens when someone posts a new listing."** → Section 3.5, end-to-end.
18. **"How do you prevent someone from editing another user's listing?"** → Explicit ownership check (`seller_id == user_id or is_admin`) in `ProductService`.
19. **"What happens if two users try to wishlist the same item at the same time?"** → DB-level unique constraint prevents duplicates even under a race (Section 13.3, Q57).
20. **"How is dark mode implemented, and why store it in the database instead of just localStorage?"** → So the preference follows the user across devices/browsers, not just the one browser that set it; `localStorage` is also used for zero-flicker anonymous-session/instant toggling (Section 10.8).
21. **"What would you add if you had one more month?"** → Section 16.
22. **"What was the most interesting bug or edge case you had to think through?"** → The price-vs-exchange validation rule, or the orphaned-report FK issue upon listing deletion (Section 7.3 / 15).
23. **"How did you structure your code to keep it maintainable?"** → Clear separation: routes (thin controllers) → services (business logic) → models (schema) — a layered architecture, not logic dumped directly in routes.
24. **"Did you use any external APIs?"** → Google's OAuth 2.0 userinfo endpoint, optionally, via Flask-Dance.
25. **"What happens if Google OAuth isn't configured?"** → The app detects missing credentials at startup and simply doesn't register that blueprint or render the button — graceful degradation, not a crash.
26. **"How do you validate that an email belongs to a real student?"** → Be honest: it's a string-suffix check only (`.edu`/`.ac.in`), not real identity verification — no verification email is sent (Section 9).
27. **"What's your password policy?"** → Minimum 8 characters, at least one letter and one number, enforced in `validate_password_strength()`.
28. **"How is your app deployed?"** → Be honest: this repo runs via Flask's built-in dev server; there's no Dockerfile or production WSGI config in the codebase yet — explain what you'd add (gunicorn/uWSGI + nginx).
29. **"What's a design decision you'd reconsider today?"** → Duplicated image-processing logic between `ImageService` (products) and `UserService` (avatars) instead of one configurable service (Section 10.3 / 15).
30. **"How would you demo this project live in an interview?"** → Register with a `.edu`/`.ac.in` email → post a listing with images and either a price or exchange flag → search/filter it on Explore → wishlist it via AJAX → view the seller dashboard stats update → log in as admin (`admin@medicaps.ac.in` / `admin123`) → show user ban and listing moderation.

---

## 20. Weak Areas

**Topics you must be solid on before discussing this project, because interviewers will probe here:**

1. **Flask Application Factory pattern & circular imports** — be able to explain *why* `create_app()` exists and why models/blueprints are imported inside the function body, not at module level.
2. **SQLAlchemy relationship semantics** — `lazy='joined'` vs `lazy='dynamic'`, `cascade="all, delete-orphan"`, and why `Report` was left without a cascade (a real gap you should own, not hide).
3. **Session-based auth vs JWT** — know the actual trade-offs cold; don't just say "sessions are simpler," explain *why* that fits *this specific* server-rendered architecture.
4. **The exact list of unfinished/mocked features** — dashboard chart data, missing report-submission route, non-functional "Contact Seller" button, `TestingConfig` defined but unused, README claiming Flask-Migrate is used when it isn't actually a dependency. **Do not get caught claiming these are fully implemented.**
5. **CSRF** — this is the most likely "gotcha" security question. Know exactly what's missing and exactly how Flask-WTF would fix it, including the AJAX-specific header approach for the wishlist endpoint.
6. **Why `db.create_all()` isn't a migration system** — and what breaks when a model's column changes after the table already exists in a running database.
7. **Race conditions** — the `views += 1` lost-update problem and the wishlist duplicate-insert race are exactly the kind of "what could go wrong under concurrency" questions a strong interviewer will ask.
8. **The exact validation flow for "price OR exchange"** — trace it precisely: nullable price, `is_exchangeable` boolean, and the service-level rule requiring at least one.
9. **Difference between application-level validation and database-level constraints** — know which rules in this app are *only* enforced in Python (condition/status whitelist) vs *actually* enforced by the schema (unique constraints, NOT NULL, foreign keys).
10. **Image processing pipeline details** — resize dimensions (1200px products, 300×300 avatars), format (WebP), and *why* re-encoding is itself a security control (not just a size optimization).

---

## 21. One-Day Revision Notes (≈20-Minute Read)

- **What it is:** Campus-only marketplace, Flask, restricted to `.edu`/`.ac.in` emails.
- **Pattern:** Application Factory (`create_app()` in `app/__init__.py`).
- **Blueprints (7):** main, auth, product, wishlist, profile, dashboard, admin.
- **Layers:** routes (thin) → services (business logic) → models (SQLAlchemy).
- **Models (6 tables):** users, categories, products, product_images, wishlists, reports.
- **Auth:** Flask-Login session cookies (not JWT); PBKDF2-SHA256 password hashing; optional Google OAuth via Flask-Dance, conditionally registered only if configured.
- **Campus check:** `is_valid_campus_email()` — a string-suffix check on `.edu`/`.ac.in`, applied to both local and OAuth signup — not real identity verification.
- **Listings:** price nullable + `is_exchangeable` flag; must have at least one; images via Pillow → resize to 1200px max → WebP → UUID filename.
- **Search:** dynamically chained SQLAlchemy `.filter()` calls on one base query; paginated with Flask-SQLAlchemy's `paginate()`.
- **Wishlist:** AJAX toggle endpoint, DB unique constraint on `(user_id, product_id)` prevents duplicates.
- **Dashboard:** real aggregate stats (COUNT/SUM queries) but the 7-day chart is hardcoded demo data — **know this**.
- **Admin:** `admin_bp.before_request` stacks `@login_required` + `@admin_required` once for the whole blueprint; can ban users, delete listings, dismiss reports.
- **Known gaps (say these proactively if asked "what's not done"):** no CSRF protection (acknowledged in code), no user-facing report-submission route (admin review UI exists but nothing creates a report), no real messaging/"Contact Seller" (dead button), no automated tests, no Flask-Migrate despite README mentioning it, orphaned-report FK issue on listing deletion, `views` counter race condition, hardcoded `SECRET_KEY` fallback, no rate limiting, no HTTPS enforcement in-app.
- **Default admin:** `admin@medicaps.ac.in` / `admin123` (seeded by `seed.py`).
- **DB:** SQLite dev / MySQL prod, switched by `DATABASE_URL`; `run.py` auto-creates the MySQL database and seeds data on every startup.
- **Frontend:** Jinja2 templates, vanilla JS, CSS custom properties for theming (light/dark), Chart.js + Lucide via CDN — no SPA framework.

---

## 22. Cheat Sheet

### Architecture (one line)
`Browser → Flask (Blueprints) → Services → SQLAlchemy Models → SQLite/MySQL`, with local-disk image storage and optional Google OAuth.

### Database (6 tables)
```
users ──1:M── products ──1:M── product_images
  │                │
  └──M:M(wishlists)┘
  │
  └──1:M── reports ──M:1── products
categories ──1:M── products
```

### Key API surface

| Feature | Route(s) | Method |
|---|---|---|
| Register/Login/Logout | `/auth/register`, `/auth/login`, `/auth/logout` | GET/POST, GET/POST, GET |
| Google OAuth | `/auth/google/callback` | GET |
| Browse/Search | `/`, `/explore` | GET |
| Listing CRUD | `/p/create`, `/p/<id>`, `/p/<id>/edit`, `/p/<id>/status`, `/p/<id>/delete` | GET/POST |
| Wishlist | `/wishlist/`, `/wishlist/toggle/<id>` | GET, POST(AJAX/JSON) |
| Profile | `/profile/<id>`, `/profile/edit`, `/profile/settings`, `/profile/delete` | GET, GET/POST, GET/POST, POST |
| Dashboard | `/dashboard/` | GET |
| Admin | `/admin/`, `/admin/users`, `/admin/listings`, `/admin/reports` (+ action sub-routes) | GET/POST |

### Tech stack in one breath
Flask 3 + Flask-SQLAlchemy + Flask-Login + Flask-Dance (optional OAuth) + Pillow + SQLite/MySQL + Jinja2 + vanilla JS + Chart.js + Lucide icons.

### Features at a glance
Campus-gated auth · Listings (sale/exchange) · Multi-image upload with WebP processing · Category browsing · Advanced filtered search + pagination · AJAX wishlist · Seller analytics dashboard · Public profiles · Persisted dark mode · Admin moderation (ban/delete/dismiss).

### Important functions, quick index
`create_app()` → app/__init__.py | `initialize_database()` → run.py | `seed_categories()` → seed.py | `AuthService.*` → auth_service.py | `ProductService.*` → product_service.py | `ImageService.process_and_save_product_image()` → image_service.py | `AnalyticsService.get_seller_stats()` → analytics_service.py | `admin_required` → decorators.py | `is_valid_campus_email` / `validate_password_strength` → validators.py

### Top 5 "gotcha" questions to have crisp answers for
1. Is there CSRF protection? → **No**, acknowledged in-code, fixable with Flask-WTF.
2. Is the dashboard chart real data? → **No**, hardcoded demo array.
3. Can users actually report a listing? → **No** route exists for that, even though admin-side review is fully built.
4. Does "Contact Seller" work? → **No**, it's a dead button — no handler at all.
5. Is Flask-Migrate actually used? → **No** — it's mentioned in the README but not in `requirements.txt`; schema is created via `db.create_all()` only.

---

*This guide reflects the state of the MediCart codebase as analyzed on 2026-07-27. Every claim above is traceable to a specific file in `app/`, `run.py`, or `seed.py`.*
