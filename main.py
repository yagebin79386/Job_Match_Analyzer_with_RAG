import schedule
import time
from datetime import datetime
import os
import json
from dotenv import load_dotenv
from process_jobs_rag import JobProcessor
from email_service import EmailService
import traceback

load_dotenv()

def process_jobs():
    """Process jobs using the complete workflow."""
    print(f"Starting job processing at {datetime.now()}")
    
    try:
        # Initialize the job processor
        processor = JobProcessor()
        
        # Run the complete workflow
        processor.process_jobs()
        
        # Send email with top jobs after processing
        print("Sending email with top jobs...")
        email_service = EmailService()
        email_service.send_job_newsletter()
        
    except Exception as e:
        print(f"Error processing jobs: {str(e)}")
        print(f"Error type: {type(e)}")
        print(f"Traceback: {traceback.format_exc()}")

def main():
    # Schedule the job to run on Wednesdays and Sundays at 4:00
    schedule.every().wednesday.at("04:00").do(process_jobs)
    schedule.every().sunday.at("04:00").do(process_jobs)
    
    print(f"Job scheduler initialized at {datetime.now()}")
    print("Job will run on Wednesdays and Sundays at 04:00")
    
    # Print next run time
    next_run = schedule.next_run()
    if next_run:
        print(f"Next scheduled run: {next_run}")
    
    # Optional: Uncomment to run immediately on startup
    # process_jobs()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main() 