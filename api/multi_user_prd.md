# Multi-User Migration PRD

## Overview
This document outlines the plan to migrate the HubGPT API from a single-user to a multi-user architecture while maintaining API stability and feature parity.

## Status Overview
✅ = Complete
🔄 = In Progress
⏳ = Pending

## Goals
- ✅ Enable multiple users to use the system independently
- ✅ Maintain existing API endpoint compatibility
- ✅ Ensure data isolation between users
- 🔄 Scale storage from file-based to database-backed
- ✅ Implement proper authentication and authorization
- 🔄 Allow for future collaboration features

## Non-Goals
- Rewriting the frontend
- Changing the core advisor/chat functionality
- Modifying the tool execution framework
- Changing the LLM integration architecture

## Migration Phases

### Phase 1: Authentication & User Management ✅
**Goal**: Replace basic auth with JWT while maintaining backward compatibility
**Status**: Complete

#### Changes
1. Database Setup
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    settings JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    token TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

#### New Endpoints
```http
POST /api/v1/auth/register
{
    "username": str,
    "email": str,
    "password": str
}

POST /api/v1/auth/login
{
    "username": str,
    "password": str
}
Response: {
    "access_token": str,
    "token_type": "bearer"
}

POST /api/v1/auth/logout
Headers: Authorization: Bearer <token>
Response: Success message

GET /api/v1/users/me
Headers: Authorization: Bearer <token>
Response: UserResponse object
```

#### Compatibility Layer
- ✅ Add JWT auth alongside basic auth
- ✅ Auto-create user account for existing basic auth credentials
- ✅ Map basic auth requests to the default user account

### Phase 2: Data Isolation ✅
**Goal**: Migrate to user-specific data storage while maintaining file structure
**Status**: Complete

#### Database Schema
```sql
CREATE TABLE user_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    is_public BOOLEAN DEFAULT false,
    file_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, file_path)
);

CREATE TABLE file_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID REFERENCES user_files(id),
    shared_with_id UUID REFERENCES users(id),
    permissions JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Storage Structure
1. User-specific directories:
```
storage/
├── users/
│   ├── {user_id}/
│   │   ├── files/
│   │   │   ├── content/       # User file content
│   │   │   ├── uploads/       # Temporary upload storage
│   │   │   └── temp/         # Processing files
│   │   └── ...
│   └── ...
└── shared/                   # Shared resources
    └── ...
```

#### File Management Features
1. Core Features ✅
   - [x] User-specific storage spaces
   - [x] Database-backed file metadata
   - [x] File path sanitization
   - [x] Access control system
   - [x] Automatic directory creation
   - [x] File type detection
   - [x] Content type tracking
   - [x] Public/private file support

2. File Operations ✅
   - [x] File upload (multipart/form-data)
   - [x] File content retrieval
   - [x] File renaming with path updates
   - [x] File deletion with cleanup
   - [x] Directory listing with tree structure
   - [x] File sharing between users

3. Access Control ✅
   - [x] Private by default
   - [x] Optional public flag
   - [x] Owner-based access
   - [x] Share-based access
   - [x] Database-tracked permissions

4. Error Handling ✅
   - [x] Failed upload cleanup
   - [x] Access validation
   - [x] Path validation
   - [x] Duplicate handling
   - [x] Proper error messages

#### File API Endpoints
```http
GET /api/v1/files
Description: List all files for current user
Response: List[FileResponse]

GET /api/v1/files/{file_path}/content
Description: Get file contents
Response: File content
Auth: Bearer token required

POST /api/v1/files/{file_path}
Description: Create or update file
Body: multipart/form-data
Fields:
  - file: File data
  - is_public: boolean (optional)
Response: FileResponse

PATCH /api/v1/files/{file_path}
Description: Rename file
Body: JSON
{
    "new_name": string
}
Response: FileResponse

DELETE /api/v1/files/{file_path}
Description: Delete file
Response: Success message
Auth: Bearer token required

POST /api/v1/files/{file_path}/share
Description: Share file with another user
Body: JSON
{
    "shared_with_id": string,
    "permissions": {
        "read": boolean,
        "write": boolean
    }
}
Response: FileShareResponse

GET /api/v1/files/{file_path}/shares
Description: List all shares for a file
Response: List[FileShareResponse]

