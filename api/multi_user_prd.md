# Multi-User Migration PRD

## Overview
This document outlines the plan to migrate the HubGPT API from a single-user to a multi-user architecture while maintaining API stability and feature parity.

## Goals
- Enable multiple users to use the system independently
- Maintain existing API endpoint compatibility
- Ensure data isolation between users
- Scale storage from file-based to database-backed
- Implement proper authentication and authorization
- Allow for future collaboration features

## Non-Goals
- Rewriting the frontend
- Changing the core advisor/chat functionality
- Modifying the tool execution framework
- Changing the LLM integration architecture

## Migration Phases

### Phase 1: Authentication & User Management
**Goal**: Replace basic auth with JWT while maintaining backward compatibility

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
```python
POST /auth/register
{
    "username": str,
    "email": str,
    "password": str
}

POST /auth/login
{
    "username": str,
    "password": str
}

POST /auth/logout
{
    "token": str
}

GET /users/me
```

#### Compatibility Layer
- Add JWT auth alongside basic auth
- Auto-create user account for existing basic auth credentials
- Map basic auth requests to the default user account

### Phase 2: Data Isolation
**Goal**: Migrate to user-specific data storage while maintaining file structure

#### Database Schema
```sql
CREATE TABLE user_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    agent_id TEXT NOT NULL,
    is_private BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, agent_id)
);

CREATE TABLE user_chats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    agent_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id UUID REFERENCES user_chats(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    tool_call_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, file_path)
);
```

#### Storage Structure
1. User-specific directories:
```
/users/{user_id}/
    agents/             # Agent definitions (small JSON/MD files)
    chats/             # Chat histories
    files/             # User's file storage
        content/       # Large content files (books, documents)
        uploads/       # User uploaded files
        temp/         # Temporary processing files
```

2. File Management Strategy:
- Small files (agent definitions, chat logs) -> Database
- Large files (books, documents) -> File system with database metadata
- Content deduplication for shared resources
- File path/metadata in database, actual content on disk
- User isolation through directory structure

#### Migration Steps
1. Create user directory structure
2. Move existing content to default user's space
3. Add database records for file metadata
4. Implement path translation layer
5. Add user context to all file operations

### Phase 3: Database Migration
**Goal**: Move appropriate data to database while maintaining efficient file storage

#### Additional Schema
```sql
CREATE TABLE agent_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    model TEXT NOT NULL,
    temperature FLOAT,
    max_tokens INTEGER,
    stream BOOLEAN DEFAULT true,
    messages JSONB NOT NULL,
    gateway TEXT,
    tools JSONB,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE file_content_refs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_hash TEXT UNIQUE NOT NULL,
    file_path TEXT NOT NULL,
    size_bytes BIGINT,
    ref_count INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Storage Strategy
1. Database Storage:
   - Agent definitions
   - Chat messages
   - File metadata
   - User settings
   - Tool configurations

2. File System Storage:
   - Large content files (books, documents)
   - User uploads
   - Generated artifacts
   - Temporary processing files

3. Content Deduplication:
   - Hash content files
   - Store unique files once
   - Track references in database
   - Clean up unused files

### Phase 4: Sharing & Collaboration
**Goal**: Enable advisor and chat sharing between users

#### Schema Additions
```sql
CREATE TABLE advisor_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    shared_with_id UUID REFERENCES users(id),
    advisor_id TEXT NOT NULL,
    permissions JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(owner_id, shared_with_id, advisor_id)
);

CREATE TABLE chat_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID REFERENCES users(id),
    shared_with_id UUID REFERENCES users(id),
    chat_id UUID REFERENCES user_chats(id),
    permissions JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(owner_id, shared_with_id, chat_id)
);
```

#### New Endpoints
```python
POST /advisors/{advisor_id}/share
{
    "username": str,
    "permissions": List[str]
}

DELETE /advisors/{advisor_id}/share/{username}

GET /advisors/shared-with-me

POST /chat/{chat_id}/share
{
    "username": str,
    "permissions": List[str]
}

DELETE /chat/{chat_id}/share/{username}

GET /chats/shared-with-me
```

### Phase 5: Tool Access Control
**Goal**: Implement user-specific tool access and quotas

#### Schema Additions
```sql
CREATE TABLE user_tool_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tool_name TEXT NOT NULL,
    quota_limit INTEGER,
    quota_used INTEGER DEFAULT 0,
    settings JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, tool_name)
);

CREATE TABLE tool_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Phase 6: API Endpoint Migration
**Goal**: Transition endpoint naming from 'advisor' to 'agent' while maintaining backward compatibility

#### Steps
1. Add new agent endpoints alongside existing advisor endpoints
2. Update documentation to prefer agent terminology
3. Mark advisor endpoints as deprecated
4. Add warning headers to advisor endpoint responses
5. Plan frontend migration
6. Set deprecation timeline

#### New Endpoints (While Maintaining Old Ones)
```python
GET /agents
POST /agents
GET /agents/{agent_id}
PUT /agents/{agent_id}
DELETE /agents/{agent_id}

GET /chat/agent/{agent_id}/history
POST /chat/agent/{agent_id}/new
GET /chat/agent/{agent_id}/latest
```

#### Migration Support
- Response header indicating preferred endpoint
- Automatic redirection option (configurable)
- Documentation updates
- Migration guide for frontend

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