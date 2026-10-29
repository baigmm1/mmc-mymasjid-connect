# GitHub Copilot Instructions

**Automatic code generation guidelines for this project**

---

## Project Overview

This is the Masjid Connect Backend API, a FastAPI-based microservices application with Azure SQL database integration. All code and specifications must follow established project guidelines.

---

## Mandatory Guidelines

### Before Generating Any Code

1. **Read these documents first:**

   - `docs/CODING_GUIDELINES.md` - Complete coding standards
   - `docs/QUICK_REFERENCE.md` - Common patterns
   - `docs/STRUCTURE.md` - Project organization

2. **Follow these documents for specifications:**
   - `docs/SPECIFICATION_GUIDELINES.md` - How to write specs

---

## Naming Conventions (CRITICAL)

### Python Code

```python
# Modules/Files
database_engine.py              # ✅ lowercase_with_underscores
DatabaseEngine.py               # ❌ Wrong

# Classes
class DatabaseEngine:           # ✅ PascalCase
class CreateUserRequest:        # ✅ PascalCase + Request suffix
class UserResponse:             # ✅ PascalCase + Response suffix

# Functions/Methods
def get_user_by_id():          # ✅ lowercase_with_underscores
async def fetch_data():        # ✅ async functions too
def GetUserById():             # ❌ Wrong

# Constants
MAX_RETRY_ATTEMPTS = 3         # ✅ UPPERCASE_WITH_UNDERSCORES
maxRetryAttempts = 3           # ❌ Wrong

# Private/Internal
def _internal_helper():        # ✅ Prefix with underscore
```

### API Endpoints

```python
# Paths (lowercase-with-hyphens, plural nouns)
/api/v1/users                  # ✅ Correct
/api/v1/country-codes          # ✅ Correct
/api/v1/Users                  # ❌ Wrong: capitalized
/api/v1/getUsers               # ❌ Wrong: includes verb

# Router functions (verb + noun, snake_case)
@router.get("/users")
async def get_users():         # ✅ Correct

@router.post("/users")
async def create_user():       # ✅ Correct
```

### Database Models

```python
# Table names (PascalCase - matches existing schema)
class CountryCode(Base):
    __tablename__ = "CountryCodes"  # ✅ PascalCase

# Column names (PascalCase - matches existing schema)
CountryCode = Column(String(3))     # ✅ PascalCase
CountryName = Column(String(50))    # ✅ PascalCase
```

---

## Code Style Requirements

### Type Hints (REQUIRED)

```python
# ✅ Always include type hints
def get_user(user_id: int) -> UserResponse:
    ...

async def fetch_data(limit: int = 10) -> list[dict[str, Any]]:
    ...

# ❌ Never omit type hints
def get_user(user_id):  # Missing type hints
    ...
```

