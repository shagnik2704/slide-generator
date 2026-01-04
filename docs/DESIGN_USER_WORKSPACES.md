# Design Document: User Workspaces & Persistence

## Overview

This document outlines the architecture for user-specific workspaces in the Slide Generator application. Users will have persistent access to their scripts, generated images, reports, and other assets across sessions and devices.

---

## Goals

1. **User Authentication**: Restrict access to @edupyramids.org accounts only
2. **Data Persistence**: Users see their work across sessions/devices
3. **File Storage**: Store generated assets in user's Google Drive
4. **No BaaS**: Self-managed infrastructure (no Supabase/Firebase)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React)                               │
│                                                                          │
│   - "Login with Google" button                                          │
│   - Project list sidebar                                                │
│   - Asset gallery per project                                           │
│   - JWT stored in httpOnly cookie                                       │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                              │
│                                                                          │
│   ┌────────────────────┐   ┌────────────────────────────────────────┐   │
│   │   Auth Layer       │   │   SQLAlchemy ORM                       │   │
│   │   - Google OAuth   │   │   - Users table                        │   │
│   │   - JWT tokens     │   │   - Projects table                     │   │
│   │   - Domain check   │   │   - Assets table (metadata)            │   │
│   └────────────────────┘   └────────────────────────────────────────┘   │
│                                                                          │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │   Google Drive Service                                          │    │
│   │   - Upload files to user's Drive                                │    │
│   │   - Download files via proxy endpoint                           │    │
│   │   - Manage folder structure                                     │    │
│   └────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────┬──────────────────────────────────────┘
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
         ┌──────────────────────┐      ┌──────────────────────┐
         │   PostgreSQL         │      │   User's Google      │
         │   (Render)           │      │   Drive              │
         │                      │      │                      │
         │   - Users            │      │   📁 Slide Generator │
         │   - Projects         │      │      📁 Project 1    │
         │   - Assets metadata  │      │         📄 script    │
         │   - OAuth tokens     │      │         🖼️ images    │
         └──────────────────────┘      └──────────────────────┘
```

---

## Authentication

### Method: Google OAuth 2.0 (Workspace Internal)

**Why:**
- edupyramids.org uses Google Workspace
- Single Sign-On for all team members
- OAuth token also grants Google Drive access

**Flow:**
```
1. User clicks "Login with Google"
2. Redirected to Google OAuth consent screen
3. User authenticates with @edupyramids.org account
4. Google returns authorization code
5. Backend exchanges code for access_token + refresh_token
6. Backend creates JWT for session management
7. Frontend stores JWT in httpOnly cookie
```

**Domain Restriction:**
- Google Cloud Console → OAuth consent → User type: "Internal"
- Only @edupyramids.org users can access

**Scopes Requested:**
- `email` - Get user's email
- `profile` - Get user's name/avatar
- `drive.file` - Access files created by our app

---

## Database Schema (PostgreSQL)

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    google_refresh_token TEXT,  -- Encrypted
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Projects table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    drive_folder_id VARCHAR(100),  -- Google Drive folder ID
    script_json JSONB,             -- The full script data
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Assets table (metadata only, files in Drive)
CREATE TABLE assets (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,  -- 'image', 'audio', 'script', 'report'
    name VARCHAR(255),
    drive_file_id VARCHAR(100),
    mime_type VARCHAR(100),
    size_bytes INTEGER,
    metadata JSONB,              -- Slide number, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_assets_project_id ON assets(project_id);
CREATE INDEX idx_users_email ON users(email);
```

---

## File Storage: Google Drive

### Folder Structure (per user)
```
📁 Slide Generator/                    ← App root folder
   📁 Python Tutorial/                 ← Project folder
      📄 script.json                   ← Full script data
      📁 images/
         🖼️ slide_01.png
         🖼️ slide_02.png
      📁 audio/
         🎵 narration.wav
      📁 reports/
         📊 compliance_report.html
         📊 quality_report.html
   📁 Linux Basics/                    ← Another project
      ...
```

### Upload Flow
```
1. Image generated on backend
2. Backend uploads to user's Drive (using stored OAuth token)
3. Drive returns file_id
4. Backend stores file_id in assets table
5. Frontend can request file via /api/assets/{id}
```

### Download Flow (Proxy Pattern)
```
1. Frontend requests GET /api/assets/{asset_id}
2. Backend validates user owns the asset
3. Backend fetches file from Drive using refresh_token
4. Backend streams file bytes to frontend
5. Frontend renders image/audio/etc.
```

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/google/login` | Redirect to Google OAuth |
| GET | `/auth/google/callback` | Handle OAuth callback |
| POST | `/auth/logout` | Clear session |
| GET | `/auth/me` | Get current user info |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects` | List user's projects |
| POST | `/projects` | Create new project |
| GET | `/projects/{id}` | Get project details |
| PUT | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |

### Assets
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/{id}/assets` | List project assets |
| GET | `/assets/{id}` | Download asset (proxy) |
| POST | `/projects/{id}/assets` | Upload asset |
| DELETE | `/assets/{id}` | Delete asset |

---

## Security Considerations

1. **OAuth tokens**: Store refresh_token encrypted in DB
2. **JWT**: Use short expiry (15min), httpOnly cookies
3. **CORS**: Restrict to your frontend domain
4. **Rate limiting**: Prevent abuse of Drive API
5. **File validation**: Check file types before upload

---

## Implementation Phases

### Phase 1: Core Auth & DB
- [ ] Set up PostgreSQL on Render
- [ ] Add SQLAlchemy models
- [ ] Implement Google OAuth flow
- [ ] Add JWT middleware
- [ ] Create auth endpoints

### Phase 2: Projects
- [ ] Create project CRUD endpoints
- [ ] Add project listing UI
- [ ] Connect existing generation flows to projects

### Phase 3: Google Drive Integration
- [ ] Set up Google Cloud project with Drive API
- [ ] Implement Drive service (upload/download)
- [ ] Add asset proxy endpoint
- [ ] Migrate image generation to use Drive

### Phase 4: Frontend Updates
- [ ] Add login/logout UI
- [ ] Add project sidebar
- [ ] Add asset gallery
- [ ] Protected route handling

---

## Dependencies

### Backend
- `sqlalchemy` - ORM
- `asyncpg` - Async PostgreSQL driver
- `python-jose` - JWT handling
- `google-auth` - Google OAuth
- `google-api-python-client` - Drive API

### Infrastructure
- PostgreSQL (Render free tier)
- Google Cloud project (free, own quota)

---

## Open Questions

1. **Token refresh strategy**: Background job or on-demand?
2. **Offline access**: What happens if user revokes Drive access?
3. **Storage limits**: Handle cases where user's Drive is full?
4. **Migration**: How to handle existing users/data?

---

## References

- [Google OAuth 2.0 for Web](https://developers.google.com/identity/protocols/oauth2/web-server)
- [Google Drive API](https://developers.google.com/drive/api/v3/about-sdk)
- [FastAPI OAuth2](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
