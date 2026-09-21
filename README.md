# Qiora for Students

A pay-to-access online learning marketplace for students in Uganda, open to lecturers and teachers of every subject. Students register, pick a
course, pay with MTN MoMo / Airtel Money / card (via Pesapal), get unlocked automatically,
watch protected video, download notes, take quizzes and earn certificates. It installs on a
phone as an app (PWA) and lessons can be saved for offline study.

## What it does

| Area | Features |
|---|---|
| Students | Sign up, browse and search courses, free preview lessons, pay, watch, download notes, quizzes, certificates (print / save as PDF), reviews, "My account" page |
| Teachers | Add / edit / delete courses and lessons, upload video and PDF notes, build quizzes, see paying students and quiz results |
| Admins | Dashboard (courses, paying students, revenue, pending payments), approve payments by hand, block students, edit site settings in `/django-admin/` |
| Security | Videos and notes live outside any public URL and are served only through permission-checked views (with HTTP Range support for seeking); expired or unpaid access is refused on every request; blocked users are logged out immediately |
| Mobile | Installable PWA, offline page, "Download for offline" per lesson |

## Run it on your computer

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
copy .env.example .env            # then set a real SECRET_KEY
python manage.py migrate
python manage.py createsuperuser  # a superuser is a full admin
python manage.py runserver
python manage.py test core        # 49 tests covering every flow
```

## Payments

**Manual mobile money (works with no setup keys).** In `/django-admin/`, open Site settings and
enter your MTN / Airtel number. At checkout students see the number, send the money, and
enter the transaction ID from their confirmation SMS. The payment appears at the top of the
Payments page (admin menu) with the ID and phone; check it against your MoMo statement and press
**Approve** (unlocks the course) or **Reject**. Each transaction ID can only be used once.

**Automatic (Pesapal).** When the three `PESAPAL_*` values below are set, an online button
appears at checkout as well.

### Pesapal setup

1. Create a merchant account at https://developer.pesapal.com (sandbox first).
2. Put `PESAPAL_CONSUMER_KEY` and `PESAPAL_CONSUMER_SECRET` in `.env`.
3. Pesapal must reach your site over public HTTPS. Locally use an ngrok tunnel and set `SITE_URL`.
4. Run `python manage.py register_ipn` once and copy the printed id into `PESAPAL_IPN_ID`.
5. For real money set `PESAPAL_ENV=live` with your live keys and re-run step 4.

If a student pays informally, an admin can approve the payment from the Payments page.

## Deploy on Vercel + Supabase

Vercel runs the site; Supabase Postgres stores the data.

1. Supabase: Connect, then **Transaction pooler** string (port `6543`). Use a password with
   letters and numbers only.
2. Create the tables once from your computer:
   ```
   set DATABASE_URL=postgresql://postgres.<ref>:<password>@<pooler-host>:5432/postgres
   python manage.py migrate
   python manage.py createsuperuser
   ```
3. In Vercel, Settings, Environment Variables:
   `DATABASE_URL` (same string but port `6543`), `SECRET_KEY` (long random text), `DEBUG=False`.
   Add the `PESAPAL_*` and `SITE_URL` values when you take payments.
4. Deploy this repo, and **redeploy after changing any variable**.
5. Open `/healthz/` on your site. It names the problem in one line
   (`DATABASE_URL_NOT_SET`, `DB_PASSWORD_WRONG`, `TABLES_MISSING`, `DB_UNREACHABLE`, or `ok`).

### Limits on Vercel

Vercel has no permanent disk, so uploaded videos, notes, thumbnails and logos cannot be saved
there (the upload pages show a clear message instead of crashing), and a function cannot stream
large video anyway. Vercel is fine for the pages, sign-in, courses and payments. For paid video
online use a host with a disk (Railway, Render, a VPS) or move video to cloud storage such as
Cloudflare R2 or Supabase Storage.

## Pricing model

`Course.price` is per course; `Course.access_days` makes access time-limited.

| Plan | Setup |
|---|---|
| One course | price = 30000, access days blank (lifetime) |
| Full term | price = 150000, access days = 90 |
| Monthly | price = 50000, access days = 30 |
| Free course | price = 0 (students are enrolled directly) |

## Not built yet

- Cloud file storage (needed for uploads on Vercel; see above).
- Password reset by email (needs an email provider).
- A public "apply to teach" form. Teacher accounts are created by an admin by setting the
  user's role to `teacher` in `/django-admin/`.
