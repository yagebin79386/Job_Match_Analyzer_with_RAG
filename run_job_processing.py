#!/usr/bin/env python3
"""
Run the job processing workflow directly.
This script triggers the entire workflow:
1. Retrieves jobs from Apify
2. Extracts keywords using GPT
3. Queries the PersonalRAG for information (optional)
4. Analyzes job fitness against RAG info
5. Extracts numerical scores from job analyses

Usage:
    python run_job_processing.py                 # Run with all features
    python run_job_processing.py --no-rag        # Run without RAG functionality
    python run_job_processing.py --no-milvus     # Run without Milvus connection check
    python run_job_processing.py --test          # Run in test mode (no Apify scraping)

Before running, make sure all dependencies are installed:
    pip install -r requirements.txt
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from dotenv import load_dotenv

def check_env_vars():
    """Check required environment variables and print a helpful message if missing."""
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    required_vars = {
        'DB_HOST': 'PostgreSQL database host',
        'DB_PORT': 'PostgreSQL database port',
        'DB_NAME': 'PostgreSQL database name',
        'DB_USER': 'PostgreSQL database user',
        'DB_PASSWORD': 'PostgreSQL database password',
        'OPENAI_API_KEY': 'OpenAI API key for GPT analysis',
        'APIFY_API_TOKEN': 'Apify API token for job scraping',
        'APIFY_TASK_ID': 'Apify task ID for job scraping' 
    }
    
    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"{var} ({description})")
    
    if missing_vars:
        print("Error: Missing required environment variables in your .env file:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease add these variables to your .env file in the project directory.")
        return False
    
    return True

def check_and_start_docker():
    """Check if Docker containers are running and start them if needed."""
    print("Checking if Milvus Docker containers are running...")
    
    # Get list of running containers with milvus in name
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=milvus", "--format", "{{.Names}}"],
            capture_output=True, 
            text=True, 
            check=False
        )
        running_containers = result.stdout.strip().split('\n')
        running_containers = [c for c in running_containers if c]  # Remove empty strings
        
        required_containers = ['milvus-standalone', 'milvus-etcd', 'milvus-minio']
        missing_containers = [c for c in required_containers if c not in running_containers]
        
        if missing_containers:
            print(f"Some Milvus containers are not running: {', '.join(missing_containers)}")
            print("Starting Docker containers...")
            
            # Check if docker-compose file exists in the expected location
            compose_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                       "Personal_RAG", "docker-compose.yml")
            
            if not os.path.exists(compose_file):
                print(f"Error: Docker compose file not found at {compose_file}")
                return False
                
            # Start containers using docker-compose
            compose_dir = os.path.dirname(compose_file)
            subprocess.run(
                ["docker-compose", "-f", compose_file, "up", "-d"],
                cwd=compose_dir,
                check=True
            )
            
            print("Docker containers started. Waiting for Milvus to be ready...")
            # Give some time for containers to start
            subprocess.run(
                ["sleep", "10"],
                check=False
            )
            return True
        else:
            print("All Milvus containers are running.")
            return True
            
    except subprocess.CalledProcessError as e:
        print(f"Error checking Docker status: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error checking Docker: {str(e)}")
        return False

def run_processing(use_rag=True, test_mode=False, skip_milvus=False):
    """
    Run the full job processing workflow once.
    
    Args:
        use_rag (bool): Whether to use RAG functionality
        test_mode (bool): Run in test mode (doesn't trigger Apify scraping)
        skip_milvus (bool): Skip Milvus connection check
    """
    print(f"\n{'=' * 60}")
    print(f"Starting job processing at {datetime.now()}")
    print(f"{'=' * 60}")
    
    # Check environment variables
    if not check_env_vars():
        sys.exit(1)
    
    try:
        # Dynamically import the JobProcessor to catch import errors
        try:
            from process_jobs_rag import JobProcessor
        except ImportError as e:
            print(f"Error importing required modules: {str(e)}")
            print("\nPlease make sure you've installed all dependencies:")
            print("pip install -r requirements.txt")
            sys.exit(1)
        
        # Check and start Docker containers if needed for Milvus
        if use_rag and not skip_milvus:
            if not check_and_start_docker():
                print("\nWarning: Could not verify Docker containers are running.")
                proceed = input("Continue anyway? (y/n): ")
                if proceed.lower() != 'y':
                    print("Exiting...")
                    sys.exit(1)
                
        # Set environment variable to skip Milvus connection check if needed
        if skip_milvus:
            os.environ['SKIP_MILVUS_CHECK'] = 'true'
            print("Skipping Milvus connection check as requested.")
        
        # Run in test mode if requested
        if test_mode:
            print("\nRunning in TEST MODE - will skip Apify scraping")
        
        # Initialize the job processor
        processor = JobProcessor(test_mode=test_mode)
        
        # Check if RAG is available and required
        if use_rag and processor.rag is None:
            print("\nWARNING: RAG functionality was requested but is not available.")
            print("This could be due to missing dependencies or configuration issues.")
            proceed = input("Continue without RAG functionality? (y/n): ")
            if proceed.lower() != 'y':
                print("Exiting...")
                sys.exit(1)
            
            print("Continuing without RAG functionality...")
        
        # Run the workflow
        processor.process_jobs()
        
        print(f"\n{'=' * 60}")
        print(f"Job processing completed at {datetime.now()}")
        print(f"{'=' * 60}\n")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError running job processing: {str(e)}")
        print("Stack trace:", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Run job collection and processing workflow',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_job_processing.py                 # Run with all features
  python run_job_processing.py --no-rag        # Run without RAG functionality
  python run_job_processing.py --no-milvus     # Run without Milvus check
  python run_job_processing.py --test          # Run in test mode (no scraping)
        """
    )
    parser.add_argument('--no-rag', action='store_true', help='Run without RAG functionality')
    parser.add_argument('--no-milvus', action='store_true', help='Skip Milvus connection check')
    parser.add_argument('--test', action='store_true', help='Run in test mode (no Apify scraping)')
    args = parser.parse_args()
    
    # Print banner
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║          Job Collection Reminder System              ║")
    print("╚══════════════════════════════════════════════════════╝")
    
    # Run the processing
    run_processing(use_rag=not args.no_rag, test_mode=args.test, skip_milvus=args.no_milvus) 