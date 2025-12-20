import time
from etl_pipeline import ETLPipeline

def test_performance():
    pipeline = ETLPipeline()
    start_time = time.time()
    result = pipeline.run_pipeline('data/raw_data.csv')
    execution_time = time.time() - start_time
    print(f"⏱️  Время выполнения ETL: {execution_time:.2f} секунд")
    assert execution_time < 5
    assert len(result) == 7

def test_memory_usage():
    pipeline = ETLPipeline()
    pipeline.run_pipeline('data/raw_data.csv')
    memory_usage = pipeline.transformed_data.memory_usage(deep=True).sum()
    print(f"💾 Использование памяти: {memory_usage} байт")
    assert memory_usage < 200000  # relaxed limit
