# Database Migrations Guide

## Initial Setup

When setting up the project for the first time, run migrations:

```bash
# Using Docker
docker-compose exec app python manage.py migrate

# Or locally
python manage.py migrate
```

## Migration Status

Check migration status:

```bash
python manage.py showmigrations
```

## Creating Migrations

Migrations are automatically detected when models change. To create migrations:

```bash
# For all apps
python manage.py makemigrations

# For specific app
python manage.py makemigrations brands
```

## Important Notes

### CheckConstraint with Length Lookup

The `Brand` model has a `prefix_length_valid` constraint that uses raw SQL in the migration because Django's `CheckConstraint` doesn't support the `length` lookup for `CharField`.

The constraint is defined in `brands/migrations/0001_initial.py` using `RunSQL`:

```python
migrations.RunSQL(
    sql="ALTER TABLE brands ADD CONSTRAINT prefix_length_valid CHECK (LENGTH(prefix) >= 2 AND LENGTH(prefix) <= 10);",
    reverse_sql="ALTER TABLE brands DROP CONSTRAINT IF EXISTS prefix_length_valid;",
)
```

Validation is also enforced in the model's `clean()` method for application-level validation.

### Migration Dependencies

Migration dependencies are automatically handled:
- `products` depends on `brands`
- `licenses` depends on `brands` and `products`
- `activations` depends on `licenses`

## Troubleshooting

### "relation does not exist" Error

If you see errors like `relation "brands" does not exist`:

1. Check if migrations exist:
   ```bash
   ls brands/migrations/
   ```

2. Create migrations if missing:
   ```bash
   python manage.py makemigrations
   ```

3. Apply migrations:
   ```bash
   python manage.py migrate
   ```

### "django_content_type.name does not exist" Error

This indicates Django's contenttypes app needs migration:

```bash
python manage.py migrate contenttypes
```

### Tables Already Exist

If tables exist but migrations aren't applied:

```bash
# Fake the initial migrations (use with caution)
python manage.py migrate --fake-initial
```

### Reset Database (Development Only)

⚠️ **WARNING**: This will delete all data!

```bash
# Drop and recreate database
docker-compose down -v
docker-compose up -d db
docker-compose exec app python manage.py migrate
```

## Migration Files

All migration files are version-controlled and should be committed:

- `brands/migrations/0001_initial.py` - Initial brands, API keys, webhooks
- `products/migrations/0001_initial.py` - Initial products
- `licenses/migrations/0001_initial.py` - Initial license keys, licenses, audit logs
- `licenses/migrations/0002_initial.py` - Foreign keys and indexes
- `activations/migrations/0001_initial.py` - Initial activations
- `activations/migrations/0002_initial.py` - Foreign keys and indexes

## Production Considerations

1. **Always backup** before running migrations in production
2. **Test migrations** in staging first
3. **Review migration SQL** using `python manage.py sqlmigrate <app> <migration>`
4. **Use transactions** - migrations run in transactions by default
5. **Monitor** migration execution time for large tables

