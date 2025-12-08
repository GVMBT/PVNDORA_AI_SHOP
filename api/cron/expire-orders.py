"""
Expire Orders Cron Job
Schedule: */5 * * * * (every 5 minutes)
"""
# Delegate to valid module name (expire_orders.py)
from api.cron.expire_orders import handler  # noqa: F401

