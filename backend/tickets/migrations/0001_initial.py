from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Ticket",
            fields=[
                ("ticket_id", models.CharField(max_length=128, primary_key=True, serialize=False)),
                ("channel", models.CharField(blank=True, max_length=32, null=True)),
                ("locale", models.CharField(blank=True, max_length=16, null=True)),
                ("message", models.TextField()),
                ("case_type", models.CharField(blank=True, max_length=64, null=True)),
                ("severity", models.CharField(blank=True, max_length=16, null=True)),
                ("department", models.CharField(blank=True, max_length=64, null=True)),
                ("agent_summary", models.TextField(blank=True, null=True)),
                ("human_review_required", models.BooleanField(blank=True, null=True)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "tickets"},
        ),
    ]