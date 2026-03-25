"""
Generate demo CSV files: customer.csv, sales.csv
"""
from pathlib import Path
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_CUSTOMER_DIR = PROJECT_ROOT / "data" / "demo_customer"
DEMO_SALES_DIR = PROJECT_ROOT / "data" / "demo_sales"


def generate_customer(n_rows: int = 1200) -> pd.DataFrame:
    """Customer dataset: id, age, gender, income, segment, signup_date, purchase_count."""
    np.random.seed(42)
    random.seed(42)

    segments = ["Bronze", "Silver", "Gold", "Platinum"]
    genders = ["M", "F", "Other"]

    id_ = np.arange(1, n_rows + 1)
    age = np.clip(np.random.normal(38, 12, n_rows).astype(int), 18, 75)
    gender = np.random.choice(genders, n_rows, p=[0.48, 0.48, 0.04])
    income = np.clip(np.random.lognormal(10, 0.5, n_rows).astype(int), 15000, 150000)
    segment = np.random.choice(segments, n_rows, p=[0.4, 0.35, 0.18, 0.07])
    base = datetime(2020, 1, 1)
    signup_date = [base + timedelta(days=random.randint(0, 1200)) for _ in range(n_rows)]
    purchase_count = np.random.poisson(8, n_rows)

    # Some missing values (for profile demo)
    income = income.astype(float)
    income[np.random.choice(n_rows, size=int(n_rows * 0.03), replace=False)] = np.nan
    signup_date = pd.Series(signup_date)
    signup_date.iloc[np.random.choice(n_rows, size=int(n_rows * 0.02), replace=False)] = pd.NaT

    df = pd.DataFrame({
        "id": id_,
        "age": age,
        "gender": gender,
        "income": income,
        "segment": segment,
        "signup_date": pd.to_datetime(signup_date).dt.strftime("%Y-%m-%d"),
        "purchase_count": purchase_count,
    })
    return df


def generate_sales(n_rows: int = 2500) -> pd.DataFrame:
    """Sales dataset: date, product_id, amount, quantity, region, category."""
    np.random.seed(43)
    random.seed(43)

    regions = ["North", "South", "East", "West", "Central"]
    categories = ["Electronics", "Clothing", "Food", "Home", "Sports"]

    base = datetime(2023, 1, 1)
    dates = [base + timedelta(days=random.randint(0, 365)) for _ in range(n_rows)]
    product_id = np.random.randint(1000, 9999, n_rows)
    amount = np.round(np.random.lognormal(3, 1.2, n_rows), 2)
    quantity = np.random.randint(1, 15, n_rows)
    region = np.random.choice(regions, n_rows, p=[0.25, 0.2, 0.2, 0.2, 0.15])
    category = np.random.choice(categories, n_rows, p=[0.25, 0.2, 0.2, 0.2, 0.15])

    # Some missing values
    amount = amount.astype(float)
    amount[np.random.choice(n_rows, size=int(n_rows * 0.02), replace=False)] = np.nan

    df = pd.DataFrame({
        "date": pd.to_datetime(dates).strftime("%Y-%m-%d"),
        "product_id": product_id,
        "amount": amount,
        "quantity": quantity,
        "region": region,
        "category": category,
    })
    return df


def main():
    DEMO_CUSTOMER_DIR.mkdir(parents=True, exist_ok=True)
    DEMO_SALES_DIR.mkdir(parents=True, exist_ok=True)

    customer = generate_customer(1200)
    customer_path = DEMO_CUSTOMER_DIR / "customer.csv"
    customer.to_csv(customer_path, index=False)
    print(f"Written: {customer_path} ({len(customer)} rows)")

    sales = generate_sales(2500)
    sales_path = DEMO_SALES_DIR / "sales.csv"
    sales.to_csv(sales_path, index=False)
    print(f"Written: {sales_path} ({len(sales)} rows)")


if __name__ == "__main__":
    main()
