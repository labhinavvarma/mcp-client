import json
import random
from faker import Faker

def generate_test_json(num_rows: int, num_cols: int, output_file: str = "test_data.json"):
    fake = Faker()
    data = {}

    # Generate unique column names using Faker
    col_names = set()
    while len(col_names) < num_cols:
        col_names.add(fake.word())

    col_names = list(col_names)

    # Fill each column with random float values
    for col in col_names:
        data[col] = [round(random.uniform(1, 1000), 2) for _ in range(num_rows)]

    # Write to JSON file
    with open(output_file, "w") a s f:
        json.dump(data, f, indent=2)

    print(f"✅ JSON file '{output_file}' generated with {num_cols} columns and {num_rows} rows.")

# Example usage
if __name__ == "__main__":
    generate_test_json(num_rows=100, num_cols=100)
