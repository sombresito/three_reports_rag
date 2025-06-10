"""Utility to download the embedding model to a user defined location."""

import argparse
import os

from sentence_transformers import SentenceTransformer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and save the embedding model locally",
    )
    parser.add_argument(
        "--output-path",
        default=os.getenv("EMBEDDING_MODEL_PATH"),
        help=(
            "Directory where the model will be stored. "
            "If omitted, the EMBEDDING_MODEL_PATH environment variable is used."
        ),
    )
    args = parser.parse_args()

    if not args.output_path:
        parser.error(
            "Output path must be provided via --output-path or EMBEDDING_MODEL_PATH"
        )

    os.makedirs(args.output_path, exist_ok=True)
    model = SentenceTransformer("intfloat/multilingual-e5-small")
    model.save(args.output_path)


if __name__ == "__main__":
    main()

