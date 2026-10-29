# Masjid Connect Backend API

A modern, production-ready FastAPI backend with comprehensive health monitoring, structured logging, and enterprise-grade error handling.

---

## 🚀 Quick Start

```powershell
# 1. Activate virtual environment
..\.venv\Scripts\Activate.ps1

# 2. Run application
fastapi dev .\src\main.py

# 3. Run tests
.\run-tests.ps1

# 4. View API docs
# Open browser: http://localhost:8000/docs
```

---

## 📚 Documentation

### 👉 **New to the project? START HERE:**

1. **[GUIDELINES.md](GUIDELINES.md)** - Project guidelines summary (⭐ START HERE)
2. **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Cheat sheets and common patterns
3. **[docs/README.md](docs/README.md)** - Complete project documentation

### 📖 Essential Reading

#### For Developers

- **[GUIDELINES.md](GUIDELINES.md)** - Quick summary of all standards
- **[docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - Fast lookup, cheat sheets
- **[docs/CODING_GUIDELINES.md](docs/CODING_GUIDELINES.md)** - Complete coding standards
- **[docs/STRUCTURE.md](docs/STRUCTURE.md)** - Project organization

#### For Specification Writers

- **[docs/SPECIFICATION_GUIDELINES.md](docs/SPECIFICATION_GUIDELINES.md)** - How to write specs
- **[specifications/README.md](specifications/README.md)** - Spec index and templates
- **[docs/CODING_GUIDELINES.md](docs/CODING_GUIDELINES.md)** - Standards to incorporate

#### Technical References

- **[docs/API.md](docs/API.md)** - API endpoints and contracts
- **[docs/DATABASE.md](docs/DATABASE.md)** - Database schema and patterns
- **[docs/DATABASE_QUICKSTART.md](docs/DATABASE_QUICKSTART.md)** - Quick database setup
- **[README-TESTING.md](README-TESTING.md)** - Testing guide

#### Implementation Details

- **[GUIDELINES_IMPLEMENTATION.md](GUIDELINES_IMPLEMENTATION.md)** - Guidelines implementation summary
- **[docs/GUIDELINES_STRUCTURE.md](docs/GUIDELINES_STRUCTURE.md)** - Documentation structure
- **[.github/copilot-instructions.md](.github/copilot-instructions.md)** - Auto-enforcement rules

---

## ⚡ Quick Reference

### Naming Conventions

```python
# Files & Modules
database_engine.py              # lowercase_with_underscores

# Classes
class DatabaseEngine:           # PascalCase
class CreateUserRequest:        # PascalCase + Request
class UserResponse:             # PascalCase + Response

# Functions
def get_user_by_id():          # lowercase_with_underscores
async def fetch_data():        # async too

# Constants
MAX_RETRY_ATTEMPTS = 3         # UPPERCASE_WITH_UNDERSCORES

# API Paths
/api/v1/users                  # lowercase-with-hyphens
/api/v1/country-codes          # plural nouns

# JSON Properties (Pydantic alias)
Field(..., alias="userId")     # camelCase in JSON responses
```

### Exception Handling

```python
from src.core.exceptions import NotFoundError, ValidationError

# 404 - Resource not found
raise NotFoundError(f"User {user_id} not found")

# 400 - Invalid input
raise ValidationError("Invalid email format")

# 409 - Duplicate
raise ConflictError("Email already exists")
```

### Logging

```python
import logging
logger = logging.getLogger(__name__)

# INFO - Success
logger.info("User created", extra={"user_id": user.id})

# ERROR - Failure
logger.error(f"Failed: {e}", extra={"data": data})

# ⚠️ NEVER log passwords, tokens, or PII!
```

**📖 See [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) for complete cheat sheets**

---

## 🎯 Project Standards

All code must follow these standards:

✅ **Naming:** snake_case functions, PascalCase classes, UPPERCASE constants  
✅ **Types:** Type hints required on all functions  
✅ **Docs:** Docstrings required on all public functions/classes  
✅ **Errors:** Use custom exceptions (NotFoundError, ValidationError, etc.)  
✅ **Logging:** Structured JSON with correlation IDs  
✅ **Security:** Never log sensitive data, validate all inputs  
✅ **Testing:** ≥80% coverage (≥90% for new features)  
✅ **Style:** PEP 8 compliant

**📖 Complete standards: [docs/CODING_GUIDELINES.md](docs/CODING_GUIDELINES.md)**

---

## 📁 Project Structure

```
backend-api/
├── GUIDELINES.md                    ⭐ START HERE
├── README.md                        📖 This file
├── README-TESTING.md                🧪 Testing guide
│
├── .github/
│   └── copilot-instructions.md     🤖 Auto-enforce standards
│
├── docs/
│   ├── QUICK_REFERENCE.md          ⚡ Fast lookup
│   ├── CODING_GUIDELINES.md        📘 Complete standards
│   ├── SPECIFICATION_GUIDELINES.md 📗 Spec writing
│   ├── STRUCTURE.md                🏗️  Organization
│   ├── API.md                      🔌 API docs
│   └── DATABASE.md                 💾 Database docs
│
├── specifications/
│   └── README.md                   📑 Spec index
│
├── src/
│   ├── api/                        🌐 API endpoints
│   ├── core/                       🔧 Core utilities
│   ├── database/                   💾 Database layer
│   ├── models/                     📋 Pydantic models
│   └── main.py                     🚀 Entry point
│
└── tests/
    ├── unit/                       🧪 Unit tests
    ├── integration/                🔗 Integration tests
    └── contract/                   📜 Contract tests
```

**📖 Detailed structure: [docs/STRUCTURE.md](docs/STRUCTURE.md)**

---

## 🛠️ Development

### Prerequisites

- Python 3.11+
- Virtual environment at `../.venv/`
- SQL Server (local or Azure)

### Setup

```powershell
# 1. Activate environment
..\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment (optional)
cp .env.example .env

# 4. Run application
fastapi dev .\src\main.py
```

### Testing

```powershell
# Run all tests
.\run-tests.ps1

# Run with coverage
.\run-tests.ps1 -Coverage

# Run specific tests
.\run-tests.ps1 tests/unit/
```

**📖 Testing guide: [README-TESTING.md](README-TESTING.md)**

---

## 📝 Contributing

### Workflow

1. **Review Guidelines**

   - Read [GUIDELINES.md](GUIDELINES.md)
   - Review [docs/CODING_GUIDELINES.md](docs/CODING_GUIDELINES.md)

2. **For New Features**

   - Write spec using [docs/SPECIFICATION_GUIDELINES.md](docs/SPECIFICATION_GUIDELINES.md)
   - Get approval

3. **Implement**

   - Follow coding standards
   - Include type hints and docstrings
   - Add structured logging
   - Use custom exceptions

4. **Test**

   - Write unit tests
   - Write integration tests
   - Ensure ≥80% coverage (≥90% for new)

5. **Document**

   - Update API docs
   - Update README if needed
   - Complete docstrings

6. **Submit**
   - Create pull request
   - Use checklist from guidelines

### Pre-Commit Checklist

- [ ] Follows naming conventions
- [ ] Has type hints
- [ ] Has docstrings
- [ ] Uses custom exceptions
- [ ] Includes logging
- [ ] No sensitive data exposed
- [ ] Tests passing (≥80% coverage)
- [ ] Documentation updated

**📖 Complete workflow: [docs/README.md § Contributing](docs/README.md#contributing)**

---

## 🔗 Key Links

### Documentation

- [GUIDELINES.md](GUIDELINES.md) - Start here
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Daily reference
- [docs/CODING_GUIDELINES.md](docs/CODING_GUIDELINES.md) - Complete standards
- [docs/README.md](docs/README.md) - Full documentation

### API

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health Check: http://localhost:8000/api/v1/health
- Build Version: http://localhost:8000/api/v1/build 🆕

### Repository

- GitHub: https://github.com/baigmm1/mmc-application
- Branch: add-azure-sql-support

---

## 🆘 Need Help?

### Common Questions

**Q: Where do I start?**  
A: Read [GUIDELINES.md](GUIDELINES.md) or [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)

**Q: How do I name my function?**  
A: `snake_case` - see [docs/QUICK_REFERENCE.md § Naming](docs/QUICK_REFERENCE.md)

**Q: Which exception should I use?**  
A: See [docs/QUICK_REFERENCE.md § Exceptions](docs/QUICK_REFERENCE.md)

**Q: What logging level?**  
A: See [docs/QUICK_REFERENCE.md § Logging](docs/QUICK_REFERENCE.md)

**Q: How do I run tests?**  
A: `.\run-tests.ps1` - see [README-TESTING.md](README-TESTING.md)

**Q: What test coverage is required?**  
A: 80% minimum, 90% for new features

---

## 📊 Features

- ✅ FastAPI framework (async Python)
- ✅ Azure SQL Database integration
- ✅ Health monitoring endpoints
- ✅ **Build version tracking with auto-increment** 🆕
- ✅ Structured JSON logging with correlation IDs
- ✅ Comprehensive error handling
- ✅ Security headers (OWASP)
- ✅ OpenAPI documentation
- ✅ Request validation (Pydantic)
- ✅ CORS support
- ✅ Environment configuration
- ✅ Comprehensive test suite (100+ tests)
- ✅ Complete coding guidelines
- ✅ Specification templates

**📖 Build Version System:** [BUILD_VERSION_README.md](BUILD_VERSION_README.md)

---

## 📦 Tech Stack

- **Framework:** FastAPI 0.104+
- **Language:** Python 3.11+
- **Database:** Azure SQL Server
- **ORM:** SQLAlchemy (async)
- **Validation:** Pydantic v2
- **Testing:** pytest + pytest-asyncio
- **Logging:** structlog + python-json-logger
- **Database Driver:** aioodbc + pyodbc

---

## 📄 License

[License information to be added]

---

## 🎉 Quick Win

Get started in 3 minutes:

```powershell
# 1. Activate & Run
..\.venv\Scripts\Activate.ps1
fastapi dev .\src\main.py

# 2. Test
.\run-tests.ps1

# 3. View Docs
# Browser: http://localhost:8000/docs
```

**Read [GUIDELINES.md](GUIDELINES.md) before contributing!**

---

**Last Updated:** December 8, 2025  
**Version:** 1.0  
**Status:** ✅ Production Ready

**Quick Access:** [Guidelines](GUIDELINES.md) | [Quick Ref](docs/QUICK_REFERENCE.md) | [Coding Standards](docs/CODING_GUIDELINES.md) | [Spec Guidelines](docs/SPECIFICATION_GUIDELINES.md)
