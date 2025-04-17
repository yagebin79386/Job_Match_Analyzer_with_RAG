import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from dotenv import load_dotenv
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER')
        self.smtp_port = int(os.getenv('SMTP_PORT'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_sender = os.getenv('EMAIL_SENDER', self.email_user)
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        # Database connection
        self.db_host = os.getenv('DB_HOST')
        self.db_port = os.getenv('DB_PORT')
        self.db_name = os.getenv('DB_NAME')
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        # Create emails directory if it doesn't exist
        os.makedirs('emails', exist_ok=True)
        # Store the last run time
        self.last_run_file = 'last_email_run.txt'
    
    def _get_db_connection(self):
        """Get a connection to the database."""
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            user=self.db_user,
            password=self.db_password
        )
    
    def _get_last_run_time(self):
        """Get the last time the email service was run."""
        if os.path.exists(self.last_run_file):
            with open(self.last_run_file, 'r') as f:
                last_run = f.read().strip()
                try:
                    return datetime.fromisoformat(last_run)
                except ValueError:
                    # If there's an error parsing the date, return a date 7 days ago
                    return datetime.now() - timedelta(days=7)
        # If the file doesn't exist, return a date 7 days ago
        return datetime.now() - timedelta(days=7)
    
    def _update_last_run_time(self):
        """Update the last run time to now."""
        with open(self.last_run_file, 'w') as f:
            f.write(datetime.now().isoformat())
    
    def get_top_jobs(self, limit=7):
        """
        Get the top jobs with the highest scores that have been created
        since the last email run.
        
        Args:
            limit (int): The maximum number of jobs to return
            
        Returns:
            list: A list of job dictionaries
        """
        last_run = self._get_last_run_time()
        
        conn = self._get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT *
                    FROM jobs
                    WHERE created_at > %s
                    ORDER BY score DESC NULLS LAST
                    LIMIT %s
                """, (last_run, limit))
                
                jobs = cur.fetchall()
                print(f"Retrieved {len(jobs)} jobs created since {last_run}")
                return jobs
        except Exception as e:
            print(f"Error retrieving jobs: {str(e)}")
            return []
        finally:
            conn.close()

    def send_job_newsletter(self, recipient_email=None):
        """
        Send a newsletter with the top jobs by score.
        
        Args:
            recipient_email (str, optional): The email to send to. If None, uses the email from env.
        """
        if recipient_email is None:
            recipient_email = self.recipient_email
            
        if not recipient_email:
            print("No recipient email provided or configured. Cannot send email.")
            return
            
        # Get the top jobs
        jobs = self.get_top_jobs(limit=7)
        
        if not jobs:
            print("No new jobs to send. Skipping email.")
            return
        
        msg = MIMEMultipart('alternative')
        today = datetime.now().strftime("%Y-%m-%d")
        msg['Subject'] = f'Top Job Matches - {today}'
        msg['From'] = self.email_sender
        msg['To'] = recipient_email

        # Create HTML content
        html_template = """
        <html>
            <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50; text-align: center;">Your Top 7 Job Matches</h1>
                <p style="text-align: center; color: #7f8c8d;">Showing the best matches since the last update</p>
                
                {% for job in jobs %}
                <div style="margin-bottom: 30px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; background-color: #f9f9f9;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <h2 style="color: #3498db; margin-top: 0;">{{ job.title }}</h2>
                        <span style="background-color: {% if job.score >= 7.0 %}#27ae60{% elif job.score >= 5.0 %}#f39c12{% else %}#e74c3c{% endif %}; color: white; padding: 5px 10px; border-radius: 20px; font-weight: bold;">{{ job.score|round(1) }}/10</span>
                    </div>
                    
                    <p><strong>Company:</strong> {{ job.company_name }}</p>
                    <p><strong>Location:</strong> {{ job.location }}</p>
                    {% if job.experience_level %}
                    <p><strong>Experience Level:</strong> {{ job.experience_level }}</p>
                    {% endif %}
                    {% if job.sector %}
                    <p><strong>Sector:</strong> {{ job.sector }}</p>
                    {% endif %}
                    {% if job.work_type %}
                    <p><strong>Work Type:</strong> {{ job.work_type }}</p>
                    {% endif %}
                    {% if job.contract_type %}
                    <p><strong>Contract Type:</strong> {{ job.contract_type }}</p>
                    {% endif %}
                    {% if job.salary %}
                    <p><strong>Salary:</strong> {{ job.salary }}</p>
                    {% endif %}
                    {% if job.published_at %}
                    <p><strong>Published Date:</strong> {{ job.published_at }}</p>
                    {% endif %}
                    {% if job.applications_count %}
                    <p><strong>Applications Count:</strong> {{ job.applications_count }}</p>
                    {% endif %}
                    
                    <div style="margin: 15px 0; padding: 10px; background-color: #fff; border-left: 4px solid #3498db;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Match Analysis</h3>
                        <p>{{ job.gpt_analysis }}</p>
                    </div>
                    
                    <div style="margin-top: 15px;">
                        {% if job.apply_url %}
                        <a href="{{ job.apply_url }}" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">Apply Now</a>
                        {% endif %}
                        {% if job.company_url %}
                        <a href="{{ job.company_url }}" style="margin-left: 10px; color: #3498db; text-decoration: none;">View Company Profile</a>
                        {% endif %}
                        {% if job.job_url %}
                        <a href="{{ job.job_url }}" style="margin-left: 10px; color: #3498db; text-decoration: none;">View Job Posting</a>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            </body>
        </html>
        """

        template = Template(html_template)
        html_content = template.render(jobs=jobs)
        
        # Save the HTML content to a file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        email_file_path = f"emails/job_newsletter_{timestamp}.html"
        
        with open(email_file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"Email saved to {email_file_path}")
        
        # Attach the HTML content to the email
        msg.attach(MIMEText(html_content, 'html'))

        # Send the email
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
                print(f"Email sent successfully to {recipient_email}")
                # Update the last run time after successful sending
                self._update_last_run_time()
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            print("Note: The email has been saved locally even though sending failed.")

# For testing
if __name__ == "__main__":
    email_service = EmailService()
    email_service.send_job_newsletter() 