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
- ✅ Scale storage from file-based to database-backed
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

#### File Management Features
1. Core Features ✅
   - [x] User-specific storage spaces
   - [x] Database-backed file metadata
   - [x] File path sanitization
   - [x] Access control system
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

### Phase 3: Chat System Migration ✅
**Goal**: Move chat functionality to database storage
**Status**: Complete

#### Database Schema
```sql
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    advisor_id UUID REFERENCES advisors(id),
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tool_calls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES messages(id),
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL,
    result JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Phase 4: Sharing & Collaboration 🔄
**Goal**: Enable secure resource sharing between users
**Status**: In Progress

#### Features
1. File Sharing ✅
   - [x] Database schema for shares
   - [x] Basic share creation/deletion
   - [x] Share permissions management
   - [x] Share listing
   - [x] Access control enforcement

2. Resource Sharing 🔄
   - [x] Advisor sharing
   - [ ] Chat sharing
   - [ ] Tool sharing
   - [ ] Workspace sharing

3. Collaboration Tools ⏳
   - [ ] Shared workspaces
   - [ ] Team management
   - [ ] Access control lists
   - [ ] Activity tracking

### Phase 5: Advanced Features ⏳
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

## Next Steps

1. Complete chat sharing implementation
2. Add team workspace features
3. Implement usage analytics
4. Add enterprise features
5. Optimize storage and performance

## Success Metrics

✅ **Achieved**
- Zero downtime during migration
- No breaking changes to frontend
- Successful data isolation between users
- Improved performance with database backend
- Maintained feature parity throughout migration

🔄 **In Progress**
- Complete resource sharing implementation
- Team workspace functionality
- Usage analytics and monitoring

## Testing Strategy

The test harness at `/` (index.html) provides comprehensive testing capabilities for:

1. Authentication flows
2. File management operations
3. Chat functionality
4. Advisor management
5. Sharing features

For automated testing, see the test suite in `api/tests/`. 