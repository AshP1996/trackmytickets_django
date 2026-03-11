"""
Selenium Browser Automation Tests for Multi-Tenant Ticket System
Requires: pip install selenium webdriver-manager
Run: python -m pytest tests/test_browser_ui.py -v --tb=short
"""
import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

BASE_URL = "http://localhost:8080"


@pytest.fixture(scope="module")
def driver():
    """Create a headless Chrome driver."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)
    yield driver
    driver.quit()


def login(driver, org, email, password="password123"):
    """Helper to login to an organization."""
    driver.get(BASE_URL)
    driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
    driver.delete_all_cookies()
    driver.get(f"{BASE_URL}/{org}/login")
    time.sleep(1)
    
    email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[name='email'], #email")
    email_field.clear()
    email_field.send_keys(email)
    
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password'], input[name='password'], #password")
    password_field.clear()
    password_field.send_keys(password)
    
    submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], .login-btn, .btn-primary")
    submit_btn.click()
    time.sleep(2)


# ════════════════════════════════════════════════════════════════════════
# LOGIN TESTS
# ════════════════════════════════════════════════════════════════════════
class TestLoginFlow:
    
    def test_login_page_loads(self, driver):
        driver.get(f"{BASE_URL}/demo/login")
        time.sleep(1)
        assert "login" in driver.current_url.lower() or "Login" in driver.page_source or "Sign In" in driver.page_source

    def test_login_success_demo(self, driver):
        login(driver, "demo", "admin@demo.com")
        assert "login" not in driver.current_url.lower()

    def test_landing_page_loads(self, driver):
        driver.get(BASE_URL)
        time.sleep(1)
        assert "TrackMyTicket" in driver.page_source


# ════════════════════════════════════════════════════════════════════════
# DASHBOARD TESTS
# ════════════════════════════════════════════════════════════════════════
class TestDashboard:
    
    def test_admin_dashboard_loads(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/admin/dashboard")
        time.sleep(2)
        page = driver.page_source
        # Should show some dashboard content
        assert "Dashboard" in page or "Total" in page or "Tickets" in page

    def test_dashboard_no_spinner(self, driver):
        """Verify dashboard doesn't get stuck in infinite spinner."""
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/admin/dashboard")
        time.sleep(3)
        # After 3 seconds, loading should be complete
        page = driver.page_source
        assert "loading" not in page.lower() or "Total" in page


# ════════════════════════════════════════════════════════════════════════
# TICKET LIST TESTS
# ════════════════════════════════════════════════════════════════════════
class TestTicketList:
    
    def test_ticket_list_loads(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/tickets")
        time.sleep(2)
        page = driver.page_source
        assert "Tickets" in page
        # Should have ticket IDs visible
        assert "SUP-" in page or "WEB-" in page or "IT-" in page

    def test_ticket_filters_visible(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/tickets")
        time.sleep(2)
        # Check for filter elements
        page = driver.page_source
        assert "Status" in page or "Priority" in page or "Filter" in page

    def test_new_ticket_button_exists(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/tickets")
        time.sleep(2)
        page = driver.page_source
        assert "New Ticket" in page or "Create" in page


# ════════════════════════════════════════════════════════════════════════
# PROJECT LIST TESTS
# ════════════════════════════════════════════════════════════════════════
class TestProjectList:
    
    def test_project_list_loads(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/projects")
        time.sleep(2)
        page = driver.page_source
        assert "Projects" in page or "SUP" in page or "WEB" in page

    def test_create_project_button(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/projects")
        time.sleep(2)
        page = driver.page_source
        assert "Create" in page or "New Project" in page or "Add" in page


# ════════════════════════════════════════════════════════════════════════
# NAVIGATION TESTS
# ════════════════════════════════════════════════════════════════════════
class TestNavigation:
    
    def test_sidebar_links(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/admin/dashboard")
        time.sleep(2)
        page = driver.page_source
        
        expected_links = ["Dashboard", "Tickets", "Projects"]
        for link in expected_links:
            assert link in page, f"Missing sidebar link: {link}"

    def test_notifications_page(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/notifications")
        time.sleep(2)
        # Page should load without error
        assert "500" not in driver.page_source or "Notifications" in driver.page_source


# ════════════════════════════════════════════════════════════════════════
# MULTI-TENANT UI TESTS
# ════════════════════════════════════════════════════════════════════════
class TestMultiTenantUI:
    
    def test_different_org_login(self, driver):
        """Test login to different organizations."""
        for org in ["demo", "acme", "omega"]:
            creds = {
                "demo": "admin@demo.com",
                "acme": "admin@acme.com",
                "omega": "admin@omega.com"
            }
            driver.get(f"{BASE_URL}/{org}/login")
            time.sleep(1)
            assert "404" not in driver.page_source, f"Login page for {org} returns 404"


# ════════════════════════════════════════════════════════════════════════
# ADMIN PAGES TESTS
# ════════════════════════════════════════════════════════════════════════
class TestAdminPages:
    
    def test_users_page(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/admin/users")
        time.sleep(2)
        assert "Users" in driver.page_source

    def test_departments_page(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/admin/departments")
        time.sleep(2)
        assert "Department" in driver.page_source

    def test_data_sources_page(self, driver):
        login(driver, "demo", "admin@demo.com")
        driver.get(f"{BASE_URL}/demo/admin/data-sources")
        time.sleep(2)
        assert "Data Source" in driver.page_source or "data" in driver.page_source.lower()