### Docstrings (REQUIRED)

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two geographic coordinates.

    Uses the Haversine formula to calculate the great-circle distance
    between two points on Earth's surface.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance between points in kilometers

    Raises:
        ValueError: If coordinates are out of valid range

    Example:
        >>> distance = calculate_distance(40.7128, -74.0060, 34.0522, -118.2437)
        >>> print(f"Distance: {distance:.2f} km")
        Distance: 3944.42 km
    """
    # Implementation
```

### Async/Await

```python
# ✅ Use async for I/O operations
async def get_user(user_id: int) -> UserResponse:
    async with session_maker() as session:
        result = await session.execute(query)
        return result.scalar_one_or_none()

# ❌ Don't forget await
async def get_user(user_id: int):
    result = session.execute(query)  # Missing await
```

---

## Error Handling (REQUIRED)

### Use Custom Exceptions

```python
from src.core.exceptions import (
    NotFoundError,
    ValidationError,
    ConflictError,
    MasjidConnectException
)

# ✅ Correct error handling
async def get_user(user_id: int) -> UserResponse:
    """Fetch user by ID."""
    try:
        if user_id < 1:
            raise ValidationError("User ID must be positive")

        async with session_maker() as session:
            query = select(User).where(User.id == user_id)
            result = await session.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                raise NotFoundError(f"User with ID {user_id} not found")

            return UserResponse.model_validate(user)

    except (NotFoundError, ValidationError):
        raise  # Re-raise application exceptions
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise MasjidConnectException(
            detail="Failed to fetch user",
            error_code="DATABASE_ERROR"
        )

# ❌ Don't use generic exceptions
def get_user(user_id: int):
    if not user:
        raise Exception("Error")  # Too vague
```

### Exception Mapping

- `ValidationError` → 400 (Bad Request)
- `AuthenticationError` → 401 (Unauthorized)
- `AuthorizationError` → 403 (Forbidden)
- `NotFoundError` → 404 (Not Found)
- `ConflictError` → 409 (Conflict)
- `MasjidConnectException` → 500 (Internal Server Error)

---

## Logging Requirements

### Logger Setup

```python
import logging

# ✅ Create logger at module level
logger = logging.getLogger(__name__)
```

### Log Levels

```python
# DEBUG - Development diagnostics (not in production)
logger.debug(f"Processing user {user_id}")

# INFO - Successful operations
logger.info(
    "User created successfully",
    extra={"user_id": user.id, "correlation_id": correlation_id}
)

# WARNING - Potential issues
logger.warning(
    "Connection pool 80% full",
    extra={"active": pool.active, "max": pool.size}
)

# ERROR - Failed operations
logger.error(
    f"Failed to create user: {e}",
    extra={"data": data.model_dump(), "correlation_id": correlation_id}
)

# CRITICAL - System failures
logger.critical(f"Database connection failed: {e}", exc_info=True)
```

### Security in Logging

```python
# ❌ NEVER log sensitive data
logger.info(f"User password: {password}")           # WRONG!
logger.debug(f"Auth token: {token}")                # WRONG!
logger.info(f"Credit card: {cc_number}")            # WRONG!

# ✅ DO log operation results
logger.info(
    "User authenticated successfully",
    extra={"user_id": user.id, "correlation_id": correlation_id}
)
```

---

## Pydantic Models

### Request Models

```python
class CreateMasjidRequest(BaseModel):
    """Request model for creating masjid."""

    MasjidName: str = Field(
        ...,
        alias="masjidName",
        min_length=3,
        max_length=100,
        description="Name of the masjid",
        examples=["Masjid Al-Huda"]
    )
    CountryCode: str = Field(
        ...,
        alias="countryCode",
        min_length=3,
        max_length=3,
        pattern="^[A-Z]{3}$",
        description="ISO 3166-1 alpha-3 country code",
        examples=["USA", "CAN"]
    )

    model_config = {"populate_by_name": True}
```

### Response Models

```python
class MasjidResponse(BaseModel):
    """Response schema for masjids."""

    MasjidId: int = Field(..., alias="masjidId", description="Unique identifier")
    MasjidName: str = Field(..., alias="masjidName", description="Name of the masjid")
    CountryCode: str = Field(..., alias="countryCode", description="Country code")

    model_config = {"from_attributes": True, "populate_by_name": True}
```

**Note:** Python attributes use PascalCase (matching database columns), but JSON properties use camelCase via the `alias` parameter.

---

## API Endpoint Pattern

```python
from fastapi import APIRouter, status
from src.models.response import ItemResponse
from src.core.exceptions import NotFoundError

router = APIRouter(prefix="/api/v1/items", tags=["items"])

@router.get(
    "/",
    response_model=list[ItemResponse],
    status_code=status.HTTP_200_OK,
    summary="List all items",
    description="Retrieve a list of all items"
)
async def get_items() -> list[ItemResponse]:
    """
    Retrieve all items.

    Returns:
        List of all items

    Raises:
        HTTPException: If database query fails
    """
    logger.info("Fetching all items")

    try:
        async with session_maker() as session:
            query = select(Item)
            result = await session.execute(query)
            items = result.scalars().all()

        logger.info(f"Retrieved {len(items)} items")
        return [ItemResponse.model_validate(item) for item in items]

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise MasjidConnectException(
            detail="Failed to retrieve items",
            error_code="DATABASE_ERROR"
        )
```

---

## Database Patterns

### SQLAlchemy Models

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Masjid(Base):
    """SQLAlchemy model for Masjids table."""

    __tablename__ = "Masjids"

    MasjidId = Column(Integer, primary_key=True, autoincrement=True)
    MasjidName = Column(String(100), nullable=False)
    CountryCode = Column(String(3), nullable=False)
    CreatedAt = Column(DateTime, nullable=False)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<Masjid(MasjidId={self.MasjidId}, MasjidName='{self.MasjidName}')>"
```

### Query Patterns

```python
# ✅ Use context manager
async def get_masjid(masjid_id: int) -> Masjid | None:
    """Fetch masjid by ID."""
    async with session_maker() as session:
        query = select(Masjid).where(Masjid.MasjidId == masjid_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

# ❌ Don't forget context manager
async def get_masjid(masjid_id: int):
    session = session_maker()
    result = await session.execute(query)
    return result  # Session never closed!
```

---

## Testing Requirements

### Test Naming

```python
# ✅ Descriptive test names
def test_get_user_by_id_returns_user_when_exists():
    ...

def test_get_user_by_id_raises_not_found_when_missing():
    ...

def test_create_user_returns_201_with_valid_data():
    ...

# ❌ Vague test names
def test_user():
    ...

def test_get():
    ...
```

### Test Coverage

- **Minimum:** 80% overall
- **New Features:** 90% before merge
- **Critical Paths:** 100% (auth, security)

---

## Security Requirements

### Input Validation

```python
# ✅ Always validate with Pydantic
class CreateUserRequest(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    password: str = Field(..., min_length=8, max_length=128)
```

### Never Expose Sensitive Data

```python
# ❌ Don't expose internal details
raise Exception(f"SQL Error: {sql_statement}")
raise Exception(f"File: /etc/secrets/key.pem")

# ✅ Use user-friendly messages
raise AuthenticationError("Invalid credentials")
raise NotFoundError("Resource not found")
```

---

## File Organization

```
src/
├── api/v1/endpoints/       # API endpoints
│   └── items.py
├── models/                 # Pydantic models
│   ├── request.py          # Request models
│   └── response.py         # Response models
├── database/models/        # SQLAlchemy models
│   └── item.py
├── core/                   # Core utilities
│   ├── exceptions.py
│   ├── logging.py
│   └── middleware.py
└── services/              # Business logic
    └── item_service.py
```

---

## Quick Checklist for Code Generation

When generating code, ensure:

- [ ] ✅ Correct naming conventions (snake_case, PascalCase, etc.)
- [ ] ✅ Type hints on all functions
- [ ] ✅ Docstrings on all public functions/classes
- [ ] ✅ Custom exceptions (NotFoundError, ValidationError, etc.)
- [ ] ✅ Structured logging with correlation IDs
- [ ] ✅ No sensitive data in logs or errors
- [ ] ✅ Async/await for I/O operations
- [ ] ✅ Pydantic models for validation
- [ ] ✅ Context managers for database sessions
- [ ] ✅ Appropriate HTTP status codes
- [ ] ✅ Security-first principles

---

## References

- [../docs/CODING_GUIDELINES.md](../docs/CODING_GUIDELINES.md) - Complete guidelines
- [../docs/QUICK_REFERENCE.md](../docs/QUICK_REFERENCE.md) - Quick patterns
- [../docs/SPECIFICATION_GUIDELINES.md](../docs/SPECIFICATION_GUIDELINES.md) - Spec standards
- [../docs/STRUCTURE.md](../docs/STRUCTURE.md) - Project structure

---

**When in doubt, consult the full guidelines in the `docs/` directory.**
