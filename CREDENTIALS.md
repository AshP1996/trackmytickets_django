# Login Credentials

These credentials have been verified and are ready for use.

## Platform Admin
- **URL**: [https://trackmytickets.in/platform/login](https://trackmytickets.in/platform/login) (Production)
- **Local URL**: [http://localhost:8080/platform/login](http://localhost:8080/platform/login)
- **Email**: `superadmin@platform.com`
- **Password**: `password123`

---

## Demo Organization
- **Organization Name**: Demo Corp
- **Subdomain**: `demo`
- **URL**: [http://localhost:8080/demo/auth/login](http://localhost:8080/demo/auth/login) (Local)

### 1. Organization Admin
- **Email**: `admin@demo.com`
- **Password**: `password123`
- **Role**: Admin (Full access to organization settings and tickets)

### 2. Support Agent
- **Email**: `agent@demo.com`
- **Password**: `password123`
- **Role**: Agent (Can view and reply to assigned tickets)

### 3. Customer
- **Email**: `customer@demo.com`
- **Password**: `password123`
- **Role**: Customer (Can create tickets and view their own)

> For local development, ensure the `web` container is running and accessible at `http://localhost:8080`.

---

## Acme Corp (Basic Verification)
- **Organization Name**: Acme Corp
- **Subdomain**: `acme`
- **URL**: [http://localhost:8080/acme/auth/login](http://localhost:8080/acme/auth/login)

### 1. Organization Admin
- **Email**: `admin@acme.com`
- **Password**: `password123`

---

## Omega Corp (Full System Test)
- **Organization Name**: Omega Corp
- **Subdomain**: `omega`
- **URL**: [http://localhost:8080/omega/auth/login](http://localhost:8080/omega/auth/login)

### 1. Organization Admin
- **Email**: `admin@omega.com`
- **Password**: `password123`
- **Role**: Admin

### 2. Support Manager
- **Email**: `manager@omega.com`
- **Password**: `password123`
- **Role**: Manager (Can manage projects and assign tickets)

### 3. Support Agent
- **Email**: `agent@omega.com`
- **Password**: `password123`
- **Role**: Agent (Can work on assigned tickets)

### 4. Customer
- **Email**: `customer@omega.com`
- **Password**: `password123`
- **Role**: Customer (Can create tickets)
