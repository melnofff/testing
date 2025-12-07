# This test tries to use Great Expectations if available; otherwise falls back to pandas checks.
try:
    import great_expectations as ge
    GE_AVAILABLE = True
except Exception:
    GE_AVAILABLE = False

import pandas as pd
from etl_pipeline import ETLPipeline

def test_data_quality():
    pipeline = ETLPipeline()
    pipeline.run_pipeline('data/raw_data.csv')
    df = pipeline.transformed_data.copy()

    # Basic checks (always run)
    assert 'id' in df.columns
    assert 'name' in df.columns
    assert df['id'].notna().all()
    assert df['name'].notna().all()
    assert (df['salary'] > 0).all()
    assert (df['age'] >= 18).all() and (df['age'] <= 70).all()
    assert set(df['department'].unique()).issubset({'IT','HR','Finance'})

    # If Great Expectations is available, run additional expectations
    if GE_AVAILABLE:
        gdf = ge.from_pandas(df)
        expected_columns = ['id','name','age','salary','department','join_date','experience_years','salary_category']
        assert gdf.expect_table_columns_to_match_ordered_list(expected_columns).success
        assert gdf.expect_column_values_to_be_unique('id').success
        assert gdf.expect_column_values_to_not_be_null('id').success
        assert gdf.expect_column_values_to_not_be_null('name').success
        assert gdf.expect_column_values_to_be_between('age',18,70).success
        assert gdf.expect_column_values_to_be_between('salary',10000,200000).success
