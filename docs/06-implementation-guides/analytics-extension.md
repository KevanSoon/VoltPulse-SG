# Analytics Extension Guide

Guide for adding new analytics endpoints and visualizations.

---

## Overview

The analytics system provides:
- **District Heatmaps**: Postal district aggregation
- **Anomaly Detection**: Statistical outlier detection
- **Cohort Analysis**: Housing type comparisons
- **Intervention Tracking**: Before/after effectiveness

You can extend with custom analytics features.

---

## Adding New Endpoint

### Step 1: Define Pydantic Models

Create `backend/analytics/models.py` entry:

```python
class EnergyTrendResponse(BaseModel):
    """Response for energy trend analysis."""
    trends: List[TrendDataPoint]
    forecast: Optional[List[ForecastPoint]] = None
    summary_statistics: Dict[str, float]
    generated_at: str
```

### Step 2: Create Service Method

Create `backend/analytics/services/trend_analyzer.py`:

```python
class TrendAnalyzer:
    """Analyzes energy consumption trends."""

    async def analyze_trends(
        self,
        records: List[dict],
        period_months: int = 12
    ) -> Dict[str, Any]:
        """Analyze consumption trends over time."""

        # Group by month
        monthly_data = {}
        for record in records:
            month = record["billing_period_end"][:7]  # YYYY-MM
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(record["consumption_kwh"])

        # Calculate monthly averages
        trends = []
        for month in sorted(monthly_data.keys()):
            avg = sum(monthly_data[month]) / len(monthly_data[month])
            trends.append({
                "month": month,
                "average_kwh": avg,
                "household_count": len(monthly_data[month])
            })

        # Simple linear forecast
        # ... implement forecasting logic ...

        return {
            "trends": trends,
            "forecast": forecast_data,
            "summary_statistics": {...}
        }
```

### Step 3: Add Router Endpoint

Edit `backend/analytics/router.py`:

```python
from .services.trend_analyzer import TrendAnalyzer

trend_analyzer = TrendAnalyzer()

@router.get("/trends", response_model=EnergyTrendResponse)
async def get_energy_trends(
    period_months: int = Query(12, ge=3, le=36),
    housing_type: Optional[str] = None
):
    """Get energy consumption trends over time."""
    records = await get_consumption_records()

    if housing_type:
        records = [r for r in records if classify_housing_type(r["premise_address"]).value == housing_type]

    result = await trend_analyzer.analyze_trends(records, period_months)

    return EnergyTrendResponse(
        trends=result["trends"],
        forecast=result.get("forecast"),
        summary_statistics=result["summary_statistics"],
        generated_at=datetime.now().isoformat()
    )
```

---

## Frontend Visualization

### Create React Component

`frontend/src/app/analytics/components/TrendChart.tsx`:

```typescript
import { Line } from 'recharts';
import { LineChart, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

export function TrendChart({ data }: { data: TrendDataPoint[] }) {
  return (
    <LineChart width={800} height={400} data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="month" />
      <YAxis />
      <Tooltip />
      <Legend />
      <Line type="monotone" dataKey="average_kwh" stroke="#8884d8" />
    </LineChart>
  );
}
```

### Integrate in Dashboard

`frontend/src/app/analytics/page.tsx`:

```typescript
import { TrendChart } from './components/TrendChart';

export default function AnalyticsPage() {
  const [trendData, setTrendData] = useState([]);

  useEffect(() => {
    fetch('/api/analytics/trends')
      .then(res => res.json())
      .then(data => setTrendData(data.trends));
  }, []);

  return (
    <div>
      <h2>Energy Trends</h2>
      <TrendChart data={trendData} />
    </div>
  );
}
```

---

## Statistical Analysis

Use SciPy for advanced analytics:

```python
from scipy import stats
from scipy.signal import find_peaks

def detect_seasonal_patterns(monthly_data: List[float]):
    """Detect seasonal consumption patterns."""

    # Detrend data
    detrended = stats.detrend(monthly_data)

    # Find peaks (high consumption months)
    peaks, _ = find_peaks(detrended, prominence=0.5)

    # Autocorrelation to detect periodicity
    acf = np.correlate(detrended, detrended, mode='full')
    acf = acf[len(acf)//2:]
    acf /= acf[0]

    # Find dominant period
    period_peaks, _ = find_peaks(acf[1:], prominence=0.3)
    dominant_period = period_peaks[0] + 1 if len(period_peaks) > 0 else None

    return {
        "high_consumption_months": peaks.tolist(),
        "dominant_period": dominant_period,
        "seasonality_strength": float(np.max(acf[1:]))
    }
```

---

## Related Documentation

- [Heatmap Analytics](../04-services/heatmap-analytics.md)
- [Statistical Analysis](../04-services/statistical-analysis.md)
- [Analytics Endpoints](../05-api-reference/endpoints.md#analytics-dashboard)

---

**Generated:** 2024-06-15
