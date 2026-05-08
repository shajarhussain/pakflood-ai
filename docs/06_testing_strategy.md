# Testing Strategy

## Layer Matrix

| Layer | Tool | Coverage Target | Scope |
|---|---|---|---|
| Unit — backend | pytest | ≥80% (Phase 6) | Services, adapters, repositories, risk classifier, explainer |
| Integration — backend | pytest + test PostGIS DB | All endpoints | FastAPI endpoints with real DB |
| Unit — frontend | Vitest + React Testing Library | Key components | MapLegend, RiskExplanationPanel, DistrictHoverCard, SourceBadge |
| E2E | Playwright | Critical paths | District search → click → panel → disclaimer |
| ML | pytest | 100% schema | Feature schema, no leakage, artifact creation, inference |
| Geospatial | GeoPandas/Shapely | All spatial ops | Valid geometry, CRS=EPSG:4326, bounding box in Pakistan |
| Accessibility | axe-playwright | All pages | Keyboard nav, contrast, labels, aria |
| Security | Bandit + npm audit | All code | No high-severity findings, no secrets |

## Quality Gate Command

```bash
# Backend
cd backend && pytest app/tests/ --cov=app --cov-report=term-missing -q

# Frontend
cd frontend && npm test

# E2E
cd frontend && npx playwright test --project=chromium

# Security
cd backend && bandit -r app/ -ll
cd frontend && npm audit --audit-level=high
```

## Key Test Examples

```python
# Backend — risk classification
def test_risk_level_thresholds():
    assert classify_risk(0.10) == "Low"
    assert classify_risk(0.45) == "Moderate"
    assert classify_risk(0.70) == "High"
    assert classify_risk(0.90) == "Severe"

# Backend — health endpoint
def test_health_returns_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

```typescript
// Frontend — Playwright E2E
test('district click opens risk panel', async ({ page }) => {
  await page.goto('/');
  await page.getByPlaceholder('Search district').fill('Sukkur');
  await page.getByText('Sukkur').click();
  await expect(page.getByText('Flood Risk')).toBeVisible();
  await expect(page.getByText('Confidence')).toBeVisible();
  await expect(page.getByText('Official sources')).toBeVisible();
});
```

## Phase Completion Gate

A phase is complete only when ALL of these are true:
1. All tests pass (no skipped, no failures)
2. UI screenshot matches visual checklist
3. No flood-specific logic in generic platform code
4. Safety disclaimer visible on every page
5. `docs/adr/` updated if architecture changed
6. No secrets committed to git
