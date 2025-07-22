# 📊 Alemeno Credit Approval System

A backend system for processing and approving customer loan applications. Built with Django and Django Rest Framework, containerized with Docker, and powered by PostgreSQL, Celery, and Redis.

---

## ✨ Features

* **Customer Registration**
  Automatically calculates an `approved_limit` based on the customer's monthly income.

* **Loan Eligibility Check**
  Determines eligibility using a custom credit score algorithm and customer loan history.

* **Loan Creation**
  Processes new loan applications, updates customer debt, and applies eligibility logic.

* **View Loans by Customer**
  Lists all loans associated with a specific customer.

* **Detailed Loan View**
  Retrieves in-depth information about individual loans, including customer details.

* **Loan Statement**
  Provides a detailed breakdown of loan terms, EMIs paid, remaining installments, and due EMIs.

* **Background Data Ingestion**
  Imports initial customer and loan data from Excel via Celery background tasks.

* **Dockerized Environment**
  All services (web, database, Redis, Celery) run in isolated containers for consistency.

* **Robust Error Handling**
  Returns meaningful error messages and status codes for all edge cases.

* **Unit Testing**
  Full test coverage for models, utility functions, and API endpoints.

---

## 🛠️ Tech Stack

* **Language:** Python 3.10
* **Framework:** Django 5.0.1, Django Rest Framework
* **Database:** PostgreSQL 13
* **Queue:** Celery + Redis
* **Containerization:** Docker & Docker Compose
* **Excel Parsing:** Pandas & OpenPyXL
* **Precision:** Decimal for accurate financial calculations

---

## 🚀 Setup & Installation

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop/)
* [Git](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/LAKSHYA1509/Alemeno_Task
cd Alemeno_Task
```

### 2. Create Environment File

Create a `.env` file in the root directory:

```env
POSTGRES_DB=alemeno_db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
REDIS_HOST=redis
REDIS_PORT=6379
```

### 3. Build & Start the Containers

```bash
docker-compose up -d --build
```

Check service status:

```bash
docker-compose ps
```

### 4. Ingest Initial Data

Place `customer_data.xlsx` and `loan_data.xlsx` in a `data/` directory at the project root.

Run the ingestion task:

```bash
docker-compose exec web python manage.py ingest_initial_data
```

Monitor Celery logs:

```bash
docker-compose logs celery_worker-1
```

### 5. Reset Database Sequence (Important!)

```bash
docker-compose exec db-1 bash
psql -U user -d alemeno_db

# Run inside psql
SELECT setval('core_customer_customer_id_seq', (SELECT MAX(customer_id) FROM core_customer));

\q
exit
```

---

## 📡 API Endpoints

Base URL: `http://localhost:8000/api/`

---

### 1. Register Customer

**POST** `/register`

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "age": 30,
  "monthly_income": 60000.00,
  "phone_number": "1234567890"
}
```

📥 `approved_limit = 36 * monthly_income (rounded to nearest lakh)`

---

### 2. Check Loan Eligibility

**POST** `/check-eligibility`

```json
{
  "customer_id": 1,
  "loan_amount": 500000.00,
  "tenure": 12
}
```

📥 Returns eligibility, interest rates, and EMI calculation.

---

### 3. Create Loan

**POST** `/create-loan`

```json
{
  "customer_id": 1,
  "loan_amount": 100000.00,
  "tenure": 12,
  "interest_rate": 15.00
}
```

📥 Returns approval status, EMI, and corrected interest rate if needed.

---

### 4. View All Loans for a Customer

**GET** `/view-loans/{customer_id}`

Returns all loans associated with a customer.

---

### 5. View Single Loan Details

**GET** `/view-loan/{loan_id}`

Returns loan details including customer info.

---

### 6. View Loan Statement

**GET** `/view-statement/{customer_id}/{loan_id}`

Returns loan statement including:

* EMIs paid
* Remaining payments
* EMIs due
* Start and end dates

---

## ✅ Running Unit Tests

Ensure containers are running:

```bash
docker-compose up -d
```

Run tests:

```bash
docker-compose exec web python manage.py test core
```

🟢 All tests should pass.

---

## 🧯 Error Handling

All API endpoints return:

* `400 Bad Request` – for invalid input
* `404 Not Found` – for missing records
* `500 Internal Server Error` – for unexpected failures

---

## 📁 Directory Structure (Important Folders)

```
Alemeno_Task/
├── core/                 # Django app with models, views, serializers
├── data/                 # Contains customer_data.xlsx & loan_data.xlsx
├── docker/               # Docker-related configs
├── .env                  # Environment variables
├── docker-compose.yml    # Docker orchestration
└── README.md             # Project documentation
```
