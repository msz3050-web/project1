import random
import uuid
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# -----------------------
# CONFIG
# -----------------------

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 6, 30)

BASE_MONTHLY_VOLUME = 200

SEVERITY_DIST = [0.5, 0.35, 0.15]  # 1,2,3
SEVERITY_VALUES = [1, 2, 3]

# -----------------------
# HELPERS
# -----------------------

def random_date(start, end):
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))

def seasonal_factor(month):
    if month in [12, 1, 2]:  # חורף
        return 1.3
    elif month in [6, 7, 8]:  # קיץ
        return 1.15
    elif month in [4, 9]:  # חגים לדוגמה
        return 0.8
    return 1.0

# -----------------------
# GENERATORS
# -----------------------

def generate_customers(n=50):
    data = []
    for i in range(n):
        tier = random.choice(["A", "B", "C"])
        sla_base = {"A": 24, "B": 48, "C": 72}[tier]
        data.append({
            "customer_id": i,
            "name": f"Customer_{i}",
            "industry": random.choice(["Manufacturing", "Retail", "Energy"]),
            "tier": tier,
            "contract_sla_hours": sla_base
        })
    return pd.DataFrame(data)

def generate_assets(customers, n=300):
    data = []
    for i in range(n):
        customer_id = random.choice(customers["customer_id"].tolist())
        data.append({
            "asset_id": i,
            "customer_id": customer_id,
            "asset_type": random.choice(["Pump", "Generator", "Compressor"]),
            "install_date": random_date(datetime(2018,1,1), datetime(2023,1,1)),
            "criticality": random.choice([1,2,3]),
            "failure_weight": np.random.pareto(2.0) + 1
        })
    return pd.DataFrame(data)

def generate_technicians(n=8):
    data = []
    for i in range(n):
        skill = random.choice([1,2,3])
        data.append({
            "technician_id": i,
            "name": f"Tech_{i}",
            "skill_level": skill,
            "base_resolution_hours": random.randint(6, 24),
            "active": True
        })
    return pd.DataFrame(data)

def generate_tickets(assets, technicians):
    tickets = []
    current = START_DATE

   


    
    while current <= END_DATE:
        month_factor = seasonal_factor(current.month)
        monthly_volume = int(BASE_MONTHLY_VOLUME * month_factor * np.random.normal(1, 0.1))
        monthly_capacity = len(technicians) * 140  # שעות עבודה חודשיות
        expected_hours = monthly_volume * 15  # הערכה גסה

        load_ratio = expected_hours / monthly_capacity
        
        weighted_assets = assets["failure_weight"] / assets["failure_weight"].sum()

        for _ in range(monthly_volume):
            open_time = random_date(
                datetime(current.year, current.month, 1),
                datetime(current.year, current.month, 28)
            )

            asset = assets.sample(weights=weighted_assets).iloc[0]
            tech = technicians.sample().iloc[0]

            severity = np.random.choice(SEVERITY_VALUES, p=SEVERITY_DIST)

            severity_factor = {1: 1.8, 2: 1.2, 3: 0.8}[severity]

            resolution_hours = (
                tech["base_resolution_hours"]
                * severity_factor
                /  (0.7 + tech["skill_level"] * 0.6)
                * np.random.normal(1, 0.35)
            )

            resolution_hours = resolution_hours * (1 + min(load_ratio, 1.2) * 0.45)

            sla_hours = {1: 54, 2: 30, 3: 10}[severity]

            close_time = open_time + timedelta(hours=max(1, resolution_hours))

            status = "closed"
            if resolution_hours > sla_hours:
                status = "escalated"
            overload_factor = 1

            if monthly_volume > BASE_MONTHLY_VOLUME * 1.15:
                overload_factor = 1.4
            
            resolution_hours = resolution_hours * overload_factor

            tickets.append({
                "ticket_id": str(uuid.uuid4()),
                "asset_id": asset["asset_id"],
                "open_time": open_time,
                "severity": severity,
                "assigned_technician_id": tech["technician_id"],
                "sla_hours": sla_hours,
                "close_time": close_time,
                "status": status
            })

        # קפיצה לחודש הבא
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return pd.DataFrame(tickets)

# -----------------------
# RUN
# -----------------------

if __name__ == "__main__":
    customers = generate_customers()
    assets = generate_assets(customers)
    technicians = generate_technicians()
    tickets = generate_tickets(assets, technicians)

    print(tickets.head())
    print("Total tickets:", len(tickets))

print("Severity distribution:")
print(tickets["severity"].value_counts(normalize=True))

print("\nEscalation rate:")
print((tickets["status"] == "escalated").mean())

tickets["resolution_hours"] = (
    (tickets["close_time"] - tickets["open_time"]).dt.total_seconds() / 3600
)

print("\nAverage resolution time:")
print(tickets["resolution_hours"].mean())



tickets.to_csv("tickets.csv", index=False)