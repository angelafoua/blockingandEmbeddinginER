from pii_extraction import extract_pii
from normalization import normalize_record
from blocking import build_blocks, recursive_blocking, generate_candidate_pairs
from matching import is_match
from clustering import build_clusters
import csv

def read_input(file_path):
    records = []
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            records.append(row[0])
    return records

def write_output(cluster_map, output_file):
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["record_id", "cluster_id"])
        for record_id, cluster_id in cluster_map.items():
            writer.writerow([record_id, cluster_id])

def main():

    input_file = "C:\\Users\\ldfoua1\\OneDrive - UA Little Rock\\Documents\\PhD\\Blocking-only DWM\\blockingMainlyER-main\\S1G.txt" \

    output_file = "output/clusters.csv"

    raw_records = read_input(input_file)

    normalized_records = {}
    blocking_tokens = {}

    # Step 1 + 2: Extract + Normalize
    for record in raw_records:
        pii_data = extract_pii(record)
        norm_record = normalize_record(pii_data)

        record_id = norm_record["record_id"]
        normalized_records[record_id] = norm_record

        blocking_tokens[record_id] = norm_record["blocking_tokens"]

    # Step 3: Blocking
    initial_blocks = build_blocks(blocking_tokens)
    final_blocks = recursive_blocking(initial_blocks)

    # Step 4: Candidate pairs
    pairs = generate_candidate_pairs(final_blocks)

    # Step 5: Clustering
    cluster_map = build_clusters(pairs, normalized_records, is_match)

    # Step 6: Output
    write_output(cluster_map, output_file)


if __name__ == "__main__":
    main()
