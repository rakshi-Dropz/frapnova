app_name = "stock_flow"
app_title = "Stock Flow"
app_publisher = "Rakshi"
app_description = "Maker Checker Stock App"
app_email = "Rakshi@email.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Home Pages & Website Routing
# -----------------------------
# Route the root "/" directly to our Zerodha-style home landing page
home_page = "home"

website_route_rules = [
    {"from_route": "/", "to_route": "home"},
    {"from_route": "/login", "to_route": "login"},
    {"from_route": "/frapnora", "to_route": "frapnora"},
]

# Post-login destination for authenticated users
login_redirect_url = "/frapnora"

# Scheduled Tasks
# ---------------
scheduler_events = {
    "daily": [
        "stock_flow.tasks.check_low_stock_and_notify"
    ]
}