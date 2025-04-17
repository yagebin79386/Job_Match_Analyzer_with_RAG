# Job Match Analyzer with RAG

A sophisticated job matching system that retrieves job listings via Apify, analyzes them using OpenAI's GPT models, and leverages a personal Retrieval Augmented Generation (RAG) system to assess job fit based on your personal profile.

[![GitHub stars](https://img.shields.io/github/stars/yagebin79386/Job_Match_Analyzer_with_RAG?style=social)](https://github.com/yagebin79386/Job_Match_Analyzer_with_RAG/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## 🌟 Overview

This project creates an automated job matching system that:

1. **Retrieves job listings** using Apify's LinkedIn Jobs Scraper
2. **Stores job details** in a PostgreSQL database
3. **Extracts key information** from job descriptions
4. **Cross-references** with your personal profile data using RAG technology
5. **Analyzes job fit** with GPT models to provide match scores
6. **Sends personalized email digests** with the best job matches

## 🖼️ Showcase

Here's an example of the system in action - analyzing a Data Analyst/Data Scientist internship position and providing a detailed match assessment:

<!-- 
To add your own screenshot:
1. Add your job analysis screenshot to a folder named 'images' in this repository
2. Replace the placeholder URL below with: ./images/job_analysis_example.png
-->

![Job Match Analysis Example](https://i.imgur.com/YOURIMAGEIDHere.png)

The system delivers comprehensive job analyses that include:
- Overall match score (e.g., 9.0/10)
- Key strengths and weaknesses of the position
- Specific requirements analysis
- Company culture assessment
- Career growth potential
- Compensation considerations
- Final recommendation

This helps job seekers quickly identify the most promising opportunities based on their personal profile and preferences.

## 🛠️ Core Components

- **`apify_wrapper.py`**: Interfaces with Apify API to retrieve job listings
- **`create_table.sql`**: SQL script for database schema creation
- **`process_jobs_rag.py`**: Performs RAG-based job analysis and scoring
- **`email_service.py`**: Generates and sends HTML email digests
- **`run_job_processing.py`**: Coordinates the end-to-end workflow
- **`personal_rag.py`**: Implements RAG system for personal data retrieval
- **`main.py`**: Schedules regular job processing runs

## 🔄 Workflow

1. **Job Collection**: Fetches jobs from LinkedIn via Apify
2. **Data Processing**: Stores job listings in PostgreSQL
3. **RAG Integration**: Extracts job requirements and queries personal RAG system
4. **GPT Analysis**: Uses OpenAI models to analyze job-profile match
5. **Scoring**: Assigns numerical scores (1-10) based on match quality
6. **Notification**: Sends email digests with best matches and detailed analysis

## 📋 Requirements

- Python 3.8+
- PostgreSQL database
- Apify account with API token
- OpenAI API key
- SMTP email server access
- Personal RAG system (see [Personal RAG System](https://github.com/yagebin79386/Peronsal-RAG-System))

## 🚀 Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/yagebin79386/Job_Match_Analyzer_with_RAG.git
cd Job_Match_Analyzer_with_RAG
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Database setup

This project uses PostgreSQL to store job data. The database schema is defined in `create_table.sql`.

```bash
# Create PostgreSQL database
createdb job_collection

# Initialize database schema
psql -d job_collection -f create_table.sql
```

**Note:** Unlike some projects, this repository does not include a separate database.py module. The database interactions are handled directly within the processing scripts.

### 4. Environment configuration

Create a `.env` file with the following variables:

```
# Apify API Configuration
APIFY_API_TOKEN=your_apify_token
APIFY_TASK_ID=your_task_id

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=job_collection
DB_USER=your_username
DB_PASSWORD=your_password

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# Email Configuration
SMTP_SERVER=your_smtp_server
SMTP_PORT=587
EMAIL_USER=your_email
EMAIL_PASSWORD=your_password
EMAIL_SENDER=your_sender_email
RECIPIENT_EMAIL=your_recipient_email
```

### 5. Personal RAG system

This project requires a Personal RAG system to analyze your profile against job requirements. You can set up your own following our companion repository:

👉 [Personal RAG System](https://github.com/yagebin79386/Peronsal-RAG-System)

## 📊 Job Analysis Process

The system evaluates job matches based on:

1. **Technical Skills Match**: How well your skills align with job requirements
2. **Experience Level Fit**: Whether your experience matches the job level
3. **Industry/Domain Knowledge**: Familiarity with the job's industry
4. **Soft Skills Compatibility**: Alignment with required soft skills
5. **Career Trajectory**: How well the job fits your career path

Each job receives a score from 1-10, with jobs scoring 7+ considered good matches.

## 📨 Email Notifications

The system sends beautiful HTML emails containing:

- Job titles and companies
- Match scores with color-coding (green for 7+, yellow for 5-7, red for <5)
- Detailed match analysis for each position
- Direct links to job applications
- Organized by match quality

## 🏃‍♂️ Running the System

### Manual execution

```bash
python run_job_processing.py
```

### Scheduled execution

```bash
python main.py  # Runs daily at configured time
```

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related Projects

- [Personal RAG System](https://github.com/yagebin79386/Peronsal-RAG-System) - The companion RAG system for personal data management used by this project 