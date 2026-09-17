# Qiora for Law Students — Pay-to-Access Online Studying System

A Django rebuild of the flow you sketched: register, pick a course, pay via MTN MoMo /
Airtel Money / card through Pesapal, get auto-unlocked, watch protected video, do a
quiz, earn a certificate. Built for reselling to schools / law faculties in Uganda.

## What's inside

- **accounts** — custom `User` with `role` (admin/teacher/student), `phone` (for mobile
  money), `is_blocked` (admin can lock a student out from `/django-admin/`).
- **courses** — `Course`, `Lesson`. This is where the paywall actually lives:
  `courses/views.py`'s `_has_access()` is the one function every locked view checks.
- **payments** — `Enrollment` (is_paid + expiry), `Payment`, and
  `payments/services/pesapal.py`, the Pesapal API v3 integration.
- **quizzes** — `Quiz`, `Question`, `QuizAttempt`.
- **certificates** — auto-issued when a quiz is passed.
- **reviews** — one review per paid student per course.
- **core** — homepage, shared `SiteSettings` (momo number, logo) editable from
  `/django-admin/`.

## The security trick you asked about

Lesson videos and notes are stored in `PROTECTED_MEDIA_ROOT` (`protected_media/`), which
is **never** wired into a public URL (see `onlineschool/urls.py` — only `MEDIA_ROOT` is
served). The only way to read a lesson file is `courses/views.stream_video` /
`download_notes`, which call `_has_access(user, lesson)` on every single request before
opening the file. `stream_video` also implements HTTP Range requests by hand, so the
`<video>` tag can seek — a plain `FileResponse` would work but breaks seeking on long
videos.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env          # then edit .env: set a real SECRET_KEY

python manage.py migrate
python manage.py createsuperuser   # this account is full admin regardless of `role`
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. Log into `/django-admin/` with your superuser to:

- Edit **Site settings** (momo number shown in the footer, site name, logo).
- Add a **Course** (title, price, `access_days` — leave blank for lifetime, or e.g. `30`
  for "monthly access", `90` for "full term") and its **Lessons** inline (upload a video
  file and/or notes PDF right there, or use the nicer "Add Course" / "Manage Lessons"
  pages once logged in as admin/teacher on the site itself).
- Create **Teacher** accounts (students self-register at `/accounts/register/`; teacher
  accounts are created by you, either in `/django-admin/` by setting `role=teacher`, or
  by making a normal account then editing its role).
- Mark one lesson per course `free_preview=True` if you want a free taste before paying.

## Wiring up Pesapal (MTN MoMo / Airtel / Visa / Mastercard)

1. Create a merchant account at https://developer.pesapal.com and grab your **sandbox**
   consumer key + secret first (test with fake money before going live).
2. Put them in `.env`:
   ```
   PESAPAL_ENV=sandbox
   PESAPAL_CONSUMER_KEY=...
   PESAPAL_CONSUMER_SECRET=...
   ```
3. Pesapal needs a **publicly reachable** URL to send payment notifications to — your
   laptop's `127.0.0.1` doesn't count. For local testing, run an ngrok tunnel:
   ```bash
   ngrok http 8000
   ```
   Copy the `https://...ngrok-free.app` URL into `.env` as `SITE_URL`.
4. Register your IPN endpoint (one-time, run again if the URL ever changes):
   ```bash
   python manage.py register_ipn
   ```
   Copy the printed `ipn_id` into `.env` as `PESAPAL_IPN_ID`, then restart the server.
5. Add a phone number to your test student account (via `/django-admin/` for now — a
   "my account" page to self-edit phone is a natural next feature to add), then go
   through Course → Checkout → "Pay with MTN MoMo / Airtel Money / Card". Pesapal's
   sandbox lets you simulate a successful or failed mobile money payment.
6. When you're ready to charge real money: set `PESAPAL_ENV=live`, swap in your live
   consumer key/secret, re-run `register_ipn` against your real domain, and update
   `SITE_URL`.

If a student pays you informally (sends momo directly and messages you), an admin can
also **manually approve** a pending payment from the "Payments" page in the site nav —
that flips `is_paid` the same way a real Pesapal callback would.

## Going live (selling this to a school)

- Switch `DATABASES` in `onlineschool/settings.py` from SQLite to Postgres/MySQL for
  anything beyond a single-school pilot.
- Set `DEBUG=False`, fill in `ALLOWED_HOSTS`, and serve `protected_media/` and
  `media/` from disk on the server that runs Django (not from a separate static host —
  the whole point is that only Django's permission-checked views can read
  `protected_media/`).
- Run behind gunicorn/uwsgi + nginx, or a PaaS that supports a persistent Python
  process (this is the tradeoff you accepted picking Django over plain PHP — it needs
  a real app server, not bargain-bin shared hosting).
- Back up `db.sqlite3` (or your Postgres DB) and `protected_media/` together — losing
  either one independently corrupts the "who paid for what" picture.

## Pricing model

`Course.price` is per-course. `Course.access_days` makes it time-boxed:

| What you called it | How to set it up |
|---|---|
| 1 course = 30k | price=30000, access_days=blank (lifetime) |
| Full term = 150k | make a bundle "course" per term at price=150000, access_days=90 |
| Monthly access = 50k | price=50000, access_days=30 |

## Not built yet (natural next steps)

- A student "edit my phone number" page (right now that's admin-only via
  `/django-admin/`; the checkout view intentionally blocks payment without a phone
  number, since Pesapal needs one).
- Course search/filter and category tagging, if your catalog grows past a browsable
  single page.
- Automatic certificate PDF download (right now `certificates/certificate.html` is a
  print-friendly page, not a generated PDF file).
