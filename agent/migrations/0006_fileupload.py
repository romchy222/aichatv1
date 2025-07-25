# Generated by Django 5.2.4 on 2025-07-19 19:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agent', '0005_contentfilter_moderationlog'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUpload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='uploads/%Y/%m/%d/')),
                ('original_filename', models.CharField(max_length=255)),
                ('file_type', models.CharField(choices=[('image', 'Изображение'), ('document', 'Документ'), ('spreadsheet', 'Таблица'), ('pdf', 'PDF'), ('text', 'Текстовый файл'), ('other', 'Другое')], default='other', max_length=20)),
                ('file_size', models.BigIntegerField()),
                ('mime_type', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(choices=[('pending', 'Ожидает обработки'), ('processing', 'Обрабатывается'), ('completed', 'Обработан'), ('failed', 'Ошибка')], default='pending', max_length=20)),
                ('extracted_text', models.TextField(blank=True, help_text='Извлеченный из файла текст')),
                ('analysis_result', models.JSONField(blank=True, help_text='Результат анализа файла', null=True)),
                ('session_id', models.CharField(blank=True, max_length=100, null=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'File Upload',
                'verbose_name_plural': 'File Uploads',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
