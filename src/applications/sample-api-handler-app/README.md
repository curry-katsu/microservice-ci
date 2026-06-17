# sample-api-handler-app

Sample Lambda API application for integration testing API Gateway style events.

The handler includes:

- Bearer token authorization.
- CRUD business logic for order records stored in PostgreSQL.
- S3 audit records for write operations.

Run local integration tests after starting the local environment:

```bash
make local-up
make integration-test PROJECT=src/applications/sample-api-handler-app
```
