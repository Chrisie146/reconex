# Environment Configuration Guide

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Generate a secure SECRET_KEY:**
   ```bash
   # Using OpenSSL:
   openssl rand -hex 32

   # Or using Python:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Update `.env` file with your values:**
   - Set `SECRET_KEY` to the generated value
   - Update `DATABASE_URL` if not using SQLite
   - Configure `ALLOWED_ORIGINS` for your frontend URL(s)
   - Set `ENVIRONMENT=production` when deploying

## Environment Variables

### Required

- **SECRET_KEY**: JWT signing key (minimum 32 characters)
  - ⚠️ **CRITICAL**: Must be set to a strong random value in production
  - Can be auto-generated in development (with warning)

### Optional (with defaults)

- **ENVIRONMENT**: `development` | `staging` | `production`
  - Default: `development`
  - Affects validation strictness and logging

- **DEBUG**: `True` | `False`
  - Default: `True`
  - Set to `False` in production

- **DATABASE_URL**: Database connection string
  - Default: `sqlite:///./statement_analyzer.db`
  - Examples:
    - SQLite: `sqlite:///./database.db`
    - PostgreSQL: `postgresql://user:pass@localhost:5432/dbname`
    - MySQL: `mysql+pymysql://user:pass@localhost:3306/dbname`

- **ALLOWED_ORIGINS**: Comma-separated CORS origins
  - Default: `http://localhost:3000,http://localhost:8000`
  - Production: Your actual domain(s)

- **ACCESS_TOKEN_EXPIRE_MINUTES**: JWT token lifetime
  - Default: `10080` (7 days)

- **API_HOST**: Server bind address
  - Default: `0.0.0.0`

- **API_PORT**: Server port
  - Default: `8000`

- **LOG_LEVEL**: Logging verbosity
  - Default: `DEBUG` in development, `INFO` in production
  - Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

- **MAX_UPLOAD_SIZE_MB**: Maximum file upload size
  - Default: `50`

## Configuration Validation

The application validates configuration on startup:

### ✅ Production Checks
- SECRET_KEY must be set and strong (32+ characters)
- SECRET_KEY must not be a default/example value
- DATABASE_URL must not contain "EXAMPLE"

### ⚠️ Development Warnings
- Weak SECRET_KEY generates a warning (auto-generated if missing)
- Short SECRET_KEY triggers a warning
- Localhost in CORS in production triggers a warning

## Examples

### Development (.env)
```bash
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=dev-secret-key-replace-in-production-12345678
DATABASE_URL=sqlite:///./statement_analyzer.db
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
LOG_LEVEL=DEBUG
```

### Production (.env)
```bash
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<your-secure-random-key-generated-with-openssl>
DATABASE_URL=postgresql://username:password@db-host:5432/statement_db
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
LOG_LEVEL=INFO
ACCESS_TOKEN_EXPIRE_MINUTES=10080
MAX_UPLOAD_SIZE_MB=50
```

## Troubleshooting

### "SECRET_KEY environment variable must be set in production"
Generate a secure key and add to `.env`:
```bash
openssl rand -hex 32
```

### "Configuration validation failed"
Check the error messages in the logs. Common issues:
- Missing or weak SECRET_KEY
- Invalid DATABASE_URL
- Incorrect environment variable format

### Database connection errors
- Verify DATABASE_URL is correct
- For PostgreSQL/MySQL, ensure the database exists
- Check permissions and credentials

## Security Best Practices

1. **Never commit `.env` to version control**
   - `.env` is in `.gitignore`
   - Only commit `.env.example`

2. **Use strong, unique SECRET_KEY**
   - Generate with cryptographically secure method
   - Never reuse across environments
   - Rotate periodically

3. **Restrict CORS origins**
   - List only your actual frontend URLs
   - Never use `*` in production

4. **Use environment-appropriate settings**
   - `DEBUG=False` in production
   - Appropriate LOG_LEVEL for each environment
   - Secure DATABASE_URL with strong credentials

5. **Secure database credentials**
   - Use environment variables
   - Rotate credentials regularly
   - Use least-privilege access

## Migration from Old Config

If upgrading from an older version:

1. The old `config.py` with pydantic has been replaced
2. Configuration now uses plain environment variables
3. Copy `.env.example` to `.env` and update values
4. Remove any hardcoded configuration values
5. Update SECRET_KEY to a new secure value

The new config system is backward compatible with code that imports from `config.py`.
