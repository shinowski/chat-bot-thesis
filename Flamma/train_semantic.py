"""Train a separate candidate; inspect its report before activating it."""

import argparse
from pathlib import Path

from model.train_intent import train_candidate, activate_candidate, next_candidate_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='New candidate artifact; defaults to the next unused version.')
    parser.add_argument('--activate', action='store_true', help='Select the candidate after its comparison quality gate passes.')
    parser.add_argument('--supplement', type=Path, action='append', default=[], help='Additional fictional intent examples; may be supplied more than once.')
    args = parser.parse_args()
    output = args.output or next_candidate_path()
    train_candidate(output, additional_sources=args.supplement)
    if args.activate:
        activate_candidate(output)


if __name__ == '__main__':
    main()
