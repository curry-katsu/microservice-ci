# sample-sqs-handler-app

SQS event を受け取るサンプル Lambda アプリケーションです。

Handler:

```text
sample_sqs_handler_app.handler.lambda_handler
```

Integration test:

```bash
make local-up
make integration-test PROJECT=src/applications/sample-sqs-handler-app
make local-down
```
