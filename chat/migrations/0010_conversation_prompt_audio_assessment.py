# Generated by Django 4.2 on 2023-09-02 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0009_topic_custom_context"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="prompt_audio_assessment",
            field=models.TextField(blank=True),
        ),
    ]