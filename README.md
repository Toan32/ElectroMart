# ElectroMart - Storefront Module

eProject (FPT Aptech) - an online store for electronic components, built with
**Django + MongoDB**. This repository currently contains the **Storefront
module** owned by **Toan**: home page, product listing with a dynamic
specification filter, search, product detail, comparison and wishlist.

The other three modules (Sales by Tin, Account & B2B by Loc, Admin catalogue &
Interaction by Minh) plug into the same database and are developed separately.

---

## Folder layout

```
ProjectHK2/
├── Backend/                 Django project and application code
│   ├── manage.py
│   ├── electromart/         settings, URL routing, WSGI entry point
│   └── catalogue/           storefront application
│       ├── db.py            MongoDB connection
│       ├── repo.py          queries: dynamic filter, facet counts, search
│       ├── views.py         request handlers
│       ├── context_processors.py
│       └── templatetags/em_extras.py
│
├── Frontend/                everything the browser receives
│   ├── templates/           Django templates (base, home, listing, detail...)
│   └── static/
│       ├── css/style.css
│       └── js/app.js        type-ahead search, compare, wishlist
│
├── Database/
│   └── seed_data.py         collections, indexes and sample data
│
├── requirements.txt
└── .env.example
```

`Backend/electromart/settings.py` points `TEMPLATES.DIRS` and
`STATICFILES_DIRS` at the `Frontend/` folder, so the three folders stay
independent while still running as one Django project.

---

## Requirements

| Component | Version |
|-----------|---------|
| Python    | 3.12 or newer |
| Django    | 5.2 or newer (tested on 6.0) |
| MongoDB   | 8.x, running on `localhost:27017` |
| pymongo   | 4.8 or newer |

---

## Setup

```bash
# 1. Install the Python packages
pip install -r requirements.txt

# 2. Make sure MongoDB is running, then create the sample data
python Database/seed_data.py

# 3. Start the development server
cd Backend
python manage.py runserver
```

Open <http://127.0.0.1:8000/>.

Connection settings are read from the environment; copy `.env.example` to
`.env` and export the values, or keep the defaults for local development:

```
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=electromart_db
```

---

## Pages

| URL | Purpose |
|-----|---------|
| `/` | Home: category menu, banner, featured / best selling / new arrivals |
| `/category/<slug>/` | Product listing with the dynamic specification filter |
| `/product/<slug>/` | Product detail: specifications, quantity pricing, related items |
| `/search/?q=` | Full-text search results |
| `/api/suggest/?q=` | JSON endpoint for the type-ahead dropdown |
| `/compare/` | Side-by-side comparison of up to 4 products |
| `/wishlist/` | Saved products |

---

## The dynamic specification filter

This is the feature the whole project is built around, and the reason MongoDB
was chosen over a relational database.

Every category document carries its own `spec_template`:

```json
{
  "name": "Microcontrollers & Kits",
  "spec_template": [
    { "key": "clock_speed_mhz", "label": "Clock speed", "data_type": "number",
      "unit": "MHz", "is_filterable": true, "display_order": 2 },
    { "key": "core", "label": "Core", "data_type": "select",
      "allowed_values": ["ARM Cortex-M0", "Xtensa LX6", "RISC-V"],
      "is_filterable": true, "display_order": 1 }
  ]
}
```

Products in that category store matching values in a free-form sub-document:

```json
{ "specifications": { "core": "Xtensa LX6", "clock_speed_mhz": 240,
                      "flash_kb": 4096, "wifi": true } }
```

At request time `repo.spec_conditions()` reads the template, validates the query
string against it and builds a MongoDB query with dotted paths such as
`specifications.clock_speed_mhz: { $gte: 160 }`. The filter panel in the sidebar
is rendered from the same template, so **adding a category with a completely new
set of parameters requires no code change** - only a new document.

`repo.facet_counts()` then runs a single `$facet` aggregation that counts, for
every option, how many products would remain. For a given field the count
applies all the other active conditions but drops that field's own condition,
which is why sibling options stay visible instead of collapsing to the one
already selected.

Indexes that make this practical (created in `Database/seed_data.py`):

| Index | Why |
|-------|-----|
| `{ "specifications.$**": 1 }` wildcard | each category uses different keys, they cannot be listed in advance |
| `{ category_id, is_hidden, min_price }` compound | the listing query and its default sort |
| text index on name / part number / description / tags | search and type-ahead |

---

## Notes

- The project talks to MongoDB through **pymongo** rather than the Django ORM.
  `django-mongodb-backend` does not yet support Django 6, and the filter needs
  raw aggregation features (`$facet`, dotted paths, wildcard indexes) anyway.
- Because the ORM is unused, `DATABASES` is empty and sessions are stored in
  signed cookies, so no relational database has to be created.
- Compare and wishlist are kept in the session; they will move to the `users`
  collection once the Account module is merged in.
- Product images are placeholders. Replace `card-img` / `big-img` in the
  templates once real photos are available in `media/`.
