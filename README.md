# Distributed URL Shortener

A senior-level system design practice project implementing a scalable URL shortener using a microservices architecture.

## Architecture

The system is composed of the following microservices:

- **Gateway**: Entry point (Nginx/Traefik) for routing and rate limiting.
- **Auth Service**: User authentication and JWT management.
- **Write Service (Manager)**: Handles URL creation and management.
- **Read Service (Redirector)**: High-performance URL redirection.
- **Analytics Service**: Asynchronous processing of click events.

## Tech Stack

- **Languages**: Python (FastAPI), Go (optional for Redirector)
- **Databases**: PostgreSQL (User/Write), Redis (Cache), ClickHouse/Elastic (Analytics)
- **Messaging**: Kafka/RabbitMQ
- **Infrastructure**: Docker, Kubernetes, Terraform

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.11+

### Running Locally
```bash
docker-compose up --build
```
