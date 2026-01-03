#!/usr/bin/env python3
import argparse
from pathlib import Path

import processor
import scraper


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a job folder and description file from a job posting link."
    )
    parser.add_argument("url", help="Job posting link (Indeed supported)")
    args = parser.parse_args()

    job_data = scraper.scrape_job(args.url)
    result = processor.process_job(job_data, Path.cwd(), args.url)

    print(f"Created folder: {result['folder_path']}")
    print(f"Wrote description: {result['file_path']}")


if __name__ == "__main__":
    main()
