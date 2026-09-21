from django.db import migrations, models

LEGACY = ['legal_writing', 'moot_court', 'case_law', 'constitutional', 'contract', 'criminal', 'research',
          'bar_prep', 'human_rights', 'adr', 'internship', 'international', 'family_land']


def merge_into_law(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    Course.objects.filter(category__in=LEGACY).update(category='law')


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0004_alter_course_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='category',
            field=models.CharField(blank=True, choices=[('business', 'Business & Entrepreneurship'), ('finance', 'Accounting & Finance'), ('technology', 'Technology & Programming'), ('data', 'Data & Analytics'), ('science', 'Science & Mathematics'), ('health', 'Health & Medicine'), ('engineering', 'Engineering'), ('education', 'Education & Teaching'), ('arts_design', 'Arts & Design'), ('languages', 'Languages & Communication'), ('agriculture', 'Agriculture'), ('career', 'Career & Personal Growth'), ('law', 'Law'), ('other', 'Other')], max_length=20),
        ),
        migrations.RunPython(merge_into_law, migrations.RunPython.noop),
    ]
