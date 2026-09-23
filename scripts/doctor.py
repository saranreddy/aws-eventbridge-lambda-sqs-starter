#!/usr/bin/env python3
"""
Check prerequisites for the EventBridge + Lambda + SQS starter.
"""

import argparse
import shutil
import subprocess
import sys


def check_command(cmd: str, version_flag: str = "--version") -> tuple[bool, str]:
    """Check if a command is available and get its version."""
    if not shutil.which(cmd):
        return False, f"{cmd} not found"

    try:
        result = subprocess.run(
            [cmd, version_flag],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        version = result.stdout.strip() or result.stderr.strip()
        return True, version.split("\n")[0]
    except Exception as e:
        return False, str(e)


def check_aws_credentials() -> tuple[bool, str]:
    """Check if AWS credentials are configured."""
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError

        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        account = identity["Account"]
        arn = identity["Arn"]
        return True, f"Account: {account}, ARN: {arn}"
    except NoCredentialsError:
        return False, "No AWS credentials found"
    except ClientError as e:
        return False, f"AWS credentials invalid: {e}"
    except ImportError:
        return False, "boto3 not installed (run: pip install -r requirements.txt)"
    except Exception as e:
        return False, str(e)


def check_python_packages() -> tuple[bool, str]:
    """Check if required Python packages are installed."""
    try:
        import boto3

        return True, f"boto3 {boto3.__version__}"
    except ImportError:
        return False, "boto3 not installed (run: pip install -r requirements.txt)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check prerequisites for EventBridge + Lambda + SQS starter"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed version information",
    )
    args = parser.parse_args()

    checks: list[tuple[str, tuple[bool, str]]] = [
        ("Terraform", check_command("terraform", "version")),
        ("AWS CLI", check_command("aws", "--version")),
        ("Python", check_command("python3", "--version")),
        ("Python packages", check_python_packages()),
        ("AWS credentials", check_aws_credentials()),
    ]

    all_passed = True
    max_label_len = max(len(label) for label, _ in checks)

    print("Prerequisites Check")
    print("=" * 60)

    for label, (passed, info) in checks:
        status = "✓" if passed else "✗"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"

        print(f"{color}{status}{reset} {label:<{max_label_len}}", end="")

        if args.verbose or not passed:
            print(f" - {info}")
        else:
            print()

        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n✓ All checks passed! Ready to deploy.")
        print("\nNext steps:")
        print("  cd infra")
        print("  terraform init")
        print("  terraform apply -var-file=demo.tfvars")
        return 0
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
