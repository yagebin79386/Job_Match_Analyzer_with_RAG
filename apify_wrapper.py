import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv
from datetime import datetime
import time

load_dotenv()

class ApifyWrapper:
    def __init__(self):
        self.api_token = os.getenv('APIFY_API_TOKEN')
        self.client = ApifyClient(self.api_token)
        self.task_id = "BU6xftpc3qHM9y7if"  # Your task ID
        self.last_run_id = None

    def trigger_job_scraping(self):
        """Run the Apify actor task and return the run information"""
        try:
            print("Starting Apify task...")
            run_info = self.client.task(self.task_id).call()
            
            # Create a serializable version of the run info
            safe_run_info = {
                'id': run_info.get('id'),
                'actId': run_info.get('actId'),
                'taskId': run_info.get('taskId'),
                'status': run_info.get('status'),
                'defaultDatasetId': run_info.get('defaultDatasetId')
            }
            
            # Store the run ID for later use
            self.last_run_id = safe_run_info['id']
            
            print(f"Task started successfully. Run ID: {self.last_run_id}")
            return safe_run_info
        except Exception as e:
            print(f"Error triggering job scraping: {str(e)}")
            return None
    
    def wait_for_run_completion(self, run_id, max_wait_time=300, check_interval=10):
        """Wait for an Apify run to complete with timeout"""
        print(f"Waiting for run {run_id} to complete...")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                run_info = self.client.run(run_id).get()
                status = run_info.get('status')
                
                if status == 'SUCCEEDED':
                    print(f"Run {run_id} completed successfully")
                    return run_info
                elif status in ['FAILED', 'ABORTED', 'TIMED-OUT']:
                    print(f"Run {run_id} failed with status: {status}")
                    return None
                
                print(f"Run status: {status}. Waiting {check_interval} seconds...")
                time.sleep(check_interval)
            except Exception as e:
                print(f"Error checking run status: {str(e)}")
                time.sleep(check_interval)
        
        print(f"Timeout waiting for run {run_id} to complete")
        return None

    def get_job_data(self):
        """Trigger scraping job and fetch the data when complete"""
        try:
            # Start the task
            run = self.trigger_job_scraping()
            if not run:
                return None

            # Wait for the run to complete
            run_id = run['id']
            completed_run = self.wait_for_run_completion(run_id)
            
            if not completed_run:
                print("Run did not complete successfully")
                return None

            # Get the dataset ID from the completed run
            dataset_id = completed_run.get("defaultDatasetId")
            if not dataset_id:
                print("No dataset ID found in the run information")
                return None
            
            # Fetch and process the job data
            print(f"Fetching job data from dataset {dataset_id}...")
            jobs = []
            
            try:
                for item in self.client.dataset(dataset_id).iterate_items():
                    # Make sure each job item is JSON serializable
                    if isinstance(item, dict):
                        jobs.append(item)
                
                print(f"Retrieved {len(jobs)} jobs")
                return jobs
            except Exception as e:
                print(f"Error iterating dataset items: {str(e)}")
                return None
                
        except Exception as e:
            print(f"Error in get_job_data: {str(e)}")
            return None 