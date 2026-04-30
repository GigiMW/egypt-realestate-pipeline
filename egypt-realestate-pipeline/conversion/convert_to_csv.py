import os
import sys
import duckdb
import pandas as pd


def convert(db_path: str, out_dir: str) -> None:
	os.makedirs(out_dir, exist_ok=True)
	con = duckdb.connect(db_path)
	try:
		con.execute("SELECT * FROM main.mart_listings").df().to_csv(
			os.path.join(out_dir, "mart_listings.csv"), index=False
		)
		con.execute("SELECT * FROM main.avg_price_by_location").df().to_csv(
			os.path.join(out_dir, "avg_price_by_location.csv"), index=False
		)
		con.execute("SELECT * FROM main.price_distribution").df().to_csv(
			os.path.join(out_dir, "price_distribution.csv"), index=False
		)
	finally:
		con.close()


def main():
	# Resolve project root (assumes this file lives under <project>/conversion)
	this_dir = os.path.dirname(os.path.abspath(__file__))
	project_root = os.path.dirname(this_dir)
	db_path = os.path.join(project_root, "data", "realestate.duckdb")
	out_dir = os.path.join(project_root, "data")

	if not os.path.exists(db_path):
		print(f"ERROR: database not found at {db_path}", file=sys.stderr)
		sys.exit(2)

	try:
		convert(db_path, out_dir)
		print("Conversion completed: CSVs written to", out_dir)
	except Exception as e:
		print("Conversion failed:", e, file=sys.stderr)
		sys.exit(1)


if __name__ == "__main__":
	main()