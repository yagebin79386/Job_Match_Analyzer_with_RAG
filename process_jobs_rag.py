import os
import sys
import json
import time
import logging
import functools
import socket
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from database import Database
from apify_wrapper import ApifyWrapper
import importlib.util
import PIL

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('job_processing.log')
    ]
)
logger = logging.getLogger(__name__)

def with_milvus_recovery(max_attempts=3):
    """Decorator to handle Milvus connection issues by automatically restarting containers when needed.
    
    Args:
        max_attempts: Maximum number of retry attempts
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Skip recovery if SKIP_MILVUS_CHECK is true
            if os.getenv('SKIP_MILVUS_CHECK', '').lower() == 'true':
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"Milvus operation failed, but SKIP_MILVUS_CHECK is enabled: {str(e)}")
                    raise
            
            # Normal recovery flow
            for attempt in range(max_attempts):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    is_connection_error = any(err in str(e).lower() for err in 
                                             ["timeout", "connection", "connect"])
                    if attempt < max_attempts-1 and is_connection_error:
                        logger.warning(f"Milvus operation failed: {str(e)}")
                        # Try to reconnect to Milvus
                        self._ensure_milvus_connection()
                        continue
                    raise
        return wrapper
    return decorator

class JobProcessor:
    def __init__(self, test_mode=False):
        """Initialize the job processor with required components.
        
        Args:
            test_mode (bool): Whether to run in test mode (skip job retrieval and insertion)
        """
        self.db = Database()
        self.apify = ApifyWrapper()
        self.openai_client = OpenAI()
        self.test_mode = test_mode
        
        # Create log directories
        os.makedirs('logs', exist_ok=True)
        os.makedirs('debug_logs', exist_ok=True)
        
        # Import the PersonalRAG class from personal_rag.py
        try:
            logger.info("Loading PersonalRAG module...")
            
            # Use the local personal_rag.py file
            module_path = os.path.join(os.path.dirname(__file__), "personal_rag.py")
            logger.info(f"Loading PersonalRAG from: {module_path}")
            
            if os.path.exists(module_path):
                spec = importlib.util.spec_from_file_location("personal_rag", module_path)
                rag_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(rag_module)
                self.PersonalRAG = rag_module.PersonalRAG
                self.QueryMethod = rag_module.QueryMethod  # Also import the QueryMethod enum
                logger.info("PersonalRAG module loaded successfully")
            else:
                raise ImportError(f"personal_rag.py not found at {module_path}")
                
        except Exception as e:
            logger.error(f"Error loading Personal RAG module: {str(e)}")
            logger.error("Make sure personal_rag.py exists in the current directory")
            logger.error("Try installing the required dependencies: pip install -r requirements.txt")
            sys.exit(1)
        
        # Initialize RAG system
        try:
            logger.info("Initializing PersonalRAG system...")
            
            # Check Milvus connection first (unless skipped)
            if os.getenv('SKIP_MILVUS_CHECK', '').lower() != 'true':
                self._ensure_milvus_connection()
            else:
                logger.info("Skipping Milvus connection check as per environment variable")
            
            # Use the enum value instead of string
            query_method_enum = self.QueryMethod.SEMANTIC
            self.rag = self.PersonalRAG(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                llm_type="gpt",  # Use GPT for RAG queries
                query_method=query_method_enum  # Use the enum value instead of a string
            )
            logger.info("PersonalRAG initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing PersonalRAG: {str(e)}")
            # Continue without RAG if initialization fails
            self.rag = None

    def _check_milvus_connection(self):
        """Check if Milvus server is accessible."""
        # Skip check if SKIP_MILVUS_CHECK is set
        if os.getenv('SKIP_MILVUS_CHECK', '').lower() == 'true':
            logger.info("Skipping Milvus connection check as per environment variable")
            return True
            
        try:
            # Try to connect to Milvus server using socket
            host = os.getenv('MILVUS_HOST', 'localhost')
            port = int(os.getenv('MILVUS_PORT', 19530))
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)  # 2 second timeout
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                logger.info(f"Milvus server is accessible at {host}:{port}")
                return True
            else:
                logger.warning(f"Cannot connect to Milvus server at {host}:{port}")
                return False
        except Exception as e:
            logger.error(f"Error checking Milvus connection: {str(e)}")
            return False
    
    def _ensure_milvus_connection(self):
        """Ensure connection to Milvus is possible."""
        # Skip check if SKIP_MILVUS_CHECK is set
        if os.getenv('SKIP_MILVUS_CHECK', '').lower() == 'true':
            logger.info("Skipping Milvus connection check as per environment variable")
            return True
            
        # Check if we can connect to Milvus
        if not self._check_milvus_connection():
            logger.warning("Cannot connect to Milvus. Make sure Milvus is running.")
            logger.warning("You may need to manually restart the Milvus containers.")
            logger.warning("Docker command: docker-compose -f path/to/docker-compose.yml restart")
            
            # Ask user if they want to continue
            proceed = input("Could not connect to Milvus. Continue anyway? (y/n): ")
            if proceed.lower() != 'y':
                logger.error("Exiting due to Milvus connection issues")
                sys.exit(1)
            
            logger.warning("Continuing without Milvus connection")
        
        return True
    
    def log(self, message):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
        # Also write to log file
        with open(f"logs/job_processing_{datetime.now().strftime('%Y%m%d')}.log", "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def process_jobs(self):
        """Run the complete job processing workflow."""
        self.log("Starting job processing workflow")
        
        try:
            if not self.test_mode:
                # Step 1: Retrieve new jobs from Apify
                self.log("Step 1: Retrieving jobs from Apify")
                jobs = self.retrieve_jobs()
                
                if not jobs or len(jobs) == 0:
                    self.log("No jobs found to process. Exiting.")
                    return
                
                self.log(f"Retrieved {len(jobs)} jobs")
                
                # Step 2: Insert jobs into database
                self.log("Step 2: Inserting jobs into database")
                self.db.insert_jobs(jobs)
            else:
                # Skip steps 1 and 2 in test mode
                self.log("TEST MODE: Skipping job retrieval and insertion (steps 1 and 2)")
            
            # Step 3: Process jobs without keywords
            self.log("Step 3: Processing jobs without keywords")
            processed_count = self.process_job_keywords()
            self.log(f"Processed keywords for {processed_count} jobs")
            
            # Step 4: Query RAG for jobs with keywords but no RAG info
            self.log("Step 4: Querying RAG for jobs with keywords")
            rag_processed = self.process_job_rag_info()
            self.log(f"Retrieved RAG info for {rag_processed} jobs")
            
            # Step 5: Analyze fitness of jobs against RAG info
            self.log("Step 5: Analyzing job fitness against RAG info")
            analyzed_count = self.analyze_job_fitness()
            self.log(f"Analyzed fitness for {analyzed_count} jobs")
            
            # Step 6: Extract scores from existing analyses
            self.log("Step 6: Extracting scores from existing job analyses")
            score_count = self.process_job_scores()
            self.log(f"Extracted scores for {score_count} jobs")
            
            self.log("Job processing workflow completed successfully")
            
        except Exception as e:
            self.log(f"Error in job processing workflow: {str(e)}")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}")
        finally:
            self.db.close()
    
    def retrieve_jobs(self):
        """Retrieve jobs from Apify."""
        try:
            # Get jobs from Apify
            jobs = self.apify.get_job_data()
            return jobs
        except Exception as e:
            self.log(f"Error retrieving jobs: {str(e)}")
            return None
    
    def process_job_keywords(self):
        """Process jobs that don't have keywords yet."""
        try:
            # Get jobs without keywords
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, job_id, title, description
                    FROM jobs 
                    WHERE keyword IS NULL
                    LIMIT 50
                """)
                jobs = cur.fetchall()
            
            if not jobs:
                self.log("No jobs found without keywords")
                return 0
            
            processed_count = 0
            
            for job in jobs:
                job_id = job[1]  # job_id is the second column
                title = job[2]
                description = job[3]
                
                self.log(f"Extracting keywords for job: {title} (ID: {job_id})")
                
                # Extract keywords using OpenAI
                keywords = self.extract_keywords(title, description)
                
                if keywords:
                    # Update the database with the keywords
                    with self.db.conn.cursor() as cur:
                        cur.execute("""
                            UPDATE jobs
                            SET keyword = %s
                            WHERE job_id = %s
                        """, (keywords, job_id))
                        self.db.conn.commit()
                    
                    processed_count += 1
                    self.log(f"Updated keywords for job {job_id}: {keywords}")
                else:
                    self.log(f"Failed to extract keywords for job {job_id}")
            
            return processed_count
        
        except Exception as e:
            self.log(f"Error processing job keywords: {str(e)}")
            return 0
    
    def extract_keywords(self, title, description):
        """Extract keywords from job title and description using GPT."""
        try:
            prompt = f"""
            Extract 5-7 relevant technical keywords or skills from the following job posting. 
            Focus on technical skills, technologies, programming languages, frameworks, and qualifications.
            Return ONLY a comma-separated list of keywords and nothing else.
            
            Job Title: {title}
            
            Job Description:
            {description[:4000]}  # Limit description length
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using the smaller model for keyword extraction
                messages=[
                    {"role": "system", "content": "You are a job keyword extraction assistant. Extract only the most relevant technical skills and software tools from job descriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=100
            )
            
            # Extract keywords from response
            keywords = response.choices[0].message.content.strip()
            
            # Clean up the keywords
            keywords = keywords.replace('\n', ', ')
            
            return keywords
        except Exception as e:
            self.log(f"Error extracting keywords: {str(e)}")
            return None
    
    def process_job_rag_info(self):
        """Query RAG for jobs with keywords but no RAG info."""
        if not self.rag:
            self.log("RAG system not initialized. Skipping RAG processing.")
            return 0
        
        try:
            # Get jobs with keywords but no RAG info
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, job_id, title, keyword
                    FROM jobs 
                    WHERE keyword IS NOT NULL AND rag_info IS NULL
                    LIMIT 25
                """)
                jobs = cur.fetchall()
            
            if not jobs:
                self.log("No jobs found with keywords but without RAG info")
                return 0
            
            processed_count = 0
            
            for job in jobs:
                job_id = job[1]
                title = job[2]
                keywords = job[3]
                
                self.log(f"Querying RAG for job: {title} (ID: {job_id})")
                
                # Build RAG query
                query = f"My experience and skills related to these technologies and skills: {keywords}"
                
                # Query the RAG system
                rag_result = self.rag.query(query)
                time.sleep(15)
                
                if rag_result and "answer" in rag_result:
                    rag_info = rag_result["answer"]
                    
                    # Save sources as a JSON string
                    sources = json.dumps(rag_result.get("sources", []))
                    
                    # Save the full RAG result for debugging
                    with open(f"debug_logs/rag_result_{job_id}.json", "w") as f:
                        json.dump(rag_result, f, indent=2)
                    
                    # Update the database with the RAG info
                    with self.db.conn.cursor() as cur:
                        cur.execute("""
                            UPDATE jobs
                            SET rag_info = %s
                            WHERE job_id = %s
                        """, (rag_info, job_id))
                        self.db.conn.commit()
                    
                    processed_count += 1
                    self.log(f"Updated RAG info for job {job_id}")
                    
                    # Don't overload the system
                    time.sleep(1)
                else:
                    self.log(f"Failed to get RAG info for job {job_id}")
            
            return processed_count
        
        except Exception as e:
            self.log(f"Error processing job RAG info: {str(e)}")
            return 0
    
    def analyze_job_fitness(self):
        """Analyze fitness of jobs against RAG info."""
        try:
            # Get jobs with RAG info but not analyzed
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, job_id, title, description, rag_info
                    FROM jobs 
                    WHERE rag_info IS NOT NULL AND gpt_analysis IS NULL
                    LIMIT 25
                """)
                jobs = cur.fetchall()
            
            if not jobs:
                self.log("No jobs found with RAG info but without analysis")
                return 0
            
            processed_count = 0
            
            for job in jobs:
                job_id = job[1]
                title = job[2]
                description = job[3]
                rag_info = job[4]
                
                self.log(f"Analyzing fitness for job: {title} (ID: {job_id})")
                
                # Create a job data dictionary for the analyzer
                job_data = {
                    'id': job_id,
                    'title': title,
                    'description': description,
                    'rag_info': rag_info
                }
                
                # Analyze job fitness
                analysis = self.analyze_with_gpt(job_data)
                
                if analysis:
                    is_best_fit = analysis['is_best_fit']
                    analysis_text = analysis['analysis']
                    score = analysis.get('score', None)
                    
                    # Update the database with the analysis
                    with self.db.conn.cursor() as cur:
                        cur.execute("""
                            UPDATE jobs
                            SET gpt_analysis = %s, is_best_fit = %s, score = %s
                            WHERE job_id = %s
                        """, (analysis_text, is_best_fit, score, job_id))
                        self.db.conn.commit()
                    
                    processed_count += 1
                    self.log(f"Updated analysis for job {job_id} (Best fit: {is_best_fit}, Score: {score})")
                    
                    # Don't overload the system
                    time.sleep(1)
                else:
                    self.log(f"Failed to analyze job {job_id}")
            
            return processed_count
        
        except Exception as e:
            self.log(f"Error analyzing job fitness: {str(e)}")
            return 0
    
    def analyze_with_gpt(self, job_data):
        """Analyze job fitness using GPT."""
        try:
            prompt = f"""
            Analyze this job opportunity against my experience and knowledge to determine if it's a good fit.
            
            Job Details:
            Title: {job_data['title']}
            
            Job Description:
            {job_data['description'][:4000]}
            
            My Relevant Experience and Skills (from Personal Knowledge Database):
            {job_data['rag_info']}
            
            Please provide a detailed analysis including:
            1. A score from 1-10 with 1 digit after the decimal point indicating how good of a fit this job is (format as "Score: X/10")
            2. Key strengths where my experience and skills match the job requirements
            3. Gaps where I lack experience or skills required for the job
            4. Overall assessment of fit and specific recommendations
            
            Note: The information about my experience is provided as raw document chunks. Extract and use only the relevant information from these chunks when evaluating the fit.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Using the larger model for detailed analysis
                messages=[
                    {"role": "system", "content": "You are a career advisor helping to match job opportunities with a candidate's experience and skills. Provide honest and practical analysis of fit."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            analysis = response.choices[0].message.content
            
            # Extract score to determine if it's a best fit
            is_best_fit = False
            score = 0
            
            # Various score extraction patterns
            patterns = [
                r'score[:\s]+(\d+(?:\.\d+)?)\s*\/?\s*10',
                r'(\d+(?:\.\d+)?)\s*\/\s*10',
                r'rating[:\s]+(\d+(?:\.\d+)?)\s*\/?\s*10'
            ]
            
            import re
            for pattern in patterns:
                match = re.search(pattern, analysis.lower())
                if match:
                    try:
                        score = float(match.group(1))
                        is_best_fit = score >= 7.0
                        break
                    except (ValueError, IndexError):
                        pass
            
            return {
                'is_best_fit': is_best_fit,
                'analysis': analysis,
                'score': score
            }
        except Exception as e:
            self.log(f"Error analyzing with GPT: {str(e)}")
            return None
    
    def process_job_scores(self):
        """Process jobs with analysis but without scores yet."""
        try:
            # Get jobs with analysis but no score
            with self.db.conn.cursor() as cur:
                cur.execute("""
                    SELECT id, job_id, gpt_analysis
                    FROM jobs 
                    WHERE gpt_analysis IS NOT NULL AND score IS NULL
                    LIMIT 50
                """)
                jobs = cur.fetchall()
            
            if not jobs:
                self.log("No jobs found with analysis but without scores")
                return 0
            
            processed_count = 0
            
            for job in jobs:
                job_id = job[1]
                analysis = job[2]
                
                # Extract score from analysis
                score = 0
                patterns = [
                    r'score[:\s]+(\d+(?:\.\d+)?)\s*\/?\s*10',
                    r'(\d+(?:\.\d+)?)\s*\/\s*10',
                    r'rating[:\s]+(\d+(?:\.\d+)?)\s*\/?\s*10'
                ]
                
                import re
                for pattern in patterns:
                    match = re.search(pattern, analysis.lower())
                    if match:
                        try:
                            score = float(match.group(1))
                            break
                        except (ValueError, IndexError):
                            pass
                
                if score > 0:
                    # Update the database with the score
                    with self.db.conn.cursor() as cur:
                        cur.execute("""
                            UPDATE jobs
                            SET score = %s, is_best_fit = %s
                            WHERE job_id = %s
                        """, (score, score >= 7.0, job_id))
                        self.db.conn.commit()
                    
                    processed_count += 1
                    self.log(f"Updated score for job {job_id} (Score: {score})")
            
            return processed_count
        
        except Exception as e:
            self.log(f"Error processing job scores: {str(e)}")
            return 0

def main():
    """Main entry point for the job processing workflow."""
    print(f"Starting job processing at {datetime.now()}")
    
    # Run database schema update first
    try:
        from update_database import update_database_schema
        update_database_schema()
    except Exception as e:
        print(f"Error updating database schema: {str(e)}")
        print("Continuing with processing...")
    
    # Initialize job processor
    processor = JobProcessor()
    
    # Run the full workflow
    processor.process_jobs()
    
    print(f"Job processing completed at {datetime.now()}")

if __name__ == "__main__":
    main() 