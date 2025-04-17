# Job Collection Reminder

A system that scrapes job listings from LinkedIn using Apify, analyzes them with GPT, matches them against your personal knowledge database using RAG, and sends email notifications for the best matches.

## Features

- Scrapes job listings from LinkedIn using Apify
- Extracts relevant keywords from job descriptions
- Queries your personal knowledge database (RAG) to retrieve relevant information
- Analyzes job fitness based on your skills and experience
- Sends daily email newsletters with the best matches

## Setup Instructions

### 1. Prerequisites

- Python 3.10+
- PostgreSQL database
- Milvus vector database (for PersonalRAG)
- Apify account with LinkedIn Jobs Scraper actor
- OpenAI API key

### 2. Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd job-collection-reminder
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

   Note: If you're only interested in job scraping and analysis without the RAG functionality, you can skip the RAG-related dependencies:
   ```
   pip install psycopg2-binary openai apify-client python-dotenv schedule jinja2
   ```

### 3. Database Setup

1. Create a PostgreSQL database:
   ```
   createdb job_collection
   ```

2. Run the database schema setup:
   ```
   python update_database.py
   ```

### 4. Configuration

Create a `.env` file in the project root with the following variables:

```
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=job_collection
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# Apify
APIFY_API_TOKEN=your_apify_api_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Email (optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# RAG (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### 5. Personal RAG Setup (Optional)

If you want to use the Personal RAG functionality:

1. Make sure you have the PersonalRAG system set up in the `Personal_RAG` directory or at the path specified in `process_jobs_rag.py`.

2. Ensure the Milvus vector database is running and populated with your personal knowledge.

## Usage

### Running the Job Processing Workflow

You can run the job processing workflow in two ways:

1. **One-time execution**:
   ```
   python run_job_processing.py
   ```

2. **Scheduled execution** (runs daily at 9:00 AM):
   ```
   python main.py
   ```

### Workflow Steps

1. **Job Retrieval**: Fetches job listings from LinkedIn using Apify
2. **Keyword Extraction**: Extracts relevant keywords from job descriptions
3. **RAG Querying**: Retrieves information from your personal knowledge database
4. **Fitness Analysis**: Analyzes how well your skills match the job requirements
5. **Email Notification**: Sends an email with the best job matches (if enabled)

## Troubleshooting

### Missing Dependencies

If you encounter errors about missing dependencies, install them as needed:

```
pip install torch transformers langchain langchain-openai langchain-community pymilvus
```

### RAG System Not Found

If the PersonalRAG system is not found, ensure that the `personal_rag.py` file is in one of these locations:
- `Personal_RAG/personal_rag.py`
- `../Personal_RAG/personal_rag.py`
- `personal_rag.py`
- `./personal_rag.py`

### Database Errors

If you encounter database connection errors, check that:
1. Your PostgreSQL server is running
2. The database credentials in `.env` are correct
3. The database exists and is accessible

## License

[MIT License](LICENSE) 