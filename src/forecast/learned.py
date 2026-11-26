"""Models fitted on past data."""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from forecast.features import build_features, without_blackout
from forecast.weather import FIRST_DAY

TRAIN_FROM = pd.Timestamp(FIRST_DAY, tz="UTC") + pd.Timedelta(days=21)


def training_table(
    history: pd.Series, temperature: pd.Series | None
) -> tuple[pd.DataFrame, pd.Series]:
    targets = history.index[history.index >= TRAIN_FROM]
    x = build_features(history, temperature, targets)
    y = without_blackout(history).reindex(targets)
    return x[y.notna()], y[y.notna()]


class HourlyRidge:
    """One regularised linear regression per local hour."""

    def __init__(self, use_temperature: bool = True, alpha: float = 1.0):
        self.use_temperature = use_temperature
        self.alpha = alpha
        self.models: dict = {}

    def fit(self, history: pd.Series, temperature: pd.Series) -> None:
        x, y = training_table(history, temperature if self.use_temperature else None)
        complete = x.notna().all(axis=1)
        x, y = x[complete], y[complete]
        self.models = {}
        for hour, rows in self._design(x).groupby(x["hour"]):
            model = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha))
            self.models[hour] = model.fit(rows, y.loc[rows.index])

    def predict(
        self, history: pd.Series, temperature: pd.Series, targets: pd.DatetimeIndex
    ) -> pd.Series:
        x = build_features(history, temperature if self.use_temperature else None, targets)
        design = self._design(x)
        result = pd.Series(np.nan, index=targets)
        usable = design.notna().all(axis=1)
        for hour, rows in design[usable].groupby(x.loc[usable, "hour"]):
            result.loc[rows.index] = self.models[hour].predict(rows)
        return result

    @staticmethod
    def _design(x: pd.DataFrame) -> pd.DataFrame:
        weekdays = {f"weekday_{d}": (x["weekday"] == d).astype(float) for d in range(7)}
        return x.drop(columns=["hour", "weekday"]).assign(**weekdays)


class GradientBoosting:
    """Histogram gradient boosting (the LightGBM technique, as implemented in scikit-learn)."""

    def __init__(
        self,
        use_temperature: bool = True,
        learning_rate: float = 0.05,
        max_iter: int = 600,
        max_leaf_nodes: int = 31,
        predict_change: bool = False,
    ):
        self.use_temperature = use_temperature
        self.predict_change = predict_change
        self.params = {
            "learning_rate": learning_rate,
            "max_iter": max_iter,
            "max_leaf_nodes": max_leaf_nodes,
        }
        self.model = None

    def _base(self, x: pd.DataFrame) -> pd.Series:
        # With `predict_change`, the trees learn the difference from last week.
        return x["lag_1w"] if self.predict_change else pd.Series(0.0, index=x.index)

    def fit(self, history: pd.Series, temperature: pd.Series) -> None:
        x, y = training_table(history, temperature if self.use_temperature else None)
        target = y - self._base(x)
        keep = target.notna()
        self.model = HistGradientBoostingRegressor(
            loss="absolute_error", early_stopping=False, random_state=0, **self.params
        ).fit(x[keep], target[keep])

    def predict(
        self, history: pd.Series, temperature: pd.Series, targets: pd.DatetimeIndex
    ) -> pd.Series:
        x = build_features(history, temperature if self.use_temperature else None, targets)
        return pd.Series(self.model.predict(x), index=targets) + self._base(x)