DELETE /api/v1/files/{file_path}/share/{user_id}
Description: Remove file share
Response: Success message
```

### Phase 3: Sharing & Collaboration ✅
**Goal**: Enable secure file and resource sharing between users
**Status**: Complete

#### Features
1. File Sharing ✅
   - [x] Database schema for shares
   - [x] Basic share creation/deletion
   - [x] Share permissions management
   - [x] Share listing
   - [x] Access control enforcement

2. Resource Sharing 🔄
   - [ ] Advisor sharing
   - [ ] Chat sharing
   - [ ] Tool sharing
   - [ ] Workspace sharing

3. Collaboration Tools ⏳
   - [ ] Shared workspaces
   - [ ] Team management
   - [ ] Access control lists
   - [ ] Activity tracking

### Phase 4: Advanced Features ⏳
**Goal**: Add enterprise-grade features and optimizations
**Status**: Pending

#### Planned Features
1. Storage Optimization
   - [ ] File deduplication
   - [ ] Large file handling
   - [ ] Content compression
   - [ ] Caching layer

2. Security Enhancements
   - [ ] File encryption
   - [ ] Audit logging
   - [ ] Access policies
   - [ ] Rate limiting

3. Enterprise Features
   - [ ] Usage analytics
   - [ ] Quota management
   - [ ] Backup/restore
   - [ ] Admin dashboard

## Implementation Notes

### Authentication Flow
1. User registers or logs in
2. System issues JWT token
3. Token required for all API calls
4. Basic auth fallback available

### File Management Flow
1. User uploads file via multipart/form-data
2. System:
   - Validates request
   - Creates directories
   - Saves file content
   - Creates database record
   - Returns metadata
3. File access requires:
   - Valid token
   - Owner access or share

### Error Handling
- All endpoints return proper HTTP status codes
- Detailed error messages provided
- Failed operations cleaned up
- Transactions used where appropriate

### Security Considerations
- All files private by default
- Access controlled via database
- File paths sanitized
- Content types validated
- Size limits enforced

## Next Steps
1. Complete sharing implementation
2. Add team features
3. Implement analytics
4. Add enterprise features
5. Optimize storage

For technical details, see the API documentation in README.md.

## API Stability Guarantees
1. All existing endpoints will maintain their current request/response formats
2. New functionality will be added through new endpoints
3. User context will be derived from authentication
4. Existing basic auth will continue to work through Phase 1-3
5. File paths and structures will be maintained during migration

## Success Metrics
1. Zero downtime during migration
2. No breaking changes to frontend
3. Successful data isolation between users
4. Improved performance with database backend
5. Maintained feature parity throughout migration

## Timeline
- Phase 1: 1-2 weeks
- Phase 2: 2-3 weeks
- Phase 3: 2-3 weeks
- Phase 4: 1-2 weeks
- Phase 5: 1-2 weeks
- Phase 6: 2-3 weeks

Total estimated time: 9-15 weeks

## Risks and Mitigations
1. **Data Loss**
   - Dual write during migration
   - Backup all files before each phase
   - Rollback plans for each phase

2. **Performance**
   - Database indexing strategy
   - Caching layer for frequent queries
   - Gradual migration of data

3. **API Compatibility**
   - Comprehensive test suite
   - Staged rollout of changes
   - Fallback mechanisms

4. **Security**
   - Regular security audits
   - Rate limiting
   - Input validation

## Testing Strategy

### Test Infrastructure
```python
# api/tests/test_multi_user.py

from fastapi.testclient import TestClient
from api.main import app
import pytest
import jwt

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def test_user_token():
    # Create test user and return JWT token
    pass

@pytest.fixture
def test_user_basic_auth():
    # Return basic auth credentials for compatibility testing
    pass
```

### Phase-specific Test Coverage

#### Phase 1: Authentication Tests
```python
def test_register_user(test_client):
    response = test_client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepass123"
    })
    assert response.status_code == 201

def test_login_user(test_client):
    response = test_client.post("/auth/login", json={
        "username": "testuser",
        "password": "securepass123"
    })
    assert response.status_code == 200
    assert "token" in response.json()

def test_basic_auth_compatibility(test_client, test_user_basic_auth):
    # Ensure basic auth still works during migration
    response = test_client.get("/advisors", auth=test_user_basic_auth)
    assert response.status_code == 200
```

#### Phase 2: Data Isolation Tests
```python
def test_user_specific_agents(test_client, test_user_token):
    # Test user can only see their own agents
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = test_client.get("/advisors", headers=headers)
    assert response.status_code == 200
    
def test_file_isolation(test_client, test_user_token):
    # Test file operations are properly isolated
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = test_client.get("/files", headers=headers)
    assert response.status_code == 200
```

#### Phase 3: Database Migration Tests
```python
def test_large_file_handling(test_client, test_user_token):
    # Test large file upload and retrieval
    headers = {"Authorization": f"Bearer {test_user_token}"}
    with open("test_large_file.txt", "rb") as f:
        response = test_client.post("/files/upload", 
            files={"file": f},
            headers=headers
        )
    assert response.status_code == 201

def test_content_deduplication(test_client, test_user_token):
    # Test identical files are stored once
    pass
```

#### Phase 4: Sharing Tests
```python
def test_share_agent(test_client, test_user_token):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = test_client.post(
        "/agents/test-agent/share",
        json={"username": "other_user", "permissions": ["read"]},
        headers=headers
    )
    assert response.status_code == 200

def test_shared_access(test_client, test_user_token):
    # Test shared resource access
    pass
```

#### Phase 5: Tool Access Tests
```python
def test_tool_quota(test_client, test_user_token):
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = test_client.post(
        "/tools/execute",
        json={"tool": "test_tool", "params": {}},
        headers=headers
    )
    assert response.status_code == 200
```

#### Phase 6: API Migration Tests
```python
def test_agent_endpoints(test_client, test_user_token):
    # Test new agent endpoints
    headers = {"Authorization": f"Bearer {test_user_token}"}
    response = test_client.get("/agents", headers=headers)
    assert response.status_code == 200
    
    # Test old endpoints still work
    response = test_client.get("/advisors", headers=headers)
    assert response.status_code == 200
    assert "warning" in response.headers
```

### Continuous Integration
1. GitHub Actions workflow:
```yaml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:latest
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: pytest api/tests/ -v
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/test_db
```

### Test Data Management
1. Fixtures for:
   - Test users with different roles
   - Sample agents and chats
   - Various file sizes and types
   - Sharing scenarios
   - Tool usage patterns

2. Database seeding:
```python
@pytest.fixture(autouse=True)
def setup_test_data():
    # Create test database tables
    # Seed with initial data
    yield
    # Cleanup test data
```

3. File cleanup:
```python
@pytest.fixture(autouse=True)
def cleanup_test_files():
    yield
    # Remove test files from storage
```

## Future Considerations
1. Team workspaces
2. Role-based access control
3. Usage analytics
4. Billing integration
5. API key management 