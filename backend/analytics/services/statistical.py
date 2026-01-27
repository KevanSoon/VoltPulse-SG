"""Statistical analysis service for consumption data.

Uses scipy for rigorous statistical calculations:
- Confidence intervals (95% CI with z = 1.96)
- Z-scores and two-tailed p-values
- Paired t-tests for before/after intervention comparisons
"""

import numpy as np
from scipy import stats
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CohortStats:
    """Statistical summary for a cohort."""
    n: int
    mean: float
    std: float
    median: float
    min_val: float
    max_val: float
    sem: float  # Standard error of mean
    ci_lower: float
    ci_upper: float


class StatisticalAnalyzer:
    """Service for performing statistical analysis on consumption data.

    Uses 95% confidence intervals (z = 1.96) for anomaly detection
    and paired t-tests for intervention effectiveness analysis.
    """

    CONFIDENCE_LEVEL = 0.95  # 95% confidence
    Z_CRITICAL = 1.96  # Critical z-value for 95% CI (two-tailed)

    def calculate_cohort_statistics(
        self,
        consumption_values: List[float]
    ) -> CohortStats:
        """Calculate comprehensive statistics for a cohort.

        Args:
            consumption_values: List of kWh consumption values

        Returns:
            CohortStats with mean, std, CI, etc.

        Raises:
            ValueError: If fewer than 2 data points provided
        """
        if not consumption_values or len(consumption_values) < 2:
            raise ValueError("Need at least 2 data points for analysis")

        arr = np.array(consumption_values, dtype=np.float64)
        n = len(arr)
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))  # Sample std with Bessel's correction
        sem = std / np.sqrt(n) if n > 0 else 0.0

        # 95% Confidence Interval using z-score
        # For population-level anomaly detection, we use mean +/- 1.96*std
        ci_lower = mean - self.Z_CRITICAL * std
        ci_upper = mean + self.Z_CRITICAL * std

        return CohortStats(
            n=n,
            mean=mean,
            std=std,
            median=float(np.median(arr)),
            min_val=float(np.min(arr)),
            max_val=float(np.max(arr)),
            sem=sem,
            ci_lower=ci_lower,
            ci_upper=ci_upper
        )

    def calculate_z_score(
        self,
        value: float,
        mean: float,
        std: float
    ) -> float:
        """Calculate z-score for a value.

        Args:
            value: The observation value
            mean: Population/cohort mean
            std: Population/cohort standard deviation

        Returns:
            Z-score (number of standard deviations from mean)
        """
        if std == 0 or std is None:
            return 0.0
        return (value - mean) / std

    def calculate_p_value(self, z_score: float) -> float:
        """Calculate two-tailed p-value from z-score.

        Uses the standard normal distribution (scipy.stats.norm).

        Args:
            z_score: The z-score to convert

        Returns:
            Two-tailed p-value (probability of observing this extreme)
        """
        # Two-tailed p-value: probability of being this far from mean in either direction
        return float(2 * (1 - stats.norm.cdf(abs(z_score))))

    def is_anomaly(
        self,
        value: float,
        mean: float,
        std: float,
        threshold_sigma: float = 1.96
    ) -> Tuple[bool, str, float, float]:
        """Determine if a value is an anomaly based on confidence interval.

        A value is considered anomalous if it falls outside the 95% CI,
        i.e., |z-score| > 1.96.

        Args:
            value: The consumption value to check
            mean: Cohort mean consumption
            std: Cohort standard deviation
            threshold_sigma: Number of std devs for anomaly (default 1.96 for 95% CI)

        Returns:
            Tuple of (is_anomaly, anomaly_type, z_score, p_value)
            - anomaly_type is "HIGH" for overconsumption, "LOW" for underconsumption
        """
        z_score = self.calculate_z_score(value, mean, std)
        p_value = self.calculate_p_value(z_score)

        is_outlier = abs(z_score) > threshold_sigma
        anomaly_type = "HIGH" if z_score > 0 else "LOW"

        return (is_outlier, anomaly_type, z_score, p_value)

    def paired_t_test(
        self,
        before_values: List[float],
        after_values: List[float]
    ) -> Dict[str, float]:
        """Perform paired t-test for before/after intervention comparison.

        Used to determine if the change in consumption after an intervention
        is statistically significant.

        Args:
            before_values: Consumption values before intervention
            after_values: Consumption values after intervention

        Returns:
            Dict with t_statistic, p_value, mean_diff, ci bounds, is_significant

        Raises:
            ValueError: If sample sizes don't match or are too small
        """
        if len(before_values) != len(after_values):
            raise ValueError("Before and after samples must have equal length")

        if len(before_values) < 2:
            raise ValueError("Need at least 2 paired observations")

        before = np.array(before_values, dtype=np.float64)
        after = np.array(after_values, dtype=np.float64)

        # Paired t-test (tests if mean difference is significantly different from 0)
        t_stat, p_value = stats.ttest_rel(before, after)

        # Difference statistics (positive = savings, negative = increased consumption)
        differences = before - after
        mean_diff = float(np.mean(differences))
        std_diff = float(np.std(differences, ddof=1))
        n = len(differences)
        sem_diff = std_diff / np.sqrt(n)

        # 95% CI for the mean difference
        ci_lower = mean_diff - self.Z_CRITICAL * sem_diff
        ci_upper = mean_diff + self.Z_CRITICAL * sem_diff

        return {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "mean_difference": mean_diff,
            "std_difference": std_diff,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "is_significant": p_value < 0.05,
            "sample_size": n
        }

    def welch_t_test(
        self,
        group1: List[float],
        group2: List[float]
    ) -> Dict[str, float]:
        """Welch's t-test for independent samples with unequal variances.

        Useful for comparing consumption between different housing type cohorts
        or different districts.

        Args:
            group1: First group's consumption values
            group2: Second group's consumption values

        Returns:
            Dict with t_statistic, p_value, is_significant
        """
        if len(group1) < 2 or len(group2) < 2:
            raise ValueError("Need at least 2 observations per group")

        arr1 = np.array(group1, dtype=np.float64)
        arr2 = np.array(group2, dtype=np.float64)

        # Welch's t-test (doesn't assume equal variances)
        t_stat, p_value = stats.ttest_ind(arr1, arr2, equal_var=False)

        return {
            "t_statistic": float(t_stat),
            "p_value": float(p_value),
            "is_significant": p_value < 0.05,
            "group1_mean": float(np.mean(arr1)),
            "group2_mean": float(np.mean(arr2)),
            "group1_n": len(arr1),
            "group2_n": len(arr2)
        }

    def calculate_effect_size(
        self,
        before_values: List[float],
        after_values: List[float]
    ) -> float:
        """Calculate Cohen's d effect size for before/after comparison.

        Provides a standardized measure of the intervention's impact,
        independent of sample size.

        Args:
            before_values: Consumption values before intervention
            after_values: Consumption values after intervention

        Returns:
            Cohen's d effect size:
            - |d| < 0.2: negligible
            - 0.2 <= |d| < 0.5: small
            - 0.5 <= |d| < 0.8: medium
            - |d| >= 0.8: large
        """
        before = np.array(before_values, dtype=np.float64)
        after = np.array(after_values, dtype=np.float64)

        mean_diff = np.mean(before) - np.mean(after)

        # Pooled standard deviation
        n1, n2 = len(before), len(after)
        var1, var2 = np.var(before, ddof=1), np.var(after, ddof=1)
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

        if pooled_std == 0:
            return 0.0

        return float(mean_diff / pooled_std)

    def get_z_critical_for_confidence(self, confidence_level: float) -> float:
        """Get the critical z-value for a given confidence level.

        Args:
            confidence_level: Confidence level (e.g., 0.95 for 95%)

        Returns:
            Critical z-value (e.g., 1.96 for 95% CI)
        """
        # For two-tailed, alpha = 1 - confidence_level
        # We need the z-value that leaves alpha/2 in each tail
        alpha = 1 - confidence_level
        return float(stats.norm.ppf(1 - alpha / 2))
