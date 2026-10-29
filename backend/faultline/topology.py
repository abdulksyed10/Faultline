"""Caller -> dependency graph; reverse order is topological evaluation order."""
import numpy as np

SERVICE_IDS = ["gateway", "checkout", "catalog", "payments", "inventory", "orders", "cache", "database"]
SERVICES = [
    {"id": sid, "label": label, "role": role, "x": x, "y": y}
    for sid, label, role, x, y in [
        ("gateway", "API Gateway", "Entry point", 95, 205),
        ("checkout", "Checkout", "Orchestration", 305, 120),
        ("catalog", "Catalog", "Product discovery", 305, 300),
        ("payments", "Payments", "Transaction processing", 520, 65),
        ("inventory", "Inventory", "Stock availability", 520, 205),
        ("orders", "Orders", "Order persistence", 520, 345),
        ("cache", "Redis Cache", "Hot data", 740, 100),
        ("database", "Postgres", "System of record", 740, 300),
    ]
]
EDGES = [
    ("gateway", "checkout", .8), ("gateway", "catalog", .4),
    ("checkout", "payments", .8), ("checkout", "inventory", .5), ("checkout", "orders", .7),
    ("catalog", "inventory", .4), ("catalog", "cache", .7),
    ("payments", "database", .9), ("inventory", "database", .65),
    ("orders", "database", .85),
]
WEIGHTS = np.zeros((8, 8))
for caller, dependency, weight in EDGES:
    WEIGHTS[SERVICE_IDS.index(caller), SERVICE_IDS.index(dependency)] = weight


def ancestors(service: str) -> list[str]:
    """All callers whose responses can inherit effects from this dependency."""
    found, frontier = set(), [service]
    while frontier:
        child = frontier.pop()
        for caller, dep, _ in EDGES:
            if dep == child and caller not in found:
                found.add(caller)
                frontier.append(caller)
    return [sid for sid in SERVICE_IDS if sid in found]


def topology() -> dict:
    return {"services": SERVICES, "edges": [{"source": a, "target": b, "weight": w} for a, b, w in EDGES],
            "semantics": "caller -> dependency; latency effects travel toward callers"}
