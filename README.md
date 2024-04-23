```bash
poetry run uvicorn main:app --host localhost
```

```bash
ngrok http --domain=<domain> 8000
```

Visit `https://<domain>/stripe-checkout`
