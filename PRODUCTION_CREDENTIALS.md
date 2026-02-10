# TrackMyTickets - Production Login Credentials

**Production URL:** https://trackmytickets.in

---

## 🔐 Platform Admin

**Login URL:** https://trackmytickets.in/platform/login

| Email | Password |
|-------|----------|
| admin@trackmytickets.in | Admin@2026 |

**Features:**
- Manage all organizations
- Create/edit/delete organizations
- View platform-wide analytics
- Manage platform settings

---

## 🏢 ACME Corporation

**Subdomain:** `acme`  
**Login URL:** https://trackmytickets.in/acme/login

### Admin
| Email | Password | Role |
|-------|----------|------|
| admin@acme.com | Admin@123 | Organization Admin |

**Features:**
- Full organization management
- User management
- Department management
- Reports and analytics
- System configuration

### Department Heads
| Email | Password | Department | Role |
|-------|----------|------------|------|
| head.it@acme.com | Head@123 | IT Support | Department Head |
| head.hr@acme.com | Head@123 | Human Resources | Department Head |
| head.sales@acme.com | Head@123 | Sales | Department Head |
| head.support@acme.com | Head@123 | Customer Support | Department Head |

**Features:**
- View department tickets
- Assign tickets to agents
- View department analytics
- Manage department agents

### Agents
| Email | Password | Department | Role |
|-------|----------|------------|------|
| agent.it1@acme.com | Agent@123 | IT Support | Agent |
| agent.it2@acme.com | Agent@123 | IT Support | Agent |
| agent.support1@acme.com | Agent@123 | Customer Support | Agent |
| agent.support2@acme.com | Agent@123 | Customer Support | Agent |

**Features:**
- View assigned tickets
- Update ticket status
- Add comments to tickets
- View ticket history

### Customers
| Email | Password | Role |
|-------|----------|------|
| customer1@client.com | Customer@123 | Customer |
| customer2@client.com | Customer@123 | Customer |
| customer3@client.com | Customer@123 | Customer |

**Features:**
- View own tickets
- Create new tickets
- Add comments to own tickets
- Track ticket status

---

## 🏢 Globex Inc

**Subdomain:** `globex`  
**Login URL:** https://trackmytickets.in/globex/login

### Admin
| Email | Password | Role |
|-------|----------|------|
| admin@globex.com | Admin@123 | Organization Admin |

### Department Heads
| Email | Password | Department | Role |
|-------|----------|------------|------|
| head.eng@globex.com | Head@123 | Engineering | Department Head |
| head.marketing@globex.com | Head@123 | Marketing | Department Head |

### Agents
| Email | Password | Department | Role |
|-------|----------|------------|------|
| agent.eng1@globex.com | Agent@123 | Engineering | Agent |

### Customers
| Email | Password | Role |
|-------|----------|------|
| customer1@partner.com | Customer@123 | Customer |

---

## 🏢 Demo Corp

**Subdomain:** `demo`  
**Login URL:** https://trackmytickets.in/demo/login

| Email | Password | Role |
|-------|----------|------|
| admin@demo.com | password123 | Organization Admin |

---

## 🏢 TechFlow Solutions

**Subdomain:** `techflow`  
**Login URL:** https://trackmytickets.in/techflow/login

| Email | Password | Role |
|-------|----------|------|
| admin@techflow.com | password123 | Organization Admin |

---

## 📝 Sample Tickets (ACME Corp)

The following test tickets have been created in ACME Corporation:

1. **SUP-1** - Cannot access email account (High Priority, In Progress)
   - Assigned to: agent.it1@acme.com
   - Customer: customer1@client.com

2. **SUP-2** - Printer not working (Medium Priority, Open)
   - Assigned to: agent.it1@acme.com
   - Customer: customer2@client.com

3. **SUP-3** - Need help with software installation (Low Priority, Open)
   - Assigned to: agent.support1@acme.com
   - Customer: customer1@client.com

4. **SUP-4** - VPN connection issues (High Priority, Open, Unassigned)
   - Customer: customer2@client.com

---

## 🧪 Testing Checklist

### Platform Admin Testing
- [ ] Login to platform
- [ ] View all organizations
- [ ] Create new organization
- [ ] Edit organization details
- [ ] View platform analytics

### Organization Admin Testing (ACME)
- [ ] Login to organization
- [ ] View dashboard
- [ ] View all tickets
- [ ] Create new user
- [ ] Manage departments
- [ ] View reports
- [ ] Configure organization settings

### Department Head Testing
- [ ] Login as department head
- [ ] View department dashboard
- [ ] View department tickets
- [ ] Assign tickets to agents
- [ ] View department analytics

### Agent Testing
- [ ] Login as agent
- [ ] View assigned tickets
- [ ] Update ticket status
- [ ] Add comments to tickets
- [ ] View ticket details

### Customer Testing
- [ ] Login as customer
- [ ] View own tickets
- [ ] Create new ticket
- [ ] Add comment to ticket
- [ ] View ticket status

---

## 🔗 Quick Links

- **Landing Page:** https://trackmytickets.in/
- **Platform Login:** https://trackmytickets.in/platform/login
- **ACME Login:** https://trackmytickets.in/acme/login
- **Globex Login:** https://trackmytickets.in/globex/login
- **Demo Login:** https://trackmytickets.in/demo/login
- **TechFlow Login:** https://trackmytickets.in/techflow/login
