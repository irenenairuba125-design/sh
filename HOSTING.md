# How to host Qiora yourself

The app is a standard Django website. Any of these hosts will run it. Vercel is already
connected to your GitHub repo, so it is the quickest.

## A. Vercel + Supabase (already set up)

You only need to give Vercel two settings, then redeploy.

1. vercel.com/dashboard -> open the project that owns your site (the card showing your
   `*.vercel.app` address).
2. Settings -> Environment Variables. Add:

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | Supabase -> Connect -> **Transaction pooler** string (port 6543), with `[YOUR-PASSWORD]` replaced by your real database password (letters and numbers only) |
   | `SECRET_KEY` | any long random text (30+ letters and numbers) |

   Do not paste `.env.example` into Vercel; it holds local-only values.
3. Deployments -> the top row -> the three dots -> **Redeploy**. Wait for "Ready".
4. Open `https://YOUR-SITE.vercel.app/healthz/`. It must say `"status": "ok"`.
   Any other message names the problem (`DATABASE_URL_NOT_SET`, `DB_PASSWORD_WRONG`,
   `TABLES_MISSING`, `DB_UNREACHABLE`).
5. The tables are created once from your computer (already done for the current database):
   ```
   set DATABASE_URL=<Supabase session pooler string, port 5432>
   .venv\Scripts\python manage.py migrate
   .venv\Scripts\python manage.py createsuperuser
   ```

Use only ONE Vercel project for this repo. Extra projects made from the same repo all
redeploy on every push and fail with different errors; delete the spares
(project -> Settings -> bottom of page -> Delete Project).

Vercel cannot store uploaded files, so lesson videos, notes and thumbnails will not save
there. The pages, sign-in, courses and payments all work.

## B. A host with a disk (needed for paid video uploads)

Railway, Render, a VPS, or PythonAnywhere can save uploads.

- Build: `pip install -r requirements.txt`
- Release: `python manage.py migrate`
- Start: `gunicorn onlineschool.wsgi` (add `gunicorn` to requirements.txt)
- Environment: `DATABASE_URL` (or leave unset to use SQLite on a persistent disk),
  `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=your-domain.com`,
  `CSRF_TRUSTED_ORIGINS=https://your-domain.com`
- Keep the `protected_media/` and `media/` folders on the persistent disk and back them up.

## Sharing it with your lecturer

- The GitHub repo is private. Give access with: repo -> Settings -> Collaborators ->
  Add people (their GitHub username).
- Do not share your admin password. In `/django-admin/` -> Users -> Add user, create a
  student (and a teacher) account for them.
- After the demo: reset the Supabase database password and change your admin password,
  then update `DATABASE_URL` in Vercel and redeploy.

## Taking payments

- Manual mobile money works immediately: `/django-admin/` -> Site settings -> enter your
  MTN/Airtel number.
- Automatic payments need your own Pesapal keys (see README.md).
